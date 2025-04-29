
import aiohttp
import logging
import json
import asyncio
import base64
import socket
from .const import DOMAIN, log



async def get_mac_address_1(camera_ip, token):
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
        timeout = aiohttp.ClientTimeout(total=2)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, cookies=cookies, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    log(f"✅ Received data: {data}")
                    mac_address = data.get("data").get("mac")
                    log(f"✅ MAC Address: {mac_address}")
                    return mac_address
                else:
                    log(f"❌ Failed to get MAC Address. Status Code: {response.status}", type="error")
    except asyncio.TimeoutError:
        log("Yêu cầu đăng nhập vượt quá thời gian chờ.")
        return None
    except aiohttp.ClientError as e:
        log(f"Lỗi kết nối đến API: {e}")
        return None
    except Exception as e:
        log(f"Lỗi không xác định: {e}")
        return None

    return None



async def get_token_1(user: str, password: str, camera_ip: str) -> str:
    """Hàm đăng nhập và lấy token từ API."""
    url = f"http://{camera_ip}/cgi-bin/vs_cgi_v2?act=login"
    payload = {
        "user": user,
        "pass": password
    }
    timeout = aiohttp.ClientTimeout(total=2)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, data=payload) as response:
                if response.status == 200:
                    text_response = await response.text()  # Lấy nội dung dưới dạng text
                    result = json.loads(text_response)  # Tự decode JSON
                    token = result.get("token")
                    check = result.get("check")
                    if check == 1:
                        if token:
                            log("Đăng nhập thành công!")
                            return {"token": token}
                        else:
                            log("Không nhận được token từ API.")
                            return {"error": "no_token"}
                    else:
                        log(f"Đăng nhập thất bại! kiểm tra lại tài khoản hoặc mật khẩu.")
                        return {"error": "login_failed"}
                else:
                    log(f"Đăng nhập thất bại! Mã lỗi: {response.status}")

        except asyncio.TimeoutError:
            log("Yêu cầu đăng nhập vượt quá thời gian chờ.")
            return {"error": "timeout"}
        except aiohttp.ClientError as e:
            log(f"Lỗi kết nối đến API: {e}")
            return {"error": "url_error"}
        except Exception as e:
            log(f"Lỗi không xác định: {e}")
            return {"error": "unknown"}

    return {"error": "unknown"}

async def get_token_2(user: str, password: str, camera_ip: str) -> dict:
    """Hàm đăng nhập và lấy token từ API sử dụng Basic Auth (phiên bản async)."""
    if not user or not password:
        return {"error": "Missing username or password"}

    credentials = f"{user}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    url = f"http://{camera_ip}/api/login"
    headers = {
        "Authorization": f"Basic {encoded_credentials}"
    }

    timeout = aiohttp.ClientTimeout(total=3)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, headers=headers) as response:
                if response.status == 200:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                        token = data.get("token")
                        if token:
                            return {"token": token}
                        else:
                            return {"error": "no_token"}
                    except Exception as e:
                        log(f"Error: {e}", type="error")
                        return {"error": "login_failed"}
                else:
                    return {"error": "login_failed"}
        except asyncio.TimeoutError:
            return {"error": "timeout"}
        except aiohttp.ClientError as e:
            log(f"Error: {e}", type="error")
            return {"error": "url_error"}
        except Exception as e:
            log(f"Error: {e}", type="error")
            return {"error": "unknown"}
        
async def get_mac_address_2(camera_ip, token):
    url = f"http://{camera_ip}/api/network/config"
    payload = json.dumps({
        "id": "GSF_ID_BSP_ETH",
        "op": "G0C0S0",
    })
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        timeout = aiohttp.ClientTimeout(total=2)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, data=payload, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    log(f"✅ Received data: {data}")
                    mac_address = data.get("data", {}).get("mac")
                    log(f"✅ MAC Address: {mac_address}")
                    return mac_address
                else:
                    log(f"❌ Failed to get MAC Address. Status Code: {response.status}", type="error")
    except asyncio.TimeoutError:
        log("Yêu cầu vượt quá thời gian chờ.")
    except aiohttp.ClientError as e:
        log(f"Lỗi kết nối đến API: {e}")
    except Exception as e:
        log(f"Lỗi không xác định: {e}")

    return None

async def get_local_ip() -> str:
    """Lấy địa chỉ IP thật gắn với mạng LAN của host (không phải IP Docker)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.1.1", 80))  # Thay bằng gateway mạng nội bộ nếu cần
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        log(f"❌ Không thể lấy địa chỉ IP: {e}", type="warning")
        return "127.0.0.1"

async def get_webhook_url(local_ip, webhook_id):
    webhook_url = f"http://{local_ip}:8123/api/webhook/{webhook_id}"
    return webhook_url


async def set_callback_url(camera_ip, token, call_back_url):
    url = f"http://{camera_ip}/api/network/config"

    payload = json.dumps({
        "id": "GSF_ID_IOT_CUSTOM",
        "op": "G1C0S0",
        "data": {
            "url": call_back_url,
            "enable":1,
            "extend_header":"",
            "msg_type":1,
            "date_format":"%Y-%m-%d %X",
            "msg_frame":0,
            "msg_format":"{\"device_id\":\"((DEVICE_ID))\",\"device_version\":\"((DEVICE_VERSION))\",\"date\":\"((DATE_FORMAT))\",\"timestamp\":((TIMESTAMP)),\"label\":\"((LABEL))\",\"alias\":\"((ALIAS))\",\"count\":((COUNT)),\"img_base64\":\"((BASE64_IMAGE))\",\"extend\":{((EXTEND))}}","layTableCheckbox":"on"
        }
    })

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    try:
        timeout = aiohttp.ClientTimeout(total=2)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, data=payload, ssl=False) as response:
                if response.status == 200:
                    log(f"✅ Đăng ký URL thành công: {call_back_url}")
                    return True
                else:
                    log(f"❌ Đăng ký URL thất bại. Mã lỗi: {response.status}", type="error")
    except asyncio.TimeoutError:
        log("Yêu cầu vượt quá thời gian chờ.")
    except aiohttp.ClientError as e:
        log(f"Lỗi kết nối đến API: {e}")
    except Exception as e:
        log(f"Lỗi không xác định: {e}")

    return False


async def handle_webhook(hass, webhook_id, request):
    try:
        data = await request.json()
        label = data.get("label")
        log(f"📩 Webhook received: {label}")

        # Tìm cảm biến theo entry_id

        for entry_id, sensor_dict in hass.data[DOMAIN].items():
            if isinstance(sensor_dict, dict):
                sensors = sensor_dict.get("sensors")
                if not sensors:
                    continue
                sensor = sensors.get(label)
                if sensor:
                    await sensor.receive_ws_data({"event": label})
                    return
        log(f"❌ Không tìm thấy cảm biến cho webhook: {webhook_id}", type="warning")
    except Exception as e:
        log(f"❌ Lỗi trong xử lý webhook: {e}", type="error")
