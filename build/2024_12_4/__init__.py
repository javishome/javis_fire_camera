from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]
# async def async_setup(hass: HomeAssistant) -> bool:
#     """Thiết lập integration (không cần thiết nếu chỉ dùng config entry)."""
#     return True
DOMAIN = "fire_camera"
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Thiết lập integration từ config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    return unload_ok
