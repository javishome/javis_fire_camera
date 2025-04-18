from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
import asyncio
import logging
from .api import log

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]
DOMAIN = "fire_camera"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Thiết lập integration từ config entry."""
    try:
        # Kiểm tra xem ws_client đã tồn tại chưa
        camera_type = entry.data.get("camera_type")
        if camera_type == "1":
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
    """Unload a config entry."""
    # Dừng WebSocket client trước khi gỡ platform
    camera_type = entry.data.get("camera_type")
    if camera_type == "1":
        ws_client = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if ws_client:
            log("Dừng WebSocket client")
            await ws_client.stop()

    # Gỡ platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok