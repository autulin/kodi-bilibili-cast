#!/usr/bin/env python3
"""Run the receiver outside Kodi for protocol testing."""

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "service.bili.cast"))

from lib.device import DeviceInfo  # noqa: E402
from lib.server import BiliCastServer  # noqa: E402
from lib.storage import load_or_create_uuid  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9958)
    parser.add_argument("--name", default="我的小电视")
    parser.add_argument("--no-ssdp", action="store_true")
    args = parser.parse_args()

    device = DeviceInfo(
        uuid=load_or_create_uuid(),
        friendly_name=args.name,
        version="dev",
    )
    server = BiliCastServer(
        device=device,
        port=args.port,
        enable_ssdp=not args.no_ssdp,
    )
    server.start()
    print("device uuid:", device.uuid)
    print("HTTP/NVA port:", server.port)
    print("press Ctrl-C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()


if __name__ == "__main__":
    main()
