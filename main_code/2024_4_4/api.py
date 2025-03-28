
import aiohttp
import logging
import json
_LOGGER = logging.getLogger(__name__)


async def async_get_mac_address(camera_ip, token):
    """Lấy địa chỉ MAC từ API của camera."""
    url = f"http://{camera_ip}/cgi-bin/vs_cgi_v2?act=cfg_get&name=version"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Connection": "keep-alive",
        "Referer": f"http://{camera_ip}/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "x-access-token": token
    }
    cookies = {"token": token}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, cookies=cookies, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.info(f"✅ Received data: {data}")
                    mac_address = data.get("data").get("mac")
                    _LOGGER.info(f"✅ MAC Address: {mac_address}")
                    return mac_address
                else:
                    _LOGGER.error(f"❌ Failed to get MAC Address. Status Code: {response.status}")
    except Exception as e:
        _LOGGER.error(f"❌ Error getting MAC Address: {e}")

    return None

async def get_token(user: str, password: str, camera_ip: str) -> str:
    """Hàm đăng nhập và lấy token từ API."""
    url = f"http://{camera_ip}/cgi-bin/vs_cgi_v2?act=login"
    payload = {
        "user": user,
        "pass": password
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=payload) as response:
                if response.status == 200:
                    text_response = await response.text()  # Lấy nội dung dưới dạng text
                    result = json.loads(text_response)  # Tự decode JSON
                    token = result.get("token")
                    check = result.get("check")
                    if check == 1:
                        if token:
                            _LOGGER.info("Đăng nhập thành công!")
                            return token
                        else:
                            _LOGGER.info("Không nhận được token từ API.")
                    else:
                        _LOGGER.info(f"Đăng nhập thất bại! kiểm tra lại tài khoản hoặc mật khẩu.")
                else:
                    _LOGGER.info(f"Đăng nhập thất bại! Mã lỗi: {response.status}")
        except aiohttp.ClientError as e:
            _LOGGER.info(f"Lỗi kết nối đến API: {e}")

    return None
