"""Logging that works both inside Kodi and in a plain Python process."""

import logging

try:  # Kodi injects xbmc into the addon runtime.
    import xbmc  # type: ignore

    _HAS_XBMC = True
except Exception:  # pragma: no cover - exercised on a developer machine
    xbmc = None  # type: ignore
    _HAS_XBMC = False
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

_VALID_LEVELS = ("debug", "info", "warning", "error")


def log(message, level="info"):
    """Write a message to Kodi's log, or to stderr outside Kodi."""
    level = str(level).lower()
    if level not in _VALID_LEVELS:
        level = "info"

    if _HAS_XBMC:
        kodi_level = {
            "debug": xbmc.LOGDEBUG,
            "info": xbmc.LOGINFO,
            "warning": xbmc.LOGWARNING,
            "error": xbmc.LOGERROR,
        }[level]
        xbmc.log("[service.bili.cast] " + str(message), kodi_level)
        return

    py_level = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }[level]
    logging.log(py_level, str(message))
