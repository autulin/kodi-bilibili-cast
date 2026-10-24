#!/usr/bin/env python3
"""Send a real Play command to a running receiver, then stop it.

The access key is read from BILI_ACCESS_KEY so it does not appear in shell
history or process arguments.
"""

import argparse
import json
import os
import random
import socket
import struct
import sys
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
    parser.add_argument("aid")
    parser.add_argument("cid")
    parser.add_argument("--oid", default=None)
    parser.add_argument("--epid", type=int, default=0)
    parser.add_argument("--season", type=int, default=0)
    parser.add_argument("--content-type", default="0")
    parser.add_argument("--qn", type=int, default=80)
    parser.add_argument("--seek", type=int, default=0)
    parser.add_argument("--wait", type=float, default=15.0)
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--no-danmaku", action="store_true")
    args = parser.parse_args()

    access_key = os.environ.get("BILI_ACCESS_KEY", "")
    if not access_key:
        print("BILI_ACCESS_KEY is not set", file=sys.stderr)
        return 1

    session = str(uuid.uuid4())
    client_uuid = "Y" + "".join(
        random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(35)
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
    print(read_until(sock, b"\r\n\r\n").decode("utf-8", "replace"))

    play_params = {
        "aid": args.aid,
        "cid": args.cid,
        "biz_id": 0,
        "biz_session_id": str(uuid.uuid4()),
        "oid": args.oid or (str(args.epid) if args.epid else args.aid),
        "accessKey": access_key,
        "proj_type": "1",
        "sessionId": str(uuid.uuid4()),
        "roomId": "0",
        "userDesireSpeed": "1",
        "epId": str(args.epid),
        "seekTs": args.seek,
        "type": 0,
        "danmakuSwitchSave": not args.no_danmaku,
        "contentType": str(args.content_type),
        "isOpen": "true",
        "autoNext": "true",
        "accessCode": "",
        "seasonId": str(args.season),
        "mobileVersion": "37501100",
        "desc": 1,
        "startKey": "",
        "userDesireQn": args.qn,
    }
    print("send Play (access key redacted)")
    sock.sendall(frame_cmd("Play", 1, play_params))

    sock.settimeout(1.0)
    deadline = time.time() + args.wait
    while time.time() < deadline:
        try:
            data = sock.recv(65535)
        except socket.timeout:
            continue
        if not data:
            break
        dump_frames(data)

    if args.stop:
        print("send Stop")
        sock.sendall(frame_cmd("Stop", 2, None))
        try:
            data = sock.recv(65535)
            if data:
                dump_frames(data)
        except socket.timeout:
            pass
    sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
