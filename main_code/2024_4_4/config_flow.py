import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
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

    async def async_step_user(self, user_input=None):
        """Bước nhập thông tin từ người dùng."""
        errors = {}

        if user_input is not None:
            camera_ip = user_input["camera_ip"]
            ws_url = f"ws://{camera_ip}:8088/"
            token = await get_token(user_input[CONF_USERNAME], user_input[CONF_PASSWORD], camera_ip)
            if not token:
                errors["base"] = "invalid_credentials"
            mac_adress = await async_get_mac_address(camera_ip, token)
            if not mac_adress:
                errors["base"] = "cannot_get_mac"
            user_input["mac_address"] = mac_adress

            if not errors:
                # Kiểm tra kết nối WebSocket
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.ws_connect(ws_url, timeout=5) as ws:
                            await ws.close()    
                    # Nếu không có lỗi, cập nhật cấu hình
                    # self.hass.config_entries.async_update_entry(
                    #     self.config_entry, data=user_input
                    # )
                    return self.async_create_entry(title="WebSocket Sensor", data=user_input)
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
                    
                    # self.hass.data.setdefault(DOMAIN, {})["last_error"] = str(err)
            

        data_schema = vol.Schema({
            vol.Required("camera_name"): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,  # 🔒 Ẩn mật khẩu
            vol.Required("camera_ip"): str,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Cho phép chỉnh sửa URL sau khi đã cấu hình."""
        return WebSocketOptionsFlowHandler(config_entry)

class WebSocketOptionsFlowHandler(config_entries.OptionsFlow):
    """Xử lý chỉnh sửa cấu hình sau khi đã thêm vào Home Assistant."""

    def __init__(self, config_entry):
        """Lưu lại cấu hình hiện tại."""
        self.config_entry = config_entry

