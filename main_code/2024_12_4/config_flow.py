import voluptuous as vol
from homeassistant import config_entries
from typing import Any, Dict, Optional
# from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv  # Import thêm để dùng cv.secret
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
import asyncio
import aiohttp
import logging
from .api import get_token, async_get_mac_address

_LOGGER = logging.getLogger(__name__)

DOMAIN = "fire_camera"

class WebSocketConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Xử lý cấu hình UI cho WebSocket Component."""
    
    data: Optional[Dict[str, Any]]
    
    async def async_step_user(self, user_input=None):
        """Bước nhập thông tin từ người dùng."""
        errors = {}

        if user_input is not None:
            camera_ip = user_input["camera_ip"]
            ws_url = f"ws://{camera_ip}:8088/"
            token = await get_token(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], camera_ip)
            if token.get("token"):
                token = token["token"]
                mac_adress = await async_get_mac_address(camera_ip, token)
                if mac_adress:
                    user_input["mac_address"] = mac_adress
                else:
                    errors["base"] = "cannot_get_mac"
            else:
                errors["base"] = errors.get("error")
                
                

            if not errors:
                self.data = user_input
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.ws_connect(ws_url, timeout=5) as ws:
                            await ws.close()    
                    return self.async_create_entry(title=user_input["camera_name"], data=self.data)
                except aiohttp.ClientError as err:
                    errors["base"] = "cannot_connect"
                    _LOGGER.error(f"⚠️ Error: {err}")
                    # self.hass.data.setdefault(DOMAIN, {})["last_error"] = str(err)
                except asyncio.TimeoutError:
                    errors["base"] = "timeout"
                    _LOGGER.error("⚠️ Timeout error: Cannot connect to WebSocket")
                except Exception as err:
                    errors["base"] = "unknown"
                    _LOGGER.error(f"⚠️ Error: {err}")
                    
                    self.hass.data.setdefault(DOMAIN, {})["last_error"] = str(err)
            

        data_schema = vol.Schema({
            vol.Required("camera_name"): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,  # 🔒 Ẩn mật khẩu
            vol.Required("camera_ip"): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)



