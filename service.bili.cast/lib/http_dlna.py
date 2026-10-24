"""HTTP side of the receiver: UPnP description, SCPD and SOAP stubs."""

import os
import re
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from .device import NVA_SCPD, minimal_scpd
from .log import log
from .net import http_date
from .storage import addon_data_dir


def read_head(sock, max_bytes=65536):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > max_bytes:
            break
    head, _, rest = data.partition(b"\r\n\r\n")
    return head, rest


def parse_head(head):
    text = head.decode("iso-8859-1", "replace")
    lines = text.split("\r\n")
    if not lines or not lines[0]:
        return None, None, None, {}
    parts = lines[0].split()
    if len(parts) < 2:
        return None, None, None, {}
    method = parts[0]
    path = parts[1]
    protocol = parts[2] if len(parts) > 2 else "HTTP/1.0"
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return method, path, protocol, headers


def read_body(sock, headers, rest):
    try:
        length = int(headers.get("content-length", "0") or "0")
    except ValueError:
        length = 0
    body = rest
    while len(body) < length:
        chunk = sock.recv(min(4096, length - len(body)))
        if not chunk:
            break
        body += chunk
    return body[:length]


def send_http_response(sock, status, headers=None, body=b"", protocol="HTTP/1.1",
                       head_only=False):
    if isinstance(body, str):
        body = body.encode("utf-8")
    headers = list((headers or {}).items())
    keys = {key.lower() for key, _ in headers}
    if "content-length" not in keys:
        headers.append(("Content-Length", str(len(body))))
    if "connection" not in keys:
        headers.append(("Connection", "close"))
    if "server" not in keys:
        headers.append(("Server", "Kodi-BiliCast/0.1"))
    if "date" not in keys:
        headers.append(("Date", http_date()))

    lines = [protocol + " " + status]
    lines.extend("%s: %s" % (key, value) for key, value in headers)
    raw = ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1")
    try:
        sock.sendall(raw)
        if not head_only:
            sock.sendall(body)
    except OSError as exc:
        log("HTTP send failed: %s" % exc, "debug")


def _format_time(seconds):
    try:
        seconds = int(max(0, seconds))
    except (TypeError, ValueError):
        seconds = 0
    return "%02d:%02d:%02d" % (
        seconds // 3600,
        (seconds % 3600) // 60,
        seconds % 60,
    )


def _parse_time(value):
    if not value:
        return 0
    match = re.match(r"^(\d+):(\d+):(\d+)", value)
    if not match:
        try:
            return int(float(value))
        except ValueError:
            return 0
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _service_from_path(path):
    parts = [part for part in (path or "").strip("/").split("/") if part]
    if len(parts) >= 2 and parts[0] == "bilibili":
        return parts[1]
    if parts:
        return parts[0]
    return "NirvanaControl"


