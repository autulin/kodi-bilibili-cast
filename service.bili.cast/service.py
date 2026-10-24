"""Kodi service entry point for the Bilibili NVA/DLNA receiver."""

import xbmc
import xbmcaddon

from lib.device import DeviceInfo
from lib.log import log
from lib.player import KodiPlayer
from lib.server import BiliCastServer
from lib.storage import load_or_create_uuid


def _read_settings(addon):
    try:
        port = int(addon.getSetting("port") or "9958")
    except (TypeError, ValueError):
        port = 9958
    friendly_name = addon.getSetting("friendly_name") or "我的小电视"
    enable_ssdp = addon.getSetting("enable_ssdp").lower() != "false"
    disable_surface = addon.getSetting("compat_disable_surface").lower() != "false"
    return port, friendly_name, enable_ssdp, disable_surface


def _is_android():
    try:
        return bool(xbmc.getCondVisibility("System.Platform.Android"))
    except Exception:
        return False


def _apply_compat_settings(disable_surface):
    """Work around the N1's broken MediaCodec surface teardown.

    With ``videoplayer.usemediacodecsurface=true`` the Amlogic decoder closes
    the video a few seconds after start and Kodi tears down its window, which
    looks like a freeze/black screen.  Setting it to false keeps playback and
    stop stable.

    This only applies to Android.  CoreELEC/LibreELEC use the Amlogic decoder
    directly and do not have this setting; touching it there would just log a
    false success.
    """
    if not disable_surface:
        return
    if not _is_android():
        log("compat: not Android, skip MediaCodec surface setting", "debug")
        return
    try:
        import json
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Settings.SetSettingValue",
            "params": {
                "setting": "videoplayer.usemediacodecsurface",
                "value": False,
            },
        }
        xbmc.executeJSONRPC(json.dumps(payload))
        log("compat: disabled videoplayer.usemediacodecsurface", "info")
    except Exception as exc:
        log("compat setting failed: %s" % exc, "warning")


def _read_danmaku_settings(addon):
    area_raw = addon.getSetting("danmaku_area") or "0"
    area_map = {
        "0": 0.25, "1": 0.5, "2": 0.75, "3": 1.0,
        "1/4": 0.25, "1/2": 0.5, "3/4": 0.75,
        "1/4 屏": 0.25, "1/2 屏": 0.5, "3/4 屏": 0.75,
        "全屏": 1.0,
    }
    try:
        area = area_map.get(str(area_raw), 0.25)
    except Exception:
        area = 0.25

    def _int_setting(key, default, low, high):
        try:
            value = int(float(addon.getSetting(key) or default))
        except (TypeError, ValueError):
            value = default
        return max(low, min(high, value))

    return {
        "area": area,
        "font_size": _int_setting("danmaku_font_size", 48, 20, 96),
        "opacity": _int_setting("danmaku_opacity", 85, 10, 100) / 100.0,
        "max_lines": _int_setting("danmaku_max_lines", 4, 1, 20),
    }


def main():
    addon = xbmcaddon.Addon()
    port, friendly_name, enable_ssdp, disable_surface = _read_settings(addon)
    _apply_compat_settings(disable_surface)
    danmaku_settings = _read_danmaku_settings(addon)
    version = addon.getAddonInfo("version") or "0.1.0"
    device = DeviceInfo(
        uuid=load_or_create_uuid(),
        friendly_name=friendly_name,
        version=version,
    )

    log(
        "starting %s (%s), port=%s, ssdp=%s, danmaku=%s"
        % (
            addon.getAddonInfo("name"),
            version,
            port,
            enable_ssdp,
            danmaku_settings,
        ),
        "info",
    )
    player = KodiPlayer(addon=addon)
    server = BiliCastServer(
        device=device,
        port=port,
        enable_ssdp=enable_ssdp,
        logger=log,
        player=player,
        danmaku_settings=danmaku_settings,
    )
    try:
        server.start()
    except Exception as exc:
        log("server start failed: %s" % exc, "error")
        return

    monitor = xbmc.Monitor()
    try:
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                break
    finally:
        server.stop()
        log("service stopped", "info")


if __name__ == "__main__":
    main()
