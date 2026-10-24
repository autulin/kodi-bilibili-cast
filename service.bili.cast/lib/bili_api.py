"""Bilibili TV API helpers used by the cast receiver.

The TV playurl endpoint and appkey/sign scheme follow the MIT-licensed Macast
nirvana plugin. The access key is supplied by the casting phone and is never
written to the Kodi log.
"""

import gzip
import hashlib
import json
import time
import urllib.parse
import urllib.request
import zlib

from .log import log

APP_KEY = "4ebafd7c4951b366"
APP_SEC = "8cb98205e9b2ad3669aad0fce12a4c13"

API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2) BiliCast/0.1",
    "Referer": "https://www.bilibili.com/client",
    "Origin": "https://www.bilibili.com",
}


class BiliApiError(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def _signed_url(base, params):
    params = dict(params)
    params["appkey"] = APP_KEY
    params["ts"] = int(time.time())
    items = sorted(params.items())
    query = "&".join(
        key + "=" + urllib.parse.quote(str(value), safe="") for key, value in items
    )
    sign = hashlib.md5((query + APP_SEC).encode("utf-8")).hexdigest()
    items.append(("sign", sign))
    query = "&".join(
        key + "=" + urllib.parse.quote(str(value), safe="") for key, value in items
    )
    return base + "?" + query


def _decode_body(raw, response):
    encoding = (response.headers.get("Content-Encoding") or "").lower()
    if encoding == "gzip":
        return gzip.decompress(raw)
    if encoding == "deflate":
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def _get_json(url, timeout=15):
    request = urllib.request.Request(url, headers=API_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = _decode_body(response.read(), response)
    return json.loads(raw.decode("utf-8"))


def get_tv_playurl(
    aid,
    cid,
    oid=None,
    epid=0,
    season_id=0,
    access_key="",
    qn=80,
    playurl_type=1,
    timeout=15,
):
    """Return a playable URL and quality metadata from the TV playurl API."""
    if oid is None:
        oid = aid
    params = {
        "access_key": access_key,
        "actionKey": "appkey",
        "appkey": APP_KEY,
        "build": 36700100,
        "cid": cid,
        "fourk": 1,
        "is_proj": 1,
        "mobile_access_key": access_key,
        "object_id": oid,
        "ogv_aid": aid,
        "platform": "ios",
        "playurl_type": playurl_type,
        "protocol": 0,
        "qn": qn,
        # Without fnval the TV API only returns a muxed durl capped at 720P.
        # fnval=4048 asks for DASH, whose video list includes 1080P even for
        # a non-logged-in projection token.
        "fnval": 4048,
        "fnver": 0,
    }
    url = _signed_url("https://api.bilibili.com/x/tv/playurl", params)
    payload = _get_json(url, timeout=timeout)
    if payload.get("code") != 0:
        raise BiliApiError(
            payload.get("message") or "playurl failed",
            payload.get("code"),
        )

    data = payload.get("data") or {}
    dash = data.get("dash") or {}
    actual_qn = data.get("quality", 0)
    if dash:
        video_ids = []
        for item in dash.get("video") or []:
            try:
                video_ids.append(int(item.get("id", 0)))
            except (TypeError, ValueError):
                continue
        if video_ids:
            actual_qn = max(video_ids)
    qn_desc = _quality_desc(data, current_qn=actual_qn, desire_qn=qn)
    result = {
        "url": None,
        "quality": actual_qn,
        "accept_quality": data.get("accept_quality", []),
        "qn_desc": qn_desc,
        "duration": 0,
        "format": None,
        "dash": dash,
        "is_login": bool(data.get("is_login", False)),
        "is_vip": bool(data.get("is_vip", False)),
        "vip_status": data.get("vip_status", 0),
    }

    durl = data.get("durl") or []
    if durl:
        first = durl[0]
        result["url"] = first.get("url")
        result["format"] = "durl"
        try:
            result["duration"] = int(first.get("length", 0)) / 1000.0
        except (TypeError, ValueError):
            result["duration"] = 0

    if dash:
        try:
            result["duration"] = float(dash.get("duration", 0))
        except (TypeError, ValueError):
            pass
        result["format"] = "dash"

    if not result["url"] and not dash:
        live = data.get("live_mobile") or {}
        if live.get("stream"):
            result["url"] = live["stream"]
            result["format"] = "live"
        live = data.get("live_stream") or {}
        for stream in live.get("flv") or []:
            result["url"] = stream
            result["format"] = "live"
            break

    if not result["url"] and not dash:
        raise BiliApiError("playurl returned no playable URL")
    return result


def _quality_desc(data, current_qn=None, desire_qn=None):
    quality = data.get("quality", 0)
    if current_qn is not None:
        quality = current_qn
    support = []
    by_qn = {}
    for item in data.get("qn_extras") or []:
        qn = item.get("qn")
        if qn is None:
            continue
        by_qn.setdefault(qn, {})
        by_qn[qn]["quality"] = qn
        by_qn[qn]["needVip"] = bool(item.get("need_vip", False))
        by_qn[qn]["needLogin"] = bool(item.get("need_login", False))
    for item in data.get("support_formats") or []:
        qn = item.get("quality")
        if qn is None:
            continue
        by_qn.setdefault(qn, {})
        by_qn[qn]["description"] = item.get("new_description", "")
        by_qn[qn]["displayDesc"] = item.get("display_desc", "")
        by_qn[qn]["superscript"] = item.get("superscript", "")
    for qn in data.get("accept_quality") or []:
        if qn not in by_qn:
            by_qn[qn] = {
                "quality": qn,
                "description": "",
                "displayDesc": "",
                "needVip": False,
                "needLogin": False,
                "superscript": "",
            }
    # Keep the API order (best quality first).  The phone uses the first
    # entry as a fallback when it has not received the actual qn yet; sorting
    # numerically would make 360P the first item and the phone would show it.
    for qn in by_qn:
        item = by_qn[qn]
        item.setdefault("description", "")
        item.setdefault("displayDesc", "")
        item.setdefault("needVip", False)
        item.setdefault("needLogin", False)
        item.setdefault("superscript", "")
        support.append(item)
    return {
        "curQn": quality,
        "supportQnList": support,
        "userDesireQn": desire_qn if desire_qn is not None else quality,
    }


def get_danmaku_xml(cid, timeout=15):
    url = "https://comment.bilibili.com/%s.xml" % cid
    request = urllib.request.Request(url, headers=API_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return _decode_body(response.read(), response)


def get_video_title(aid, timeout=10):
    try:
        url = "https://api.bilibili.com/x/web-interface/view?aid=%s" % aid
        payload = _get_json(url, timeout=timeout)
        if payload.get("code") == 0:
            return (payload.get("data") or {}).get("title", "")
    except Exception as exc:
        log("get_video_title failed: %s" % exc, "debug")
    return ""