def soap_response(app, path, body):
    service = _service_from_path(path)
    default_ns = (
        "urn:app-bilibili-com:service:NirvanaControl:3"
        if service == "NirvanaControl"
        else "urn:schemas-upnp-org:service:%s:1" % service
    )
    action = "Unknown"
    service_ns = default_ns
    args = {}

    try:
        root = ET.fromstring(body)
        body_el = root.find("{http://schemas.xmlsoap.org/soap/envelope/}Body")
        if body_el is None:
            for child in root.iter():
                if _local_name(child.tag) == "Body":
                    body_el = child
                    break
        if body_el is not None and len(body_el):
            action_el = list(body_el)[0]
            action = _local_name(action_el.tag)
            if action_el.tag.startswith("{"):
                service_ns = action_el.tag[1:].split("}", 1)[0]
            for child in action_el:
                args[_local_name(child.tag)] = child.text or ""
    except Exception as exc:
        log("SOAP parse failed: %s" % exc, "warning")

    fields = []

    if action == "GetAppInfo":
        fields = [
            ("PackageName", "com.xiaodianshi.tv.yst"),
            ("AppKey", "0000000000000000"),
            ("Signature", "0000000000000000"),
            ("CurrentSignedIn", "1"),
        ]
    elif action == "GetVolume":
        fields = [("CurrentVolume", str(app.volume))]
    elif action == "SetVolume":
        try:
            app.volume = max(0, min(100, int(args.get("DesiredVolume", app.volume))))
        except ValueError:
            pass
    elif action == "GetMute":
        fields = [("CurrentMute", "0")]
    elif action == "SetMute":
        pass
    elif action == "GetTransportInfo":
        fields = [
            ("CurrentTransportState", app.transport_state),
            ("CurrentTransportStatus", "OK"),
            ("CurrentSpeed", "1"),
        ]
    elif action == "GetPositionInfo":
        position = _format_time(app.position_seconds)
        duration = _format_time(app.duration_seconds)
        fields = [
            ("Track", "1" if app.current_uri else "0"),
            ("TrackDuration", duration),
            ("TrackMetaData", ""),
            ("TrackURI", app.current_uri),
            ("RelTime", position),
            ("AbsTime", position),
            ("RelCount", "0"),
            ("AbsCount", "0"),
        ]
    elif action == "GetMediaInfo":
        fields = [
            ("NrTracks", "1" if app.current_uri else "0"),
            ("MediaDuration", _format_time(app.duration_seconds)),
            ("CurrentURI", app.current_uri),
            ("CurrentURIMetaData", ""),
            ("NextURI", ""),
            ("NextURIMetaData", ""),
            ("PlayMedium", "NETWORK" if app.current_uri else "NONE"),
            ("RecordMedium", "NOT_IMPLEMENTED"),
            ("WriteStatus", "NOT_IMPLEMENTED"),
        ]
    elif action == "GetDeviceCapabilities":
        fields = [
            ("PlayMedia", "NETWORK"),
            ("RecMedia", "NOT_IMPLEMENTED"),
            ("RecQualityModes", "NOT_IMPLEMENTED"),
        ]
    elif action == "GetTransportSettings":
        fields = [
            ("PlayMode", "NORMAL"),
            ("RecQualityMode", "NOT_IMPLEMENTED"),
        ]
    elif action == "GetProtocolInfo":
        fields = [
            ("Source", ""),
            ("Sink", "http-get:*:video/mp4:*,http-get:*:video/x-matroska:*,"
                     "http-get:*:video/mpeg:*"),
        ]
    elif action == "GetCurrentConnectionIDs":
        fields = [("ConnectionIDs", "0")]
    elif action == "GetCurrentConnectionInfo":
        fields = [
            ("RcsID", "0"),
            ("AVTransportID", "0"),
            ("ProtocolInfo", ""),
            ("PeerConnectionManager", ""),
            ("PeerConnectionID", "-1"),
            ("Direction", "Output"),
            ("Status", "OK"),
        ]
    elif action == "GetVolumeDBRange":
        fields = [("MinValue", "-60"), ("MaxValue", "0")]
    elif action == "GetVolumeDB":
        fields = [("CurrentVolume", "0")]
    elif action == "ListPresets":
        fields = [("CurrentPresetNameList", "FactoryDefaults")]
    elif action == "SelectPreset":
        pass
    elif action == "SetAVTransportURI":
        app.current_uri = args.get("CurrentURI", "")
        app.transport_state = "STOPPED"
        log("DLNA SetAVTransportURI: %s" % app.current_uri, "info")
    elif action == "SetNextAVTransportURI":
        pass
    elif action == "Play":
        app.transport_state = "PLAYING"
        log("DLNA Play", "info")
    elif action == "Pause":
        app.transport_state = "PAUSED_PLAYBACK"
        log("DLNA Pause", "info")
    elif action == "Stop":
        app.transport_state = "STOPPED"
        log("DLNA Stop", "info")
    elif action == "Seek":
        app.position_seconds = _parse_time(args.get("Target", ""))
        log("DLNA Seek: %s" % app.position_seconds, "info")
    elif action == "GetPlayInfo":
        fields = [("Content", "")]
    elif action == "GetAccountInfo":
        fields = [("VipInfo", "0")]
    elif action == "PrepareForMirrorProjection":
        fields = [
            ("ScreenWidth", "1920"),
            ("ScreenHeight", "1080"),
            ("PushUrl", ""),
        ]
    elif action == "LoginWithCode":
        pass
    elif action == "SetDanmakuSwitch":
        pass
    elif action == "AppendDanmaku":
        pass
    elif action == "SwitchQuality":
        pass

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">',
        "<s:Body>",
        '<u:%sResponse xmlns:u="%s">' % (escape(action), escape(service_ns)),
    ]
    for name, value in fields:
        lines.append("<%s>%s</%s>" % (name, escape(str(value)), name))
    lines.extend([
        "</u:%sResponse>" % escape(action),
        "</s:Body>",
        "</s:Envelope>",
    ])
    return "\n".join(lines)


