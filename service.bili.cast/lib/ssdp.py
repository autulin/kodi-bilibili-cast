"""Minimal SSDP responder for DLNA MediaRenderer + Bilibili NirvanaControl."""

import random
import socket
import threading
import time

from .log import log
from .net import choose_local_ip, get_local_ips, http_date

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SERVER = "Linux/3.0.0 UPnP/1.0 Platinum/1.0.5.13"


class SSDPServer(threading.Thread):
    def __init__(self, device, http_port, logger=log):
        super().__init__(name="BiliCast-SSDP", daemon=True)
        self.device = device
        self.http_port = http_port
        self.logger = logger
        self.running = False
        self.sock = None
        self.local_ips = get_local_ips()
        self._last_notify = 0.0
        self._entries = self._build_entries()

    def _build_entries(self):
        uuid = self.device.uuid
        base = "uuid:" + uuid
        entries = [
            ("upnp:rootdevice", base + "::upnp:rootdevice"),
            (base, base),
            ("urn:schemas-upnp-org:device:MediaRenderer:1",
             base + "::urn:schemas-upnp-org:device:MediaRenderer:1"),
            ("urn:schemas-upnp-org:service:AVTransport:1",
             base + "::urn:schemas-upnp-org:service:AVTransport:1"),
            ("urn:schemas-upnp-org:service:RenderingControl:1",
             base + "::urn:schemas-upnp-org:service:RenderingControl:1"),
            ("urn:schemas-upnp-org:service:ConnectionManager:1",
             base + "::urn:schemas-upnp-org:service:ConnectionManager:1"),
            ("urn:app-bilibili-com:service:NirvanaControl:3",
             base + "::urn:app-bilibili-com:service:NirvanaControl:3"),
        ]
        return entries

    def start(self):
        if self.running:
            return
        self.running = True
        super().start()

    def stop(self):
        self.running = False
        if self.is_alive():
            self.join(timeout=2.0)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass

            join_ips = self.local_ips or ["0.0.0.0"]
            for ip in join_ips:
                mreq = socket.inet_aton(SSDP_ADDR) + socket.inet_aton(ip)
                try:
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                    self.logger("SSDP joined %s on %s" % (SSDP_ADDR, ip), "debug")
                except OSError as exc:
                    self.logger("SSDP join failed on %s: %s" % (ip, exc), "warning")

            sock.bind(("", SSDP_PORT))
            sock.settimeout(1.0)
            self.sock = sock
            self.logger("SSDP listening on udp/%d" % SSDP_PORT, "info")
        except OSError as exc:
            self.logger("SSDP cannot bind udp/%d: %s" % (SSDP_PORT, exc), "error")
            try:
                sock.close()
            except OSError:
                pass
            self.running = False
            return

        try:
            self._send_notify("ssdp:alive")
            self._last_notify = time.time()
            while self.running:
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    if time.time() - self._last_notify >= 30:
                        self._send_notify("ssdp:alive")
                        self._last_notify = time.time()
                    continue
                except OSError:
                    break
                self._handle_datagram(data, addr)
        finally:
            try:
                self._send_notify("ssdp:byebye")
            except Exception:
                pass
            try:
                sock.close()
            except OSError:
                pass
            self.sock = None
            self.logger("SSDP stopped", "info")

    def _send_notify(self, nts):
        ips = self.local_ips or [None]
        for ip in ips:
            send_sock = None
            try:
                send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                if ip:
                    send_sock.setsockopt(
                        socket.IPPROTO_IP,
                        socket.IP_MULTICAST_IF,
                        socket.inet_aton(ip),
                    )
                send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                location = "http://%s:%d/bilibili/description.xml" % (
                    ip or choose_local_ip("127.0.0.1", self.local_ips),
                    self.http_port,
                )
                for st, usn in self._entries:
                    lines = [
                        "NOTIFY * HTTP/1.1",
                        "HOST: %s:%d" % (SSDP_ADDR, SSDP_PORT),
                        "CACHE-CONTROL: max-age=1800",
                        "LOCATION: " + location,
                        "NT: " + st,
                        "NTS: " + nts,
                        "SERVER: " + SERVER,
                        "USN: " + usn,
                        "BOOTID.UPNP.ORG: 1",
                        "CONFIGID.UPNP.ORG: 1",
                        "",
                        "",
                    ]
                    send_sock.sendto(
                        "\r\n".join(lines).encode("utf-8"),
                        (SSDP_ADDR, SSDP_PORT),
                    )
            except OSError as exc:
                self.logger("SSDP notify failed: %s" % exc, "debug")
            finally:
                if send_sock is not None:
                    send_sock.close()

    def _handle_datagram(self, data, addr):
        try:
            text = data.decode("utf-8", "replace")
        except Exception:
            return
        lines = text.split("\r\n")
        if not lines:
            return
        parts = lines[0].split()
        if len(parts) < 2 or parts[0] != "M-SEARCH" or parts[1] != "*":
            return

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        st = headers.get("st", "")
        if not st:
            return
        try:
            mx = float(headers.get("mx", "1") or "1")
        except ValueError:
            mx = 1.0

        matches = []
        if st == "ssdp:all":
            matches = list(self._entries)
        else:
            for entry in self._entries:
                if entry[0] == st:
                    matches.append(entry)
            if not matches and st in (
                "urn:schemas-upnp-org:service:NirvanaControl:3",
                "urn:app-bilibili-com:service:NirvanaControl:1",
            ):
                matches.append(self._entries[-1])

        if not matches:
            return

        # Small jitter avoids a burst when several devices answer at once.
        delay = random.uniform(0, max(0.0, min(mx, 1.0)))
        if delay > 0.02:
            threading.Thread(
                target=self._delayed_search_response,
                args=(addr, matches, st),
                daemon=True,
            ).start()
        else:
            self._send_search_response(addr, matches, st)

    def _delayed_search_response(self, addr, matches, requested_st):
        time.sleep(random.uniform(0.02, 0.3))
        self._send_search_response(addr, matches, requested_st)

    def _send_search_response(self, addr, matches, requested_st):
        if not self.sock:
            return
        ip = choose_local_ip(addr[0], self.local_ips)
        location = "http://%s:%d/bilibili/description.xml" % (ip, self.http_port)
        for st, usn in matches:
            response_st = st
            if requested_st != "ssdp:all":
                response_st = requested_st
            lines = [
                "HTTP/1.1 200 OK",
                "CACHE-CONTROL: max-age=1800",
                "DATE: " + http_date(),
                "EXT:",
                "LOCATION: " + location,
                "SERVER: " + SERVER,
                "ST: " + response_st,
                "USN: " + usn,
                "BOOTID.UPNP.ORG: 1",
                "CONFIGID.UPNP.ORG: 1",
                "",
                "",
            ]
            try:
                self.sock.sendto(
                    "\r\n".join(lines).encode("utf-8"),
                    addr,
                )
            except OSError as exc:
                self.logger("SSDP search response failed: %s" % exc, "debug")
                break
