#!/usr/bin/env python3
"""A tiny NVA client used to exercise the protocol spike."""

import argparse
import json
import socket
import struct
import time
import uuid

COMMAND = b"Command"
SEND_CMD = b"\xe0"
RET_CMD = b"\xc0"
PING = b"\xe4"


def frame_cmd(method, counter, params=None):
    cmd = method.encode()
    if params is None:
        return struct.pack(
            ">cBI2B7sB%ds" % len(cmd),
            SEND_CMD, 2, counter, 1, 7, COMMAND, len(cmd), cmd,
        )
    payload = json.dumps(params, separators=(",", ":")).encode()
    return struct.pack(
        ">cBI2B7sB%dsI%ds" % (len(cmd), len(payload)),
        SEND_CMD, 3, counter, 1, 7, COMMAND, len(cmd), cmd,
        len(payload), payload,
    )


def frame_res(counter, params=None):
    if params is None:
        return struct.pack(">cBI", RET_CMD, 0, counter)
    payload = json.dumps(params, separators=(",", ":")).encode()
    return struct.pack(">cB2I%ds" % len(payload), RET_CMD, 1, counter,
                       len(payload), payload)


def read_until(sock, marker, timeout=3.0):
    sock.settimeout(timeout)
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def dump_frames(data):
    i = 0
    while i + 6 <= len(data):
        if data[i] not in (SEND_CMD[0], RET_CMD[0], PING[0]):
            i += 1
            continue
        kind = data[i:i + 1]
        n = data[i + 1]
        counter = struct.unpack(">I", data[i + 2:i + 6])[0]
        if kind == SEND_CMD:
            if n not in (2, 3) or i + 16 > len(data):
                i += 1
                continue
            _, cmd_len, cmd_name, method_len = struct.unpack(
                ">BB7sB", data[i + 6:i + 16]
            )
            if cmd_name != COMMAND or i + 16 + method_len > len(data):
                i += 1
                continue
            method = data[i + 16:i + 16 + method_len].decode("utf-8", "replace")
            pos = i + 16 + method_len
            params = None
            if n == 3:
                if pos + 4 > len(data):
                    break
                param_len = struct.unpack(">I", data[pos:pos + 4])[0]
                pos += 4
                if pos + param_len > len(data):
                    break
                raw = data[pos:pos + param_len]
                pos += param_len
                try:
                    params = json.loads(raw.decode())
                except Exception:
                    params = raw
            print("  CMD #%d %s %s" % (counter, method, params))
            i = pos
        elif kind == RET_CMD:
            if n == 0:
                print("  RES #%d" % counter)
                i += 6
            elif n == 1:
                if i + 10 > len(data):
                    break
                param_len = struct.unpack(">I", data[i + 6:i + 10])[0]
                if i + 10 + param_len > len(data):
                    break
                raw = data[i + 10:i + 10 + param_len]
                i += 10 + param_len
                try:
                    params = json.loads(raw.decode())
                except Exception:
                    params = raw
                print("  RES #%d %s" % (counter, params))
            else:
                i += 1
        else:
            print("  PING #%d" % counter)
            i += 6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host", nargs="?", default="127.0.0.1")
    parser.add_argument("port", nargs="?", type=int, default=9958)
    args = parser.parse_args()

    session = str(uuid.uuid4())
    client_uuid = "Y" + "".join(
        __import__("random").choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        for _ in range(35)
    )
    sock = socket.create_connection((args.host, args.port), timeout=5)
    handshake = (
        "SETUP /projection NVA/1.0\r\n"
        "Session: %s\r\n"
        "NvaVersion: 1\r\n"
        "Connection: Keep-Alive\r\n"
        "UUID: %s\r\n"
        "User-Agent: Linux/3.0.0 UPnP/1.0 Platinum/1.0.5.13\r\n"
        "Host: %s:%d\r\n"
        "\r\n"
    ) % (session, client_uuid, args.host, args.port)
    sock.sendall(handshake.encode())
    response = read_until(sock, b"\r\n\r\n")
    print(response.decode("utf-8", "replace"))

    commands = [
        ("GetVolume", None),
        ("Play", {
            "aid": "123456",
            "cid": "789012",
            "epid": 0,
            "season_id": 0,
            "oid": "123456",
            "content_type": 1,
            "seekTs": 5,
            "desire_qn": 80,
            "userDesireSpeed": 1,
        }),
        ("Pause", None),
        ("Resume", None),
        ("SwitchDanmaku", {"open": "false"}),
        ("SwitchSpeed", {"speed": "1.5"}),
        ("Seek", {"seekTs": 30}),
        ("Stop", None),
    ]
    for counter, (method, params) in enumerate(commands, start=1):
        print("send:", method, params)
        sock.sendall(frame_cmd(method, counter, params))
        time.sleep(0.35)
        try:
            data = sock.recv(65535)
        except socket.timeout:
            data = b""
        if data:
            print("recv %d bytes:" % len(data))
            dump_frames(data)

    time.sleep(1.2)
    try:
        data = sock.recv(65535)
    except socket.timeout:
        data = b""
    if data:
        print("recv %d bytes:" % len(data))
        dump_frames(data)

    sock.close()


if __name__ == "__main__":
    main()