def handle_http(app, sock, method, path, headers, body):
    method = (method or "").upper()
    path_only = urllib.parse.urlsplit(path or "/").path

    if method in ("SUBSCRIBE", "UNSUBSCRIBE"):
        sid = headers.get("sid") or "uuid:" + str(uuid.uuid4())
        send_http_response(
            sock,
            "200 OK",
            {
                "SID": sid,
                "TIMEOUT": "Second-1800",
                "Content-Length": "0",
            },
        )
        return

    if method == "NOTIFY":
        send_http_response(sock, "200 OK", {"Content-Length": "0"})
        return

    if method in ("GET", "HEAD"):
        if path_only in ("/description.xml", "/bilibili/description.xml"):
            response = app.device.description_xml()
            content_type = 'text/xml; charset="utf-8"'
        elif path_only.startswith("/dash/") and path_only.endswith(".mpd"):
            name = os.path.basename(path_only)
            if not re.match(r"^[A-Za-z0-9_.-]+\.mpd$", name):
                send_http_response(sock, "400 Bad Request", {"Content-Length": "0"})
                return
            mpd_path = os.path.join(addon_data_dir(), name)
            try:
                with open(mpd_path, "r", encoding="utf-8") as handle:
                    response = handle.read()
            except OSError:
                send_http_response(sock, "404 Not Found", {"Content-Length": "0"})
                return
            content_type = 'application/dash+xml'
        elif path_only == "/dlna/NirvanaControl.xml":
            response = NVA_SCPD
            content_type = 'text/xml; charset="utf-8"'
        elif path_only.startswith("/bilibili/") and path_only.endswith("/scpd.xml"):
            service = _service_from_path(path_only)
            response = NVA_SCPD if service == "NirvanaControl" else minimal_scpd(service)
            content_type = 'text/xml; charset="utf-8"'
        elif path_only.startswith("/dlna/") and path_only.endswith(".xml"):
            service = path_only[len("/dlna/"):-len(".xml")]
            response = minimal_scpd(service)
            content_type = 'text/xml; charset="utf-8"'
        elif path_only == "/":
            response = "Kodi Bili Cast receiver\n"
            content_type = "text/plain; charset=utf-8"
        else:
            send_http_response(sock, "404 Not Found", {"Content-Length": "0"})
            return

        send_http_response(
            sock,
            "200 OK",
            {"Content-Type": content_type},
            response,
            head_only=(method == "HEAD"),
        )
        return

    if method == "POST":
        if path_only.endswith("/action") or path_only.endswith("/control.xml"):
            response = soap_response(app, path_only, body)
            send_http_response(
                sock,
                "200 OK",
                {
                    "Content-Type": 'text/xml; charset="utf-8"',
                    "EXT": "",
                },
                response,
            )
            return
        send_http_response(sock, "404 Not Found", {"Content-Length": "0"})
        return

    send_http_response(sock, "405 Method Not Allowed", {"Content-Length": "0"})
