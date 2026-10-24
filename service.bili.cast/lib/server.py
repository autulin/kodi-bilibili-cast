"""TCP server that speaks both HTTP/UPnP and NVA on the same port."""

import json
import os
import socketserver
import threading
import time
import urllib.parse

from .bili_api import BiliApiError, get_tv_playurl, get_video_title
from .danmaku import download_and_convert
from .dash import write_mpd
from .http_dlna import (
    handle_http,
    parse_head,
    read_body,
    read_head,
)
from .log import log
from .net import get_primary_ip, http_date, make_session_id
from .nva import NVAConnection
from .ssdp import SSDPServer

SUPPORT_SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2]


def send_nva_handshake(sock, device, session):
    lines = [
        "NVA/1.0 200 OK",
        "NvaVersion: 1",
        "Session: " + session,
        "Connection: Keep-Alive",
        "UUID: " + device.uuid,
        "Date: " + http_date(),
        "Content-Length: 0",
        "Server: Linux/3.0.0, UPnP/1.0, Platinum/1.0.5.13",
        "",
        "",
    ]
    sock.sendall("\r\n".join(lines).encode("utf-8"))


class BiliCastRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10.0)
        try:
            head, rest = read_head(self.request)
            if not head:
                return
            method, path, protocol, headers = parse_head(head)
            if not method or not path:
                return

            if (
                method.upper() in ("SETUP", "RESTORE", "STARTRESTORE")
                and (protocol or "").upper().startswith("NVA/")
            ):
                self._handle_nva(method, path, headers, rest)
                return

            body = read_body(self.request, headers, rest)
            handle_http(self.server.app, self.request, method, path, headers, body)
        except Exception as exc:
            log("request handler error: %s" % exc, "warning")

    def _handle_nva(self, method, path, headers, rest=b""):
        app = self.server.app
        session = headers.get("session") or make_session_id()
        client_uuid = headers.get("uuid", "")
        log(
            "NVA %s path=%s session=%s client=%s"
            % (method, path, session[-8:], client_uuid[-8:]),
            "info",
        )
        send_nva_handshake(self.request, app.device, session)
        conn = NVAConnection(
            self.request,
            app,
            session=session,
            client_uuid=client_uuid,
            remote=self.client_address,
        )
        app.on_connection_opened(conn)
        try:
            if method.upper() == "RESTORE":
                app.on_restore(conn)
            conn.start_ping()
            if rest:
                conn.parse_request(rest)
            conn.run()
        finally:
            conn.close()
            app.on_connection_closed(conn)


class BiliCastTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, addr, app):
        self.app = app
        super().__init__(addr, BiliCastRequestHandler)


