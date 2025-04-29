import voluptuous as vol
from homeassistant import config_entries
from typing import Any, Dict, Optional
# from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv  # Import thêm để dùng cv.secret
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
import asyncio
import aiohttp
from .api import get_token_1, get_mac_address_1, get_token_2, get_mac_address_2
from .const import log, DOMAIN, CAMERA_TYPES_DISPLAY

class WebSocketConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Xử lý cấu hình UI cho WebSocket Component."""
    
    data: Optional[Dict[str, Any]]
    
    async def async_step_user(self, user_input=None):
        """Bước nhập thông tin từ người dùng."""
        errors = {}

        if user_input is not None:
            # camera type 1
            camera_ip = user_input["camera_ip"]
            if user_input["camera_type"] == list(CAMERA_TYPES_DISPLAY.keys())[0]:
                ws_url = f"ws://{camera_ip}:8088/"
                token = await get_token_1(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], camera_ip)
                if token.get("token"):
                    token = token["token"]
                    mac_address = await get_mac_address_1(camera_ip, token)
                    if mac_address:
                        user_input["mac_address"] = mac_address
                        user_input["token"] = token
                    else:
                        errors["base"] = "cannot_get_mac"
                else:
                    errors["base"] = token.get("error")
            if user_input["camera_type"] == list(CAMERA_TYPES_DISPLAY.keys())[1]:
                token = await get_token_2(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], camera_ip)
                if token.get("token"):
                    token = token["token"]
                    mac_address = await get_mac_address_2(camera_ip, token)
                    if mac_address:
                        user_input["mac_address"] = mac_address
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
                    if user_input["camera_type"] == list(CAMERA_TYPES_DISPLAY.keys())[0]:
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
            vol.Required("camera_type"): vol.In(CAMERA_TYPES_DISPLAY),
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
    
    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler for this config entry."""
        return WebSocketOptionsFlow(config_entry)

class WebSocketOptionsFlow(config_entries.OptionsFlow):
    """Handle options for WebSocket Component."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        errors = {}

        # Giá trị mặc định lấy từ config_entry.data nếu options chưa có
        data = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            # Nếu user nhập thông tin, validate
            log(f"User input: {user_input}")
            new_camera_ip = user_input["camera_ip"]
            new_username = user_input[CONF_USERNAME]
            new_password = user_input[CONF_PASSWORD]
            new_camera_type = user_input["camera_type"]

            # mac_address = None

            try:
                if new_camera_type == list(CAMERA_TYPES_DISPLAY.keys())[0]:
                    ws_url = f"ws://{new_camera_ip}:8088/"
                    token_data = await get_token_1(new_username, new_password, new_camera_ip)
                    if token_data.get("token"):
                        token = token_data["token"]
                        mac_address = await get_mac_address_1(new_camera_ip, token)
                        if mac_address: 
                            user_input["mac_address"] = mac_address
                        else:
                            errors["base"] = "cannot_get_mac"
                    else:
                        errors["base"] = token_data.get("error", "unknow")
                elif new_camera_type == list(CAMERA_TYPES_DISPLAY.keys())[1]:
                    token_data = await get_token_2(new_username, new_password, new_camera_ip)
                    if token_data.get("token"):
                        token = token_data["token"]
                        mac_address = await get_mac_address_2(new_camera_ip, token)
                        if mac_address: 
                            user_input["mac_address"] = mac_address
                        else:
                            errors["base"] = "cannot_get_mac"
                    else:
                        errors["base"] = token_data.get("error", "unknow")
            except Exception as e:
                log(f"⚠️ Error during MAC checking: {e}", type="error")
                errors["base"] = "cannot_connect"

            if not errors:
                self.data = user_input
                try:
                    if user_input["camera_type"] == list(CAMERA_TYPES_DISPLAY.keys())[0]:
                        async with aiohttp.ClientSession() as session:
                            async with session.ws_connect(ws_url, timeout=5) as ws:
                                await ws.close()    
                    log("✅ WebSocket connection successful")
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        title=user_input["camera_name"],  # Cập nhật title
                        options=user_input,                # Cập nhật options
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    return self.async_abort(reason="options_updated")
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
                # Nếu OK thì lưu options mới

        # UI cho user chỉnh
        options_schema = vol.Schema({
            vol.Required("camera_name", default=data.get("camera_name")): str,
            vol.Required(CONF_USERNAME, default=data.get(CONF_USERNAME)): str,
            vol.Required(CONF_PASSWORD, default=data.get(CONF_PASSWORD)): str,
            vol.Required("camera_ip", default=data.get("camera_ip")): str,
            vol.Required("camera_type", default=data.get("camera_type")): vol.In(CAMERA_TYPES_DISPLAY),
        })

        return self.async_show_form(step_id="init", data_schema=options_schema, errors=errors)


