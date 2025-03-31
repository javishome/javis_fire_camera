import logging
import asyncio
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.persistent_notification import async_create
from homeassistant.exceptions import ConfigEntryNotReady
from .websocket_client import WebSocketClient

_LOGGER = logging.getLogger(__name__)
DOMAIN = "fire_camera"

async def async_setup_entry(hass, entry, async_add_entities):
    """Thiết lập cảm biến khi Home Assistant khởi động."""
    camera_name = entry.data.get("camera_name")
    user_name = entry.data.get("user_name")
    password = entry.data.get("password")
    camera_ip = entry.data.get("camera_ip")
    mac_address = entry.data.get("mac_address")
    
    _LOGGER.info(f"🔗 Connecting to {camera_name} at {camera_ip}...")
    
    # Khởi tạo WebSocketClient duy nhất
    ws_client = WebSocketClient(hass, user_name, password, camera_ip)
    
    # Lưu ws_client vào hass.data để dọn dẹp sau này
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ws_client
    
    # Tạo các cảm biến và đăng ký callback
    fire_sensor = FireSmokeSensor(hass, camera_name, ws_client, mac_address, "fire")
    smoke_sensor = FireSmokeSensor(hass, camera_name, ws_client, mac_address, "smoke")
    
    # Thêm các cảm biến vào HA
    async_add_entities([fire_sensor, smoke_sensor], True)
    
    # Đăng ký callback từ các cảm biến
    ws_client.add_callback(fire_sensor.receive_ws_data)
    ws_client.add_callback(smoke_sensor.receive_ws_data)
    
    # Chạy kết nối WebSocket trong một tác vụ bất đồng bộ
    hass.loop.create_task(ws_client.connect())

class FireSmokeSensor(BinarySensorEntity):
    """Cảm biến nhị phân để nhận dữ liệu từ WebSocket."""

    def __init__(self, hass, camera_name, ws_client, mac_address, event_type):
        self._attr_is_on = False
        self.hass = hass
        if event_type == "fire":
            self.name_sensor = "lửa"
        else:
            self.name_sensor = "khói"
        self.entity_id = f"binary_sensor.cam_ai_{mac_address.replace(':', '')}_{event_type.lower()}_sensor"
        self._attr_name = f"cảm biến {self.name_sensor} {camera_name}"
        self._attr_unique_id = f"binary_sensor.cam_ai_{mac_address.replace(':', '')}_{event_type.lower()}_sensor"
        self.event_type = event_type
        if event_type == "fire":
            self._attr_device_class = "heat"
        else:
            self._attr_device_class = event_type
        self.ws_client = ws_client
        self._timeout_task = None

    async def receive_ws_data(self, message):
        """Xử lý tin nhắn từ WebSocket Server."""
        _LOGGER.info(f"Received WebSocket data for {self.event_type}: {message}")
        if message.get("event") == self.event_type:
            self._attr_is_on = True
            self.async_write_ha_state()
            self.reset_timer()

    def reset_timer(self):
        """Đặt lại bộ hẹn giờ để tắt cảm biến sau 30 giây."""
        if self._timeout_task:
            self._timeout_task.cancel()
        self._timeout_task = self.hass.loop.create_task(self.turn_off_after_delay())

    async def turn_off_after_delay(self):
        """Tắt cảm biến sau 30 giây."""
        try:
            await asyncio.sleep(30)
            self._attr_is_on = False
            self.async_write_ha_state()
        except asyncio.CancelledError:
            _LOGGER.debug(f"Timer for {self._attr_name} was cancelled")

    async def async_will_remove_from_hass(self):
        """Dọn dẹp khi cảm biến bị xóa khỏi HA."""
        if self._timeout_task:
            self._timeout_task.cancel()
        self.ws_client.stop()
        await super().async_will_remove_from_hass()

    def stop_ws(self):
        """Dừng kết nối WebSocket khi HA tắt."""
        self.ws_client.stop()