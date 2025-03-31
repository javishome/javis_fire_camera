import logging
import asyncio
import aiohttp
import numpy as np
import json
from datetime import datetime
import aiofiles

_LOGGER = logging.getLogger(__name__)

class WebSocketClient:
    def __init__(self, hass, user_name, password, camera_ip):
        """Khởi tạo WebSocketClient."""
        self.hass = hass
        self.running = False
        self.user_name = user_name
        self.password = password
        self.camera_ip = camera_ip
        self.ws_url = f"ws://{camera_ip}:8088/"
        self.websocket = None
        self.session = None
        self.callbacks = []

    def add_callback(self, callback):
        """Thêm callback từ các cảm biến."""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    async def connect(self):
        """Kết nối WebSocket và lắng nghe tin nhắn."""
        self.running = True
        self.session = aiohttp.ClientSession()
        _LOGGER.info(f"Starting WebSocket client for {self.ws_url}")

        while self.running:
            try:
                async with self.session.ws_connect(self.ws_url, timeout=10) as websocket:
                    self.websocket = websocket
                    _LOGGER.info(f"✅ Connected to WebSocket: {self.ws_url}")
                    await self.send_message({"cmd": "recvpic", "streamindex": 0})

                    while self.running:
                        try:
                            # Đặt timeout 30 giây cho việc nhận tin nhắn
                            msg = await asyncio.wait_for(websocket.receive(), timeout=30)
                            if msg.type == aiohttp.WSMsgType.BINARY:
                                await self.process_message(msg.data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                _LOGGER.warning("WebSocket connection closed or error occurred")
                                break
                        except asyncio.TimeoutError:
                            _LOGGER.debug("No message received within 30 seconds, continuing...")
                            continue
                        except Exception as e:
                            _LOGGER.error(f"Error receiving WebSocket message: {e}")
                            break

            except aiohttp.ClientError as e:
                _LOGGER.error(f"⚠️ WebSocket connection error: {e}, retrying in 5s...")
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                _LOGGER.info("WebSocket connection cancelled, stopping...")
                self.running = False
                break
            except Exception as e:
                _LOGGER.error(f"⚠️ Unexpected WebSocket error: {e}, retrying in 5s...")
                await asyncio.sleep(5)

        # Dọn dẹp khi dừng
        _LOGGER.info("self.running: %s", self.running)
        await self.stop(shutdown=True)

    async def send_message(self, message):
        """Gửi lệnh qua WebSocket."""
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.send_json(message)
                _LOGGER.info(f"📤 Sent: {json.dumps(message)}")
            except Exception as e:
                _LOGGER.error(f"⚠️ Send message failed: {e}")

    async def process_message(self, message):
        """Xử lý tin nhắn nhận được từ WebSocket."""
        try:
            data = np.frombuffer(message, dtype=np.uint8)
            header = np.frombuffer(data[:12], dtype=np.uint32)
            L, F, code = header[0], header[1], header[2]
            _LOGGER.info(f"📡 Received header: L={L}, F={F}, code={code}")

            if code == 3 and L > 0:
                if F == 0:
                    image_part = data[20:]
                    name = f"/config/www/{int(datetime.now().timestamp() * 1000)}.jpg"
                    async with aiofiles.open(name, 'wb') as f:
                        await f.write(image_part.tobytes())
                    _LOGGER.info(f"📷 Saved image: {name}")
                else:
                    text_part = data[20:20+F].tobytes().decode('utf-8').replace("\x00", "").strip()
                    json_content = json.loads(text_part)
                    image_part = data[20+F:]
                    name = f"/config/www/{int(datetime.now().timestamp() * 1000)}.jpg"
                    async with aiofiles.open(name, 'wb') as f:
                        await f.write(image_part.tobytes())
                    _LOGGER.info(f"📝 JSON: {json_content}")
                    for callback in self.callbacks:
                        await callback(json_content)
        except Exception as e:
            _LOGGER.error(f"⚠️ Error processing message: {e}")

    async def stop(self, shutdown=True):
        """Dừng kết nối WebSocket."""
        self.running = False
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        if self.session:
            await self.session.close()
        self.websocket = None
        self.session = None
        if shutdown:
            _LOGGER.info("WebSocket client stopped")
        else:
            _LOGGER.info("WebSocket client stopped for reload, will restart")