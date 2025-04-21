import voluptuous as vol
from homeassistant import config_entries
from typing import Any, Dict, Optional
# from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv  # Import thêm để dùng cv.secret
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
import asyncio
import aiohttp
from .api import get_token_1, get_mac_address_1, get_token_2, get_mac_address_2
from .const import log, DOMAIN

class WebSocketConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Xử lý cấu hình UI cho WebSocket Component."""
    
    data: Optional[Dict[str, Any]]
    
    async def async_step_user(self, user_input=None):
        """Bước nhập thông tin từ người dùng."""
        errors = {}

        if user_input is not None:
            # camera type 1
            camera_ip = user_input["camera_ip"]
            if user_input["camera_type"] == "1":
                ws_url = f"ws://{camera_ip}:8088/"
                token = await get_token_1(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], camera_ip)
                if token.get("token"):
                    token = token["token"]
                    mac_adress = await get_mac_address_1(camera_ip, token)
                    if mac_adress:
                        user_input["mac_address"] = mac_adress
                        user_input["token"] = token
                    else:
                        errors["base"] = "cannot_get_mac"
                else:
                    errors["base"] = token.get("error")
            if user_input["camera_type"] == "2":
                token = await get_token_2(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], camera_ip)
                if token.get("token"):
                    token = token["token"]
                    mac_adress = await get_mac_address_2(camera_ip, token)
                    if mac_adress:
                        user_input["mac_address"] = mac_adress
                        user_input["token"] = token
                    else:
                        errors["base"] = "cannot_get_mac"
                else:
                    errors["base"] = token.get("error")

            if not errors:
                # Kiểm tra trùng tên hoặc MAC address
                for entry in self._async_current_entries():
                    log(f"Checking entry: {entry.data}")
                    if entry.data.get("camera_name") == user_input["camera_name"]:
                        errors["base"] = "name_exists"
                        break
                    if entry.data.get("mac_address") == user_input["mac_address"]:
                        errors["base"] = "mac_exists"
                        break
                
            if not errors:
                self.data = user_input
                try:
                    if user_input["camera_type"] == "1":
                        async with aiohttp.ClientSession() as session:
                            async with session.ws_connect(ws_url, timeout=5) as ws:
                                await ws.close()    
                    return self.async_create_entry(title=user_input["camera_name"], data=self.data)
                except aiohttp.ClientError as err:
                    errors["base"] = "cannot_connect"
                    log(f"⚠️ Error: {err}", type="error")
                    # self.hass.data.setdefault(DOMAIN, {})["last_error"] = str(err)
                except asyncio.TimeoutError:
                    errors["base"] = "timeout"
                    log("⚠️ Timeout error: Cannot connect to WebSocket", type="error")
                except Exception as err:
                    errors["base"] = "unknown"
                    log(f"⚠️ Error: {err}", type="error")
                    
                    self.hass.data.setdefault(DOMAIN, {})["last_error"] = str(err)
            

        data_schema = vol.Schema({
            vol.Required("camera_name"): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,  # 🔒 Ẩn mật khẩu
            vol.Required("camera_ip"): str,
            vol.Required("camera_type"): vol.In(["1", "2"]),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)



