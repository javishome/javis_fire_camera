import logging
import asyncio
from homeassistant.components.binary_sensor import BinarySensorEntity
from .websocket_client import WebSocketClient
from homeassistant.components import webhook
from .api import set_callback_url, handle_webhook, get_webhook_url, get_local_ip
from .const import log, DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Thiết lập cảm biến khi Home Assistant khởi động."""
    camera_name = entry.data.get("camera_name")
    user_name = entry.data.get("user_name")
    password = entry.data.get("password")
    camera_ip = entry.data.get("camera_ip")
    mac_address = entry.data.get("mac_address")
    camera_type = entry.data.get("camera_type")
    token = entry.data.get("token")
    local_ip = await get_local_ip()
    log(f"🔗 Connecting to {camera_name} at {camera_ip}...")
    sensors = {}
    ws_client = WebSocketClient(hass, user_name, password, camera_ip) if camera_type == "1" else None
     # Khởi tạo cảm biến
    fire_sensor = FireSmokeSensor(hass, camera_name, ws_client, mac_address, "fire")
    smoke_sensor = FireSmokeSensor(hass, camera_name, ws_client, mac_address, "smoke")
    sensors["fire"] = fire_sensor
    sensors["smoke"] = smoke_sensor

    async_add_entities([fire_sensor, smoke_sensor], True)

    if camera_type == "1":
        # CAMERA WEBSOCKET
        log(f"Khởi tạo WebSocket cho camera {camera_name} ({camera_ip}) loại {camera_type}")
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ws_client
        ws_client.add_callback(fire_sensor.receive_ws_data)
        ws_client.add_callback(smoke_sensor.receive_ws_data)
        hass.loop.create_task(ws_client.connect())

    elif camera_type == "2":
        # CAMERA WEBHOOK
        log(f"Khởi tạo Webhook cho camera {camera_name} ({camera_ip}) loại {camera_type}")
        webhook_id = f"firecam_{mac_address.replace(':', '')}"
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = sensors

        webhook.async_unregister(hass, webhook_id)

        webhook.async_register(
            hass,
            DOMAIN,
            f"Webhook {camera_name}",
            webhook_id,
            handle_webhook
        )

        # Đăng ký webhook URL lên camera
        webhook_url = await get_webhook_url(local_ip, webhook_id)
        await set_callback_url(camera_ip, token, webhook_url)
        # await hass.async_add_executor_job(set_callback_url, camera_ip, token, webhook_url)

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
        if not self.ws_client:
            log(f"data for {self.event_type} for camara type 2 {message}")
        else:
            log(f"data for {self.event_type} for camara type 1 {message}")
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
            log(f"Timer for {self._attr_name} was cancelled")

    async def async_will_remove_from_hass(self):
        """Dọn dẹp khi cảm biến bị xóa khỏi HA."""
        if self.ws_client:
            if self._timeout_task:
                self._timeout_task.cancel()
            await self.ws_client.stop()
            await super().async_will_remove_from_hass()

    async def stop_ws(self):
        """Dừng kết nối WebSocket khi HA tắt."""
        if self.ws_client:
            await self.ws_client.stop()