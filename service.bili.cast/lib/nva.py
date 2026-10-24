"""Bilibili Nirvana (NVA) TCP framing.

The frame layout follows the MIT-licensed Macast nirvana plugin:
https://github.com/xfangfang/Macast-plugins/tree/main/nirvana
"""

import json
import socket
import struct
import threading
import time

from .log import log

COMMAND = b"Command"
SEND_CMD = b"\xe0"
RET_CMD = b"\xc0"
PING = b"\xe4"


class NVAConnection:
    def __init__(self, sock, server, session="", client_uuid="", remote=None):
        self.sock = sock
        self.server = server
        self.session = session
        self.client_uuid = client_uuid
        self.remote = remote
        self.sock_lock = threading.Lock()
        self.counter_lock = threading.Lock()
        self.counter = 0
        self.cache = b""
        self.terminated = False
        self.ping_stop = threading.Event()
        self.ping_thread = None
        self.opened_at = None

    def start_ping(self):
        if self.ping_thread is not None:
            return
        self.ping_thread = threading.Thread(
            target=self._ping_loop,
            name="BiliCast-NVA-Ping",
            daemon=True,
        )
        self.ping_thread.start()

    def _ping_loop(self):
        while not self.ping_stop.wait(1.0):
            self.send_ping()

    def close(self):
        if self.terminated:
            return
        self.terminated = True
        self.ping_stop.set()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def _next_counter(self):
        with self.counter_lock:
            self.counter += 1
            return self.counter

    def send(self, data):
        with self.sock_lock:
            try:
                self.sock.sendall(data)
            except OSError as exc:
                log("NVA send failed: %s" % exc, "debug")
                self.terminated = True

    def send_res(self, counter, data=None):
        if data is None:
            binary = struct.pack(">cBI", RET_CMD, 0, counter)
        else:
            payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
            binary = struct.pack(
                ">cB2I%ds" % len(payload),
                RET_CMD,
                1,
                counter,
                len(payload),
                payload,
            )
        self.send(binary)

    def send_ping(self):
        counter = self._next_counter()
        self.send(struct.pack(">cBI", PING, 0, counter))

    def send_cmd(self, cmd, data=None):
        counter = self._next_counter()
        cmd_bytes = cmd.encode("utf-8")
        cmd_len = len(cmd_bytes)
        if data is None:
            binary = struct.pack(
                ">cBI2B7sB%ds" % cmd_len,
                SEND_CMD,
                2,
                counter,
                1,
                7,
                COMMAND,
                cmd_len,
                cmd_bytes,
            )
        else:
            payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
            binary = struct.pack(
                ">cBI2B7sB%dsI%ds" % (cmd_len, len(payload)),
                SEND_CMD,
                3,
                counter,
                1,
                7,
                COMMAND,
                cmd_len,
                cmd_bytes,
                len(payload),
                payload,
            )
        self.send(binary)

    def run(self):
        self.opened_at = time.time()
        self.sock.settimeout(1.0)
        try:
            while not self.terminated:
                try:
                    data = self.sock.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    break
                self.parse_request(data)
        finally:
            self.close()

    def parse_request(self, data):
        self.cache += data
        index = 0
        length = len(self.cache)
        while index < length:
            if length - index < 6:
                break
            header = self.cache[index:index + 6]
            if header[0] not in (SEND_CMD[0], RET_CMD[0]):
                index += 1
                continue

            try:
                cmd, all_len, counter = struct.unpack(">cBI", header)
                if cmd == SEND_CMD:
                    if all_len not in (2, 3):
                        index += 1
                        continue
                    if length - index - 6 < 10:
                        break
                    n, cmd_len, cmd_name, method_len = struct.unpack(
                        ">BB7sB", self.cache[index + 6:index + 16]
                    )
                    if n != 1 or cmd_len != 7 or cmd_name != COMMAND:
                        index += 1
                        continue
                    if all_len == 2:
                        if length - index - 16 < method_len:
                            break
                        method = struct.unpack(
                            ">%ds" % method_len,
                            self.cache[index + 16:index + 16 + method_len],
                        )[0]
                        self.server.on_command(
                            self, method.decode("utf-8", "replace"), counter, None
                        )
                        index += 16 + method_len
                    else:
                        if length - index - 16 < method_len + 4:
                            break
                        method, param_len = struct.unpack(
                            ">%dsI" % method_len,
                            self.cache[index + 16:index + method_len + 20],
                        )
                        start = index + method_len + 20
                        if length - start < param_len:
                            break
                        raw = struct.unpack(
                            ">%ds" % param_len,
                            self.cache[start:start + param_len],
                        )[0]
                        try:
                            params = json.loads(raw.decode("utf-8"))
                        except Exception as exc:
                            log("NVA bad JSON: %s" % exc, "warning")
                        else:
                            self.server.on_command(
                                self,
                                method.decode("utf-8", "replace"),
                                counter,
                                params,
                            )
                        index = start + param_len
                else:
                    if all_len == 0:
                        self.server.on_response(self, counter, None)
                        index += 6
                    elif all_len == 1:
                        if length - index - 6 < 4:
                            break
                        param_len = struct.unpack(
                            ">I", self.cache[index + 6:index + 10]
                        )[0]
                        start = index + 10
                        if length - start < param_len:
                            break
                        raw = struct.unpack(
                            ">%ds" % param_len,
                            self.cache[start:start + param_len],
                        )[0]
                        try:
                            params = json.loads(raw.decode("utf-8"))
                        except Exception as exc:
                            log("NVA bad response JSON: %s" % exc, "warning")
                        else:
                            self.server.on_response(self, counter, params)
                        index = start + param_len
                    else:
                        index += 1
            except Exception as exc:
                log("NVA parse error: %s" % exc, "warning")
                index += 1

        self.cache = self.cache[index:]
