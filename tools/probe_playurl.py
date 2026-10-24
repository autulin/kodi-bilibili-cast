#!/usr/bin/env python3
"""Probe the Bilibili TV playurl API without printing the access key."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "service.bili.cast"))

from lib.bili_api import BiliApiError, get_tv_playurl  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("aid")
    parser.add_argument("cid")
    parser.add_argument("--oid", default=None)
    parser.add_argument("--epid", type=int, default=0)
    parser.add_argument("--season", type=int, default=0)
    parser.add_argument("--qn", type=int, default=80)
    parser.add_argument("--playurl-type", type=int, default=1)
    parser.add_argument("--access-key", default="")
    args = parser.parse_args()

    try:
        result = get_tv_playurl(
            aid=args.aid,
            cid=args.cid,
            oid=args.oid or args.aid,
            epid=args.epid,
            season_id=args.season,
            access_key=args.access_key or os.environ.get("BILI_ACCESS_KEY", ""),
            qn=args.qn,
            playurl_type=args.playurl_type,
        )
    except BiliApiError as exc:
        print("BiliApiError:", exc, "code=", exc.code)
        return
    except Exception as exc:
        print("error:", exc)
        return

    url = result["url"] or ""
    print("format:", result["format"])
    print("quality:", result["quality"])
    print("accept_quality:", result["accept_quality"])
    print("duration:", result["duration"])
    print("is_login:", result.get("is_login"), "is_vip:", result.get("is_vip"))
    print("dash:", bool(result.get("dash")))
    if result.get("dash"):
        dash = result["dash"]
        print("dash_video:", [
            (item.get("id"), item.get("width"), item.get("height"), item.get("codecs"))
            for item in (dash.get("video") or [])[:8]
        ])
        print("dash_audio:", [
            (item.get("id"), item.get("bandwidth"))
            for item in (dash.get("audio") or [])[:4]
        ])
    print("url_host:", url.split("/")[2] if "://" in url else "")
    print("url_has_query:", "?" in url)
    print("qn_desc:", json.dumps(result["qn_desc"], ensure_ascii=False))


if __name__ == "__main__":
    main()
