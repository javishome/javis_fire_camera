from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
import asyncio
from .const import DOMAIN, log, CAMERA_TYPES_DISPLAY
from homeassistant.helpers import entity_registry as er
from .config_flow import WebSocketOptionsFlow

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Thiết lập integration từ config entry."""
    try:
        # Xóa entity cũ trước
        entity_registry = er.async_get(hass)
        for entity in list(entity_registry.entities.values()):
            if entity.config_entry_id == entry.entry_id:
                log(f"🗑️ Removing old entity: {entity.entity_id}")
                entity_registry.async_remove(entity.entity_id)

        # Kiểm tra xem ws_client đã tồn tại chưa
        camera_type = entry.options.get("camera_type", entry.data.get("camera_type"))
        if camera_type == list(CAMERA_TYPES_DISPLAY.keys())[0]:
            if hass.data.get(DOMAIN, {}).get(entry.entry_id) and hass.data.get(DOMAIN, {}).get(entry.entry_id).get("ws_client"):
                ws_client = hass.data.get(DOMAIN, {}).get(entry.entry_id).get("ws_client")
                if ws_client:
                    # Nếu ws_client đã tồn tại, dừng nó trước khi tạo mới
                    log("Xóa ws_client cũ")
                    await ws_client.stop()

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True
    except asyncio.CancelledError:
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and remove its entities."""
    # Stop WebSocket client
    try:
        camera_type = entry.options.get("camera_type", entry.data.get("camera_type"))
        if camera_type == list(CAMERA_TYPES_DISPLAY.keys())[0]:
            if hass.data.get(DOMAIN, {}).get(entry.entry_id) and hass.data.get(DOMAIN, {}).get(entry.entry_id).get("ws_client"):
                ws_client = hass.data.get(DOMAIN, {}).get(entry.entry_id).get("ws_client")
                if ws_client:
                    log("Dừng WebSocket client")
                    await ws_client.stop()

        if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
            if DOMAIN in hass.data:
                hass.data[DOMAIN].pop(entry.entry_id, None)

        return unload_ok
    except Exception as e:
        log(f"Lỗi khi unload: {e}")
        return False

async def async_get_options_flow(config_entry):
    return WebSocketOptionsFlow(config_entry)