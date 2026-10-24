"""Thin wrapper around Kodi's Player API.

This module is only imported inside Kodi; the developer server uses the
simulated path in lib/server.py instead.
"""

import json
import threading
import time

import xbmc
import xbmcgui

from .log import log


class KodiPlayer:
    def __init__(self, addon=None):
        self.addon = addon
        self.player = xbmc.Player()
        self._subtitle_path = None
        self._subtitle_visible = True

    # ---------------------------------------------------------------- playback
    def play(self, url, title="Bilibili", seek_seconds=0, subtitles=None,
             danmaku_open=True, headers=None, dash=False):
        item = xbmcgui.ListItem(label=title, path=url)
        try:
            item.setInfo("video", {"title": title})
            if dash:
                item.setMimeType("application/dash+xml")
                item.setProperty("inputstream", "inputstream.adaptive")
                item.setProperty("inputstream.adaptive.manifest_type", "mpd")
            else:
                item.setMimeType("video/mp4")
            item.setContentLookup(False)
        except Exception:
            pass

        if headers:
            try:
                item.setProperty("inputstream", "inputstream.ffmpegdirect")
                item.setProperty(
                    "inputstream.ffmpegdirect.stream_headers",
                    "&".join("%s=%s" % (key, value) for key, value in headers.items()),
                )
            except Exception:
                pass

        log("Kodi play: %s" % url.split("?")[0], "info")
        try:
            # Kodi supports startpos in seconds; use it so a resumed cast does
            # not flash the beginning of the video before the fallback seek.
            self.player.play(url, item, startpos=int(seek_seconds or -1))
        except Exception:
            self.player.play(url, item)
        self._subtitle_path = subtitles
        self._subtitle_visible = bool(danmaku_open)
        if seek_seconds:
            threading.Thread(
                target=self._seek_when_ready,
                args=(float(seek_seconds),),
                name="BiliCast-Seek",
                daemon=True,
            ).start()
        if subtitles:
            threading.Thread(
                target=self._set_subtitles_when_ready,
                args=(subtitles, danmaku_open),
                name="BiliCast-Subtitles",
                daemon=True,
            ).start()

    def _wait_until_active(self, timeout=30.0, need_duration=False):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                active = self.player.isPlaying() or bool(
                    xbmc.getCondVisibility("Player.Paused")
                )
                if active and (not need_duration or self.player.getTotalTime() > 0):
                    return True
            except Exception:
                pass
            time.sleep(0.25)
        return False

    def _seek_when_ready(self, seconds):
        if self._wait_until_active(30.0, need_duration=True):
            # Give the demuxer a moment to become seekable.
            time.sleep(1.0)
            try:
                self.player.seekTime(seconds)
                log("Kodi seek to %.1fs" % seconds, "info")
            except Exception as exc:
                log("Kodi seek failed: %s" % exc, "warning")

    def _set_subtitles_when_ready(self, path, visible):
        if self._wait_until_active(30.0):
            self.set_subtitles(path, visible)

    def queue_subtitles(self, path, visible=True):
        """Set subtitles once Kodi has an active player."""
        threading.Thread(
            target=self._set_subtitles_when_ready,
            args=(path, visible),
            name="BiliCast-QueueSubtitles",
            daemon=True,
        ).start()

    def set_subtitles(self, path, visible=True):
        try:
            self.player.setSubtitles(path)
            self.player.showSubtitles(bool(visible))
            self._subtitle_path = path
            self._subtitle_visible = bool(visible)
            log("Kodi subtitles set: %s visible=%s" % (path, visible), "info")
        except Exception as exc:
            log("Kodi setSubtitles failed: %s" % exc, "warning")

    def show_subtitles(self, visible):
        try:
            self.player.showSubtitles(bool(visible))
            self._subtitle_visible = bool(visible)
        except Exception as exc:
            log("Kodi showSubtitles failed: %s" % exc, "warning")

    def pause(self):
        try:
            if self.is_active() and not self.is_paused():
                # PlayerControl is asynchronous; a stuck decoder must not block
                # the NVA command thread.
                xbmc.executebuiltin("PlayerControl(Play)")
        except Exception as exc:
            log("Kodi pause failed: %s" % exc, "warning")

    def resume(self):
        try:
            if self.is_active() and self.is_paused():
                xbmc.executebuiltin("PlayerControl(Play)")
        except Exception as exc:
            log("Kodi resume failed: %s" % exc, "warning")

    def stop(self):
        # PlayerControl(Stop) runs on Kodi's UI thread.  If the Android
        # MediaCodec surface is wedged, that call can block forever; do it on
        # a worker so the NVA connection can still answer the phone.
        threading.Thread(
            target=self._stop_worker,
            name="BiliCast-Stop",
            daemon=True,
        ).start()

    def _stop_worker(self):
        try:
            if self.is_active():
                xbmc.executebuiltin("PlayerControl(Stop)")
        except Exception as exc:
            log("Kodi stop failed: %s" % exc, "warning")

    def seek(self, seconds):
        threading.Thread(
            target=self._seek_worker,
            args=(seconds,),
            name="BiliCast-SeekWorker",
            daemon=True,
        ).start()

    def _seek_worker(self, seconds):
        try:
            self.player.seekTime(float(seconds))
        except Exception as exc:
            log("Kodi seek failed: %s" % exc, "warning")

    def set_speed(self, speed):
        try:
            player_id = self._active_player_id()
            if player_id < 0:
                return False
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "Player.SetSpeed",
                "params": {"playerid": player_id, "speed": float(speed)},
            }
            result = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
            return "result" in result
        except Exception as exc:
            log("Kodi setSpeed failed: %s" % exc, "warning")
            return False

    # ------------------------------------------------------------------ state
    def is_active(self):
        try:
            if self.player.isPlaying():
                return True
            # Kodi's isPlaying() can be false while paused; the condition
            # still tells us the player owns the screen.
            return bool(xbmc.getCondVisibility("Player.Paused"))
        except Exception:
            return False

    def is_paused(self):
        try:
            return bool(xbmc.getCondVisibility("Player.Paused"))
        except Exception:
            return False

    def is_playing(self):
        return self.is_active() and not self.is_paused()

    def get_time(self):
        try:
            return float(self.player.getTime())
        except Exception:
            return 0.0

    def get_total_time(self):
        try:
            return float(self.player.getTotalTime())
        except Exception:
            return 0.0

    def get_volume(self):
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "Application.GetVolume",
            }
            result = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
            return int(result.get("result", {}).get("volume", 50))
        except Exception:
            return 50

    def set_volume(self, volume):
        try:
            volume = max(0, min(100, int(volume)))
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "Application.SetVolume",
                "params": {"volume": volume},
            }
            xbmc.executeJSONRPC(json.dumps(payload))
        except Exception as exc:
            log("Kodi setVolume failed: %s" % exc, "warning")

    def notify(self, message):
        try:
            xbmcgui.Dialog().notification("Bili Cast", str(message), time=3000)
        except Exception:
            pass

    def _active_player_id(self):
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "Player.GetActivePlayers",
            }
            result = json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
            for item in result.get("result", []):
                if item.get("type") == "video":
                    return int(item.get("playerid", -1))
        except Exception:
            pass
        return -1
