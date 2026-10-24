"""Persist the stable TV UUID in Kodi's addon_data directory."""

import os

from .net import make_tv_uuid

try:
    import xbmcvfs  # type: ignore
except Exception:  # pragma: no cover
    xbmcvfs = None


def addon_data_dir():
    if xbmcvfs is not None:
        path = xbmcvfs.translatePath(
            "special://profile/addon_data/service.bili.cast/"
        )
        try:
            if not xbmcvfs.exists(path):
                xbmcvfs.mkdirs(path)
        except Exception:
            pass
        if xbmcvfs.exists(path):
            return path

    path = os.path.join(os.path.expanduser("~"), ".kodi-bili-cast")
    os.makedirs(path, exist_ok=True)
    return path


def load_or_create_uuid():
    path = os.path.join(addon_data_dir(), "device_uuid")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
        if value:
            return value
    except OSError:
        pass

    value = make_tv_uuid()
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(value)
    except OSError:
        pass
    return value
