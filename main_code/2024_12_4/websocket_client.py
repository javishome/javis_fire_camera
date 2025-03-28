import asyncio
import websockets
import json
import numpy as np
import logging
from datetime import datetime
import aiofiles  # Thêm aiofiles để ghi file bất đồng bộ

_LOGGER = logging.getLogger(__name__)

class WebSocketClient:
    def __init__(self, hass, user_name, password, camera_ip):
        self.hass = hass
        self.running = True
        self.user_name = user_name
        self.password = password
        self.camera_ip = camera_ip
        self.websocket = None
        self.ws_url = f"ws://{camera_ip}:8088/"
        self.callbacks = []  # Danh sách các callback để gửi dữ liệu đến nhiều cảm biến

    def add_callback(self, callback):
        """Thêm callback từ các cảm biến."""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    async def connect(self):
        """Kết nối WebSocket và lắng nghe tin nhắn."""
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    _LOGGER.info(f"✅ Connected to WebSocket: {self.ws_url}")
                    await self.send_message({"cmd": "recvpic", "streamindex": 0})
                    while self.running:
                        message = await websocket.recv()
                        await self.process_message(message)
            except Exception as e:
                _LOGGER.error(f"⚠️ WebSocket error: {e}, retrying in 5s...")
                await asyncio.sleep(5)

    async def send_message(self, message):
        """Gửi lệnh qua WebSocket."""
        if self.websocket:
            try:
                json_message = json.dumps(message)
                await self.websocket.send(json_message)
                _LOGGER.info(f"📤 Sent: {json_message}")
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
                    async with aiofiles.open(name, 'wb') as f:  # Sử dụng aiofiles
                        await f.write(image_part.tobytes())
                    _LOGGER.info(f"📷 Saved image: {name}")
                else:
                    text_part = data[20:20+F].tobytes().decode('utf-8').replace("\x00", "").strip()
                    json_content = json.loads(text_part)
                    image_part = data[20+F:]
                    name = f"/config/www/{int(datetime.now().timestamp() * 1000)}.jpg"
                    async with aiofiles.open(name, 'wb') as f:  # Sử dụng aiofiles
                        await f.write(image_part.tobytes())
                    _LOGGER.info(f"📝 JSON: {json_content}")
                    for callback in self.callbacks:
                        await callback(json_content)
        except Exception as e:
            _LOGGER.error(f"⚠️ Error processing message: {e}")

    def stop(self):
        """Dừng WebSocket."""
        self.running = False
        if self.websocket:
            self.websocket.close()