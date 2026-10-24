# kodi-bilibili-cast

Turn Kodi into a Bilibili "云视听小电视" cast receiver: cast from the Bilibili
mobile app straight to Kodi, with **1080P** and **danmaku** (bullet comments).

No extra app on the phone and no login on the TV side. The addon implements
Bilibili's private "哔哩必连" (NVA) cast protocol inside Kodi, so the phone lists
it as "我的小电视(有弹幕)".

[中文说明](README.md)

## Features

- **Native Bilibili casting** — SSDP discovery; pick "我的小电视(有弹幕)" in the
  phone's cast list
- **1080P** — DASH playback through `inputstream.adaptive`; `durl` is only a
  fallback (720P)
- **Danmaku** — Bilibili XML converted to ASS subtitles, with configurable
  area, font size, opacity, and line count
- **Full controls** — play, pause, resume, seek, stop, volume, speed, quality
  switch, danmaku toggle
- **Status sync** — progress, play state, quality, and speed reported back to
  the phone every second
- **Standard library only** — the only external piece is Kodi's own
  `inputstream.adaptive`
- **Cross-platform** — Kodi 21.x on Android and CoreELEC/LibreELEC

## Known limitations

- Danmaku and regular subtitles share Kodi's single subtitle track, so they
  cannot be shown together yet
- Live streams, DLNA playback, and automatic next-episode are not implemented
- Danmaku sent from the phone is shown as a notification only
- 1080P depends on the source; 720P-only sources fall back to `durl`

## Quick start

1. Install `inputstream.adaptive` from the official Kodi repository
2. Download `service.bili.cast-<version>.zip` from
   [Releases](https://github.com/autulin/kodi-bilibili-cast/releases), or build
   it yourself with `./tools/build_zip.sh`
3. Kodi → Settings → Add-ons → Install from zip file
4. In the Bilibili app, open a video → TV icon → "我的小电视(有弹幕)"

See [docs/install.md](docs/install.md) for details.

> **Android users:** the official "云视听小电视" app also listens on
> `tcp/9958`. Stop it before using this addon
> (`adb shell am force-stop com.xiaodianshi.tv.yst`), otherwise the phone
> cannot connect. CoreELEC has no such conflict.

## Architecture

```text
Bilibili mobile app
  → SSDP discovery (udp/1900)
  → NVA/1.0 handshake (tcp/9958)
  → Play {aid, cid, accessKey, userDesireQn, ...}
  → x/tv/playurl (fnval=4048) → DASH
  → generated MPD → http://<box>:9958/dash/*.mpd → inputstream.adaptive
  → danmaku XML → ASS → setSubtitles
  → OnProgress / OnPlayState every second
```

See [docs/architecture.md](docs/architecture.md).

## Compatibility

| Environment | Status |
|---|---|
| Kodi 21.3 / Android 7.1.2 / Phicomm N1 (S905D) | Tested |
| Kodi 21.1.0 / CoreELEC 21.1.1-Omega / Phicomm N1 (S905D) | Tested |

On CoreELEC playback uses the native Amlogic decoder
(`DVDVideoCodecAmlogic`); 1080P DASH, danmaku, pause/seek/stop all work. See
[docs/coreelec.md](docs/coreelec.md).

If an Android Amlogic box shows "freeze/black screen after stop", it is the
`videoplayer.usemediacodecsurface` problem. The addon disables it by default;
see [docs/install.md](docs/install.md#android-mediacodec-surface).

## Development

```bash
# Run the protocol layer without Kodi
python3 tools/dev_run.py --port 19958

# Simulate phone NVA commands
python3 tools/fake_nva_client.py 127.0.0.1 19958

# Build an installable zip
./tools/build_zip.sh
```

More in [docs/development.md](docs/development.md).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Credits and license

The NVA protocol layer is based on the MIT-licensed
[Macast nirvana plugin](https://github.com/xfangfang/Macast-plugins/tree/main/nirvana).
Protocol details reference
[xfangfang's protocol analysis](https://xfangfang.github.io/028).
[Yiiiike/bilibili-mobile-cast-to-pc](https://github.com/Yiiiike/bilibili-mobile-cast-to-pc)
was used as a behavioral reference only; no code was copied.

Released under the MIT license. See [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Disclaimer

This is an unofficial third-party project and is not affiliated with or
endorsed by Bilibili. It is intended for personal use on your own devices with
your own account. Please follow Bilibili's terms of service and local laws; do
not use it for commercial purposes or content redistribution.
