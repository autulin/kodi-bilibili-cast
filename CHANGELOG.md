# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Nothing yet.

## [0.2.0] - 2026-10-24

First public release.

### Added

- Kodi service addon that implements Bilibili's Nirvana (NVA) cast protocol:
  SSDP discovery, UPnP device description, `NirvanaControl` SOAP, and the NVA
  binary control channel on `tcp/9958`.
- Bilibili TV `x/tv/playurl` integration with `fnval=4048` so casts can play
  in **1080P** via DASH instead of the 720P `durl` muxed stream.
- DASH to MPD conversion (`lib/dash.py`) using `SegmentBase` byte ranges, served
  over the addon's own HTTP port for `inputstream.adaptive`.
- Danmaku support: Bilibili XML download, ASS conversion, and
  `setSubtitles()` display with configurable area, font size, opacity, and line
  count.
- Phone controls: `Play`, `Pause`, `Resume`, `Seek`, `Stop`, `GetVolume`,
  `SetVolume`, `SwitchQn`, `SwitchSpeed`, and `SwitchDanmaku`.
- Status callbacks: `OnPlayState`, `OnProgress`, `OnEpisodeSwitch`,
  `OnQnSwitch`, `OnDanmakuSwitch`, and `SpeedChanged`.
- Android compatibility switch that disables `videoplayer.usemediacodecsurface`
  on Amlogic boxes, fixing window teardown on stop/quality switch.
- Developer tools: `dev_run.py`, `fake_nva_client.py`, `cast_test.py`,
  `probe_playurl.py`, `ssdp_search.py`, and `build_zip.sh`.
- Documentation: architecture, install, development, troubleshooting, and
  CoreELEC notes.

### Known limitations

- Danmaku and regular subtitles share Kodi's single subtitle track.
- Live streams, DLNA playback, and automatic next-episode are not implemented.
- Danmaku sent from the phone is shown as a notification only.
- `durl` fallback is limited to 720P.

### Tested on

- Phicomm N1 (Amlogic S905D) / Android 7.1.2 / Kodi 21.3 / Python 3.
- Phicomm N1 (Amlogic S905D) / CoreELEC 21.1.1-Omega / Kodi 21.1.0,
  kernel 4.9.269, `Phicomm,N1` device tree.
