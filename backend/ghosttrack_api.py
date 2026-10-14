"""GhostTrack web adapter. Does not import or execute the interactive upstream CLI."""
import ipaddress
import re
import threading
import time
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone as dt_timezone
from urllib.parse import quote

import httpx
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ghosttrack", tags=["GhostTrack"])
_lock = threading.Lock()
_visits = OrderedDict()
_jobs = threading.BoundedSemaphore(3)
PROVIDERS = [
    ("Facebook", "https://www.facebook.com/{}"),
    ("X / Twitter", "https://www.twitter.com/{}"),
    ("Instagram", "https://www.instagram.com/{}"),
    ("LinkedIn", "https://www.linkedin.com/in/{}"),
    ("GitHub", "https://www.github.com/{}"),
    ("Pinterest", "https://www.pinterest.com/{}"),
    ("Tumblr", "https://www.tumblr.com/{}"),
    ("YouTube", "https://www.youtube.com/{}"),
    ("SoundCloud", "https://soundcloud.com/{}"),
    ("Snapchat", "https://www.snapchat.com/add/{}"),
    ("TikTok", "https://www.tiktok.com/@{}"),
    ("Behance", "https://www.behance.net/{}"),
    ("Medium", "https://www.medium.com/@{}"),
    ("Quora", "https://www.quora.com/profile/{}"),
    ("Flickr", "https://www.flickr.com/people/{}"),
    ("Twitch", "https://www.twitch.tv/{}"),
    ("Dribbble", "https://www.dribbble.com/{}"),
    ("Product Hunt", "https://www.producthunt.com/@{}"),
    ("Telegram", "https://www.telegram.me/{}"),
]


class Query(BaseModel):
    model_config = {"extra": "forbid"}
    value: str = Field(min_length=1, max_length=100)
    region: str = Field(default="CN", min_length=2, max_length=2)


def budget(request: Request):
    # Direct peer only: forwarded headers are not trusted as rate-limit keys.
    peer = request.client.host if request.client else "local"
    now = time.monotonic()
    with _lock:
        for key in list(_visits):
            if not _visits[key] or now - _visits[key][-1] >= 60:
                del _visits[key]
        history = _visits.setdefault(peer, deque())
        while history and now - history[0] >= 60:
            history.popleft()
        if len(history) >= 8:
            raise HTTPException(429, "查询过于频繁，每分钟最多 8 次。", headers={"Retry-After": "60"})
        history.append(now)
        if len(_visits) > 4096:
            _visits.popitem(last=False)
    if not _jobs.acquire(blocking=False):
        raise HTTPException(429, "查询服务忙，请稍后重试。")
    try:
        yield
    finally:
        _jobs.release()


def stamp():
    return datetime.now(dt_timezone.utc).isoformat()


def ip_lookup(value):
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        raise HTTPException(422, "请输入有效的 IPv4 或 IPv6 地址。")
    if not address.is_global or address.is_multicast:
        raise HTTPException(422, "仅支持公网 IP，内网、回环和保留地址没有可用的地理归属。")
    try:
        response = httpx.get(f"https://ipwho.is/{address}", timeout=10, follow_redirects=False)
        if response.status_code == 429:
            delay = response.headers.get("Retry-After", "")
            headers = {"Retry-After": delay} if delay.isdigit() and len(delay) <= 8 else {}
            raise HTTPException(429, "IP 数据源免费额度或请求频率已达上限，请稍后再试；不会切换付费服务。", headers=headers)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "IP 数据源暂不可用，请检查网络后重试。")
    if not isinstance(data, dict) or data.get("success") is not True:
        raise HTTPException(502, "IP 数据源未返回可用记录。")
    fields = ("ip", "type", "country", "country_code", "region", "city", "continent", "latitude", "longitude", "postal", "connection", "timezone")
    result = {key: data.get(key) for key in fields}
    lat, lon = data.get("latitude"), data.get("longitude")
    result["maps_url"] = None
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and -90 <= lat <= 90 and -180 <= lon <= 180:
        result["maps_url"] = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=8/{lat}/{lon}"
    return {"kind": "ip", "source": "ipwho.is", "queried_at": stamp(), "data": result}


def phone_lookup(value, region="CN"):
    region = region.upper()
    if region not in phonenumbers.SUPPORTED_REGIONS:
        raise HTTPException(422, "请输入有效的两位国家地区代码，例如 CN、US、GB。")
    value = value.strip()
    if not re.fullmatch(r"\+?[\d ()-]{3,40}", value):
        raise HTTPException(422, "号码仅支持数字、前导 +、空格、括号和短横线。")
    try:
        number = phonenumbers.parse(value, region)
    except phonenumbers.NumberParseException:
        raise HTTPException(422, "无法解析该号码，请检查国家代码和长度。")
    types = {0: "固定电话", 1: "手机", 2: "固话或手机", 3: "免费电话", 4: "付费服务", 5: "共享费用", 6: "网络电话", 7: "个人号码", 8: "寻呼机", 9: "通用接入", 10: "语音信箱", 99: "未知"}
    return {"kind": "phone", "source": f"phonenumbers {phonenumbers.__version__} / libphonenumber 离线元数据", "queried_at": stamp(), "data": {
        "international": phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "e164": phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164),
        "national": phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.NATIONAL),
        "region_code": phonenumbers.region_code_for_number(number), "country_code": number.country_code,
        "description": geocoder.description_for_number(number, "zh"),
        "carrier": carrier.name_for_number(number, "zh"),
        "timezones": list(timezone.time_zones_for_number(number)),
        "valid": phonenumbers.is_valid_number(number), "possible": phonenumbers.is_possible_number(number),
        "type": types.get(phonenumbers.number_type(number), "未知"),
    }}


def check_profile(client, provider, username):
    name, pattern = provider
    url = pattern.format(quote(username, safe=""))
    result = {"name": name, "url": url, "status": "unknown", "http_status": None}
    try:
        # Do not download response bodies or follow arbitrary redirects.
        with client.stream("GET", url) as response:
            code = response.status_code
            result["http_status"] = code
            if code == 200:
                result["status"] = "reachable"
            elif code in (404, 410):
                result["status"] = "not_found"
            elif code in (401, 403, 429):
                result["status"] = "restricted"
            elif 300 <= code < 400:
                result["status"] = "redirect"
    except httpx.HTTPError:
        result["status"] = "network_error"
    return result


def username_lookup(value):
    username = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,39}", username):
        raise HTTPException(422, "用户名限 1–40 位英文字母、数字、下划线、点和短横线，首位为字母、数字或下划线。")
    with httpx.Client(timeout=httpx.Timeout(5), follow_redirects=False, headers={"User-Agent": "GhostTrack-Web/1.0 (public profile check)"}) as client:
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda site: check_profile(client, site, username), PROVIDERS))
    return {"kind": "username", "source": "公开个人页 HTTP 响应；不验证身份", "queried_at": stamp(), "data": {"username": username, "profiles": results}}


@router.get("/health")
def health():
    return {"status": "ok", "phone_metadata": phonenumbers.__version__, "platforms": len(PROVIDERS)}


@router.post("/ip", dependencies=[Depends(budget)])
def query_ip(query: Query):
    return ip_lookup(query.value)


@router.post("/phone", dependencies=[Depends(budget)])
def query_phone(query: Query):
    return phone_lookup(query.value, query.region)


@router.post("/username", dependencies=[Depends(budget)])
def query_username(query: Query):
    return username_lookup(query.value)
