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
        # Kiểm tra xem ws_client đã tồn tại chưa
        camera_type = entry.options.get("camera_type", entry.data.get("camera_type"))
        if camera_type == list(CAMERA_TYPES_DISPLAY.keys())[0]:
            ws_client = hass.data.get(DOMAIN, {}).get(entry.entry_id)
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
    camera_type = entry.options.get("camera_type", entry.data.get("camera_type"))
    if camera_type == list(CAMERA_TYPES_DISPLAY.keys())[0]:
        ws_client = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if ws_client:
            log("Dừng WebSocket client")
            await ws_client.stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if DOMAIN in hass.data:
            hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok

async def async_get_options_flow(config_entry):
    return WebSocketOptionsFlow(config_entry)