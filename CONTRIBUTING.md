# Contributing

Thanks for your interest. This is a small hobby project; issues and pull
requests are welcome.

## Before you start

- This addon must run inside Kodi's bundled Python. **Do not add third-party
  dependencies.** Use the standard library (`urllib`, `socketserver`,
  `xml.etree`, etc.).
- Keep the protocol layer (`lib/nva.py`, `lib/ssdp.py`) free of Kodi imports so
  it can run on a normal desktop for testing.
- Test the protocol layer without Kodi first:

```bash
python3 tools/dev_run.py --port 19958
python3 tools/fake_nva_client.py 127.0.0.1 19958
```

## Pull requests

1. Keep changes focused; one concern per PR.
2. Run `python3 -m compileall -q service.bili.cast tools`.
3. If you change playback or protocol behaviour, describe what you tested and
   on which device/Kodi version.
4. Do not include logs, `accessKey` values, or device-specific paths.

## Reporting playback problems

Please include:

- Kodi version and platform (Android / CoreELEC / LibreELEC)
- box model and SoC
- the `service.bili.cast` lines from `kodi.log`
- whether the video plays at 720P or 1080P (`playurl qn=`)

## License

By contributing you agree that your changes are licensed under the project's
MIT license.
