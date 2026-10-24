#!/usr/bin/env python3
"""Send an SSDP M-SEARCH and print replies."""

import argparse
import socket
import time

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--st",
        default="urn:app-bilibili-com:service:NirvanaControl:3",
    )
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    message = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: %s:%d\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 2\r\n"
        "ST: %s\r\n"
        "\r\n"
    ) % (SSDP_ADDR, SSDP_PORT, args.st)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(0.5)
    sock.sendto(message.encode(), (SSDP_ADDR, SSDP_PORT))

    deadline = time.time() + args.timeout
    seen = set()
    while time.time() < deadline:
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        text = data.decode("utf-8", "replace")
        if text in seen:
            continue
        seen.add(text)
        print("from", addr)
        print(text)
        print("-" * 60)
    sock.close()


if __name__ == "__main__":
    main()
