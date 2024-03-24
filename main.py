import os
import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# Initialize UserAgent outside of the async function to avoid re-initialization on every call
user_agent = UserAgent()

def get_random_desktop_user_agent():
    # Select a random user agent for desktop browsers
    desktop_browsers = [
        user_agent.chrome,
        user_agent.firefox,
        user_agent.edge,
    ]
    # Randomly choose among the desktop browser methods and call it to get the user agent string
    random_desktop_user_agent = random.choice(desktop_browsers)()
    return random_desktop_user_agent

async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            
            # Use the function to get a random desktop browser user agent
            random_user_agent = get_random_desktop_user_agent()
            
            custom_headers = {
                "User-Agent": random_user_agent
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "2.5.0"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(e)
            logger.error(socks5_proxy)


async def main():
    _user_id = os.getenv('USER_ID', 'default_user_id')  # Use default if not set
    proxy = os.getenv('SOCKS5_PROXY', 'socks5://default:user@ip:port')  # Use default if not set
    
    socks5_proxy_list = [proxy]
    
    tasks = [asyncio.ensure_future(connect_to_wss(i, _user_id)) for i in socks5_proxy_list]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