class BiliCastServer:
    def __init__(self, device, port=9958, enable_ssdp=True, logger=log,
                 player=None, danmaku_settings=None):
        self.device = device
        self.preferred_port = int(port or 9958)
        self.enable_ssdp = enable_ssdp
        self.logger = logger
        self.player = player
        self.danmaku_settings = danmaku_settings or {}

        self.port = None
        self.port_conflict = False
        self.tcp = None
        self.tcp_thread = None
        self.ssdp = None

        self.lock = threading.Lock()
        self.connections = set()

        self.volume = 50
        self.transport_state = "STOPPED"
        self.current_uri = ""
        self.position_seconds = 0
        self.duration_seconds = 0
        self.title = ""
        self.current_media = {}
        self.qn_info = self._placeholder_qn()
        self.danmaku_open = True
        self.subtitle_path = None

        self.play_generation = 0
        self.progress_stop = threading.Event()
        self.progress_thread = None
        self._last_state_sent = None
        self._play_started_at = 0.0

    def start(self):
        last_error = None
        for port in (self.preferred_port, 0):
            try:
                self.tcp = BiliCastTCPServer(("", port), self)
                self.port = self.tcp.server_address[1]
                break
            except OSError as exc:
                last_error = exc
                self.logger("TCP bind %s failed: %s" % (port, exc), "warning")

        if self.tcp is None:
            raise RuntimeError("cannot bind TCP server: %s" % last_error)

        self.port_conflict = self.port != self.preferred_port
        if self.port_conflict:
            self.logger(
                "preferred port %s busy, using %s; NVA clients require %s"
                % (self.preferred_port, self.port, self.preferred_port),
                "error",
            )
            self._notify(
                "端口 %s 被占用，请关闭云视听小电视后重启 Kodi"
                % self.preferred_port
            )
        self.logger("HTTP/NVA listening on tcp/%s" % self.port, "info")

        self.tcp_thread = threading.Thread(
            target=self.tcp.serve_forever,
            name="BiliCast-TCP",
            daemon=True,
        )
        self.tcp_thread.start()

        if self.enable_ssdp:
            self.ssdp = SSDPServer(self.device, self.port, self.logger)
            self.ssdp.start()
        else:
            self.logger("SSDP disabled by setting", "info")

    def stop(self):
        self._stop_progress()
        if self.player is not None:
            try:
                self.player.stop()
            except Exception:
                pass
        if self.ssdp is not None:
            self.ssdp.stop()
            self.ssdp = None

        with self.lock:
            connections = list(self.connections)
            self.connections.clear()
        for conn in connections:
            conn.close()

        if self.tcp is not None:
            try:
                self.tcp.shutdown()
            except Exception:
                pass
            try:
                self.tcp.server_close()
            except Exception:
                pass
            self.tcp = None
        if self.tcp_thread is not None:
            self.tcp_thread.join(timeout=2.0)
            self.tcp_thread = None
        self.logger("BiliCast server stopped", "info")

    # ------------------------------------------------------------- connections
    def on_connection_opened(self, conn):
        with self.lock:
            self.connections.add(conn)
        self.logger(
            "NVA client connected: %s (%s)"
            % (conn.remote, conn.session[-8:]),
            "info",
        )

    def on_connection_closed(self, conn):
        with self.lock:
            self.connections.discard(conn)
        self.logger(
            "NVA client disconnected: %s (%s)"
            % (conn.remote, conn.session[-8:]),
            "info",
        )

    def on_response(self, conn, counter, params):
        self.logger("NVA response %s: %s" % (counter, params), "debug")

    def on_restore(self, conn):
        self.logger("NVA restore session %s" % conn.session[-8:], "info")
        code = self._play_state_code()
        self._last_state_sent = code
        conn.send_cmd("OnPlayState", {"playState": code})
        conn.send_cmd("OnDanmakuSwitch", {"open": self.danmaku_open})
        conn.send_cmd("OnQnSwitch", self.qn_info)
        conn.send_cmd(
            "SpeedChanged",
            {"currSpeed": 1, "supportSpeedList": SUPPORT_SPEEDS},
        )
        if self.duration_seconds > 0:
            conn.send_cmd(
                "OnProgress",
                {
                    "duration": int(self.duration_seconds),
                    "position": int(self.position_seconds),
                },
            )

    def broadcast(self, cmd, params=None):
        with self.lock:
            connections = list(self.connections)
        for conn in connections:
            if not conn.terminated:
                try:
                    conn.send_cmd(cmd, params)
                except Exception as exc:
                    self.logger("NVA broadcast failed: %s" % exc, "debug")

    def _broadcast_state(self, code):
        if self._last_state_sent == code:
            return
        self._last_state_sent = code
        self.broadcast("OnPlayState", {"playState": code})

    # ---------------------------------------------------------------- commands
    def on_command(self, conn, method, counter, params):
        safe_params = self._redact(params or {})
        self.logger("NVA command %s #%s %s" % (method, counter, safe_params), "info")
        try:
            self._dispatch(conn, method, counter, params or {})
        except Exception as exc:
            self.logger("NVA command error %s: %s" % (method, exc), "warning")
            try:
                conn.send_res(counter)
            except Exception:
                pass

    def _dispatch(self, conn, method, counter, params):
        if method == "GetVolume":
            if self.player is not None:
                try:
                    self.volume = self.player.get_volume()
                except Exception:
                    pass
            conn.send_res(counter, {"volume": self.volume})
            return

        if method == "SetVolume":
            try:
                self.volume = max(0, min(100, int(params.get("volume", self.volume))))
            except (TypeError, ValueError):
                pass
            if self.player is not None:
                self.player.set_volume(self.volume)
            conn.send_res(counter)
            return

        if method == "Pause":
            if self.player is not None:
                self.player.pause()
            conn.send_res(counter)
            self.transport_state = "PAUSED_PLAYBACK"
            self._broadcast_state(5)
            return

        if method == "Resume":
            if self.player is not None:
                self.player.resume()
            conn.send_res(counter)
            self.transport_state = "PLAYING"
            self._broadcast_state(4)
            return

        if method == "Stop":
            self.play_generation += 1
            self._stop_progress()
            # Acknowledge first: the phone shows "stopped" immediately even if
            # Kodi's player teardown is slow.
            conn.send_res(counter)
            self.transport_state = "STOPPED"
            self.position_seconds = 0
            self._broadcast_state(7)
            if self.player is not None:
                self.player.stop()
            return

        if method == "Seek":
            seek_value = params.get(
                "seekTs", params.get("position", params.get("seek", 0))
            )
            try:
                self.position_seconds = int(float(seek_value))
            except (TypeError, ValueError):
                self.position_seconds = 0
            if self.player is not None:
                self.player.seek(self.position_seconds)
            conn.send_res(counter)
            self.broadcast(
                "OnProgress",
                {
                    "duration": int(self.duration_seconds),
                    "position": int(self.position_seconds),
                },
            )
            return

        if method == "SwitchDanmaku":
            open_value = params.get(
                "open", params.get("danmakuSwitch", params.get("switch", True))
            )
            if isinstance(open_value, str):
                open_value = open_value.lower() != "false"
            self.danmaku_open = bool(open_value)
            if self.player is not None:
                self.player.show_subtitles(self.danmaku_open)
            conn.send_res(counter)
            self.broadcast("OnDanmakuSwitch", {"open": self.danmaku_open})
            return

        if method == "SwitchSpeed":
            speed = _as_float(
                params.get("speed", params.get("userDesireSpeed", 1)), 1.0
            )
            if self.player is not None:
                self.player.set_speed(speed)
            conn.send_res(counter)
            self.broadcast(
                "SpeedChanged",
                {"currSpeed": speed, "supportSpeedList": SUPPORT_SPEEDS},
            )
            return

        if method == "SwitchQn":
            qn = _as_int(params.get("qn", params.get("userDesireQn", 0)))
            conn.send_res(counter)
            if self.current_media and self.player is not None:
                current_desire = _as_int(
                    self.current_media.get("desire_qn", 0)
                )
                # The phone sends SwitchQn(80) immediately after Play even when
                # Play already requested 80. Re-fetching here would restart the
                # video a few seconds in, so treat that automatic command as a
                # no-op. A later user-initiated switch still re-fetches.
                if (
                    qn == current_desire
                    and self.transport_state
                    in ("LOADING", "PLAYING", "PAUSED_PLAYBACK")
                    and time.time() - self._play_started_at < 8.0
                ):
                    if self.qn_info.get("curQn"):
                        self.broadcast("OnQnSwitch", self.qn_info)
                    return
                media = dict(self.current_media)
                media["desire_qn"] = qn
                media["seek_ts"] = int(self._current_position())
                self._handle_play(media)
            else:
                self.broadcast("OnQnSwitch", self._placeholder_qn(qn))
            return

        if method == "SendDanmaku":
            conn.send_res(counter)
            content = params.get("content", "")
            self.logger(
                "SendDanmaku content=%r type=%r color=%r"
                % (content, params.get("type"), params.get("color")),
                "info",
            )
            if self.player is not None and content:
                self.player.notify("弹幕: %s" % content)
            return

        if method == "Play":
            conn.send_res(counter)
            self._handle_play(params)
            return

        if method == "PlayUrl":
            conn.send_res(counter)
            self._handle_play_url(params)
            return

        # GetTVInfo and future commands: acknowledge so the client can proceed.
        conn.send_res(counter)

    # ----------------------------------------------------------------- playback
    def _handle_play(self, params):
        media = self._parse_media(params)
        self.play_generation += 1
        generation = self.play_generation
        self._stop_progress()
        self._play_started_at = time.time()

        self.current_media = media
        self.transport_state = "LOADING"
        self.duration_seconds = 0
        self.position_seconds = media["seek_ts"]
        self.title = media["title"]
        self.subtitle_path = None
        self.qn_info = self._placeholder_qn(media["desire_qn"])
        # danmakuSwitchSave=false means "don't restore a saved switch state";
        # it does not mean the phone wants danmaku hidden. Start with danmaku
        # visible and let SwitchDanmaku toggle it later.
        self.danmaku_open = True

        self.logger(
            "Play aid=%s cid=%s epid=%s season=%s oid=%s content_type=%s "
            "access_key=%s qn=%s seek=%s speed=%s danmaku=%s"
            % (
                media["aid"],
                media["cid"],
                media["epid"],
                media["season_id"],
                media["oid"],
                media["content_type"],
                "yes" if media["access_key"] else "no",
                media["desire_qn"],
                media["seek_ts"],
                media["speed"],
                self.danmaku_open,
            ),
            "info",
        )

        self._broadcast_state(3)

        if self.player is None:
            # Dev mode: no Kodi player, but keep the protocol complete.
            self._announce_playback(
                media, self.qn_info, media["title"], media["speed"]
            )
            self.transport_state = "PLAYING"
            self._broadcast_state(4)
            return

        threading.Thread(
            target=self._start_playback,
            args=(generation, media),
            name="BiliCast-Play",
            daemon=True,
        ).start()

    def _announce_playback(self, media, qn_info, title, speed):
        play_item = {
            "aid": media["aid"],
            "cid": media["cid"],
            "contentType": media["content_type"],
            "epId": media["epid"],
            "seasonId": media["season_id"],
        }
        self.broadcast("OnDanmakuSwitch", {"open": self.danmaku_open})
        self.broadcast(
            "OnEpisodeSwitch",
            {
                "playItem": play_item,
                "qnDesc": qn_info,
                "title": title,
            },
        )
        self.broadcast("OnQnSwitch", qn_info)
        self.broadcast(
            "SpeedChanged",
            {"currSpeed": speed, "supportSpeedList": SUPPORT_SPEEDS},
        )

    def _start_playback(self, generation, media):
        try:
            result = get_tv_playurl(
                aid=media["aid"],
                cid=media["cid"],
                oid=media["oid"],
                epid=media["epid"],
                season_id=media["season_id"],
                access_key=media["access_key"],
                qn=media["desire_qn"],
                playurl_type=media["playurl_type"],
            )
        except BiliApiError as exc:
            self.logger("Bilibili API error: %s (code=%s)" % (exc, exc.code), "error")
            if generation == self.play_generation:
                self.transport_state = "STOPPED"
                self._broadcast_state(7)
                self._notify("B站取流失败: %s" % exc)
            return
        except Exception as exc:
            self.logger("playurl request failed: %s" % exc, "error")
            if generation == self.play_generation:
                self.transport_state = "STOPPED"
                self._broadcast_state(7)
                self._notify("B站取流失败，请检查网络")
            return

        if generation != self.play_generation:
            return

        self.duration_seconds = result["duration"]
        self.qn_info = result["qn_desc"]
        self.qn_info["userDesireQn"] = media["desire_qn"]
        self.logger(
            "playurl qn=%s accept=%s format=%s login=%s vip=%s"
            % (
                result["quality"],
                result["accept_quality"],
                result["format"],
                result.get("is_login"),
                result.get("is_vip"),
            ),
            "info",
        )

        play_url = result["url"]
        is_dash = bool(result.get("dash"))
        if is_dash:
            mpd_path, video = write_mpd(
                media["cid"],
                result["dash"],
                result["duration"],
                max_qn=media["desire_qn"] or 80,
            )
            if mpd_path:
                # inputstream.adaptive cannot open a local file path; serve the
                # MPD from our own HTTP port so it can fetch it like a manifest.
                play_url = "http://%s:%s/dash/%s" % (
                    get_primary_ip(),
                    self.port,
                    os.path.basename(mpd_path),
                )
                self.current_uri = play_url
                self.logger(
                    "DASH selected: %sx%s qn=%s manifest=%s"
                    % (
                        video.get("width"),
                        video.get("height"),
                        video.get("id"),
                        play_url,
                    ),
                    "info",
                )
            else:
                self.logger(
                    "DASH manifest unavailable, falling back to durl", "warning"
                )
        if play_url:
            self.current_uri = play_url

        title = get_video_title(media["aid"]) or media["title"] or (
            "Bilibili %s" % media["aid"]
        )
        self.title = title
        self.logger(
            "quality actual=%s desire=%s order=%s"
            % (
                self.qn_info.get("curQn"),
                media["desire_qn"],
                [item.get("quality") for item in self.qn_info.get("supportQnList", [])],
            ),
            "info",
        )
        # Send the episode and quality events only after the real playurl
        # response.  The phone otherwise latches onto the initial curQn=0
        # placeholder and keeps showing 360P even after the actual qn arrives.
        self._announce_playback(
            media, self.qn_info, title, media["speed"]
        )

        self.player.play(
            self.current_uri,
            title,
            seek_seconds=media["seek_ts"],
            subtitles=self.subtitle_path,
            danmaku_open=self.danmaku_open,
            dash=is_dash and self.current_uri.endswith(".mpd"),
        )
        threading.Thread(
            target=self._prepare_danmaku,
            args=(generation, media["cid"]),
            name="BiliCast-Danmaku",
            daemon=True,
        ).start()
        threading.Thread(
            target=self._wait_for_playback,
            args=(generation,),
            name="BiliCast-WaitPlay",
            daemon=True,
        ).start()

    def _wait_for_playback(self, generation):
        deadline = time.time() + 30.0
        while time.time() < deadline:
            if generation != self.play_generation:
                return
            try:
                if self.player.is_active():
                    self.transport_state = "PLAYING"
                    self._start_progress(generation)
                    return
            except Exception:
                pass
            time.sleep(0.5)
        if generation == self.play_generation:
            self.logger("Kodi playback did not start within 30s", "error")
            self.transport_state = "STOPPED"
            self._broadcast_state(7)
            self._notify("Kodi 播放启动失败")

    def _start_progress(self, generation):
        self._stop_progress()
        self.progress_stop = threading.Event()
        self.progress_thread = threading.Thread(
            target=self._progress_loop,
            args=(generation, self.progress_stop),
            name="BiliCast-Progress",
            daemon=True,
        )
        self.progress_thread.start()

    def _stop_progress(self):
        if self.progress_stop is not None:
            self.progress_stop.set()
        self.progress_stop = threading.Event()

    def _progress_loop(self, generation, stop_event):
        idle_since = None
        while not stop_event.is_set():
            if generation != self.play_generation:
                return
            if self.player is None:
                return
            try:
                active = self.player.is_active()
                paused = self.player.is_paused()
            except Exception:
                active = False
                paused = False

            if not active:
                if idle_since is None:
                    idle_since = time.time()
                elif time.time() - idle_since > 5:
                    if self.transport_state in ("PLAYING", "PAUSED_PLAYBACK"):
                        self.transport_state = "STOPPED"
                        self._broadcast_state(7)
                    return
                stop_event.wait(1.0)
                continue

            idle_since = None
            state = "PAUSED_PLAYBACK" if paused else "PLAYING"
            self.transport_state = state
            self._broadcast_state(5 if paused else 4)

            try:
                self.position_seconds = self.player.get_time()
                total = self.player.get_total_time()
                if total > 0:
                    self.duration_seconds = total
            except Exception:
                pass
            self.broadcast(
                "OnProgress",
                {
                    "duration": int(self.duration_seconds),
                    "position": int(self.position_seconds),
                },
            )
            stop_event.wait(1.0)

    def _prepare_danmaku(self, generation, cid):
        if not cid:
            return
        settings = self.danmaku_settings
        try:
            path, count = download_and_convert(
                cid,
                area=float(settings.get("area", 0.25)),
                font_size=int(settings.get("font_size", 48)),
                opacity=float(settings.get("opacity", 0.85)),
                max_lines=int(settings.get("max_lines", 4)),
            )
        except Exception as exc:
            self.logger("danmaku download/convert failed: %s" % exc, "warning")
            return
        if generation != self.play_generation:
            return
        self.subtitle_path = path
        self.logger("danmaku ready: %s comments (%s)" % (count, path), "info")
        if self.player is not None:
            try:
                self.player.queue_subtitles(path, self.danmaku_open)
            except Exception as exc:
                self.logger("queue subtitles failed: %s" % exc, "warning")

    def _handle_play_url(self, params):
        url = params.get("url", "")
        title = params.get("title", "")
        self.logger("PlayUrl title=%r host=%r" % (title, _url_host(url)), "info")
        content = {}
        try:
            query = urllib.parse.urlsplit(url).query
            nva_ext = urllib.parse.parse_qs(query).get("nva_ext", [""])[0]
            if nva_ext:
                payload = json.loads(nva_ext)
                content = payload.get("content", {})
        except Exception as exc:
            self.logger("PlayUrl nva_ext parse failed: %s" % exc, "warning")
        content = dict(content)
        content.setdefault("title", title)
        if content.get("aid") and content.get("cid"):
            self._handle_play(content)
        else:
            self._notify("暂不支持此投屏类型")
            self.logger("PlayUrl without aid/cid is not supported yet", "warning")

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _parse_media(params):
        aid = str(params.get("aid", "") or "")
        cid = str(params.get("cid", "") or "")
        epid = _as_int(params.get("epId", params.get("epid", 0)))
        season_id = _as_int(params.get("seasonId", params.get("season_id", 0)))
        room_id = str(params.get("roomId", "0") or "0")
        content_type = params.get("contentType", params.get("content_type", 0))
        access_key = params.get("accessKey", params.get("access_key", "")) or ""
        desire_qn = _as_int(params.get("userDesireQn", params.get("desire_qn", 80)))
        seek_ts = _as_int(params.get("seekTs", 0))
        speed = _as_float(params.get("userDesireSpeed", 1), 1.0)
        danmaku_save = params.get("danmakuSwitchSave", True)
        if isinstance(danmaku_save, str):
            danmaku_save = danmaku_save.lower() != "false"
        playurl_type = 1
        oid = str(params.get("oid", aid) or aid)
        if epid:
            playurl_type = 2
            oid = str(epid)
        elif room_id not in ("0", "", "None"):
            playurl_type = 4
            oid = room_id
        return {
            "aid": aid,
            "cid": cid,
            "epid": epid,
            "season_id": season_id,
            "oid": oid,
            "room_id": room_id,
            "content_type": content_type,
            "access_key": access_key,
            "desire_qn": desire_qn or 80,
            "seek_ts": seek_ts,
            "speed": speed,
            "danmaku_switch_save": bool(danmaku_save),
            "title": params.get("title", "") or "",
            "playurl_type": playurl_type,
        }

    def _current_position(self):
        if self.player is not None:
            try:
                return self.player.get_time()
            except Exception:
                pass
        return self.position_seconds

    @staticmethod
    def _redact(params):
        sensitive = {
            "accessKey", "access_key", "accessCode", "access_code",
            "sessionId", "biz_session_id", "mobile_access_key",
        }
        result = {}
        for key, value in (params or {}).items():
            if key in sensitive and value:
                result[key] = "***"
            else:
                result[key] = value
        return result

    def _notify(self, message):
        self.logger(message, "warning")
        if self.player is not None:
            try:
                self.player.notify(message)
            except Exception:
                pass

    @staticmethod
    def _placeholder_qn(user_desire=0):
        return {
            "curQn": 0,
            "supportQnList": [
                {
                    "description": "",
                    "displayDesc": "",
                    "needLogin": False,
                    "needVip": False,
                    "quality": 0,
                    "superscript": "",
                }
            ],
            "userDesireQn": user_desire,
        }

    def _play_state_code(self):
        if self.transport_state == "LOADING":
            return 3
        if self.transport_state == "PLAYING":
            return 4
        if self.transport_state == "PAUSED_PLAYBACK":
            return 5
        if self.transport_state == "NO_MEDIA_PRESENT":
            return 6
        return 7


def _as_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _url_host(url):
    try:
        return urllib.parse.urlsplit(url).netloc
    except Exception:
        return ""
