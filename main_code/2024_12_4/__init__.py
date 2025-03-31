from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
import asyncio
import logging
_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]
DOMAIN = "fire_camera"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Thiết lập integration từ config entry."""
    try:
        # Kiểm tra xem ws_client đã tồn tại chưa
        ws_client = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if ws_client:
            # Nếu ws_client đã tồn tại, dừng nó trước khi tạo mới
            _LOGGER.info("Xóa ws_client cũ")
            await ws_client.stop()

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True
    except asyncio.CancelledError:
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Dừng WebSocket client trước khi gỡ platform
    ws_client = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if ws_client:
        _LOGGER.info("stop khi reload custom component")
        await ws_client.stop(shutdown=False)  # Không ghi log "stopped" khi reload

    # Gỡ platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok