# Security policy

## Reporting a vulnerability

Please open a private security advisory on GitHub, or contact the maintainer
directly. Do not open a public issue for security problems.

## Sensitive data

The Bilibili cast protocol carries a per-session `accessKey`. This addon:

- never writes `accessKey`, `accessCode`, `sessionId`, or `biz_session_id` to
  the Kodi log (they are replaced with `***`)
- never sends those values anywhere except to Bilibili's own API endpoints
- stores only a random device UUID under Kodi's `addon_data` directory

If you share logs in an issue, please check them once more yourself. Older
versions (before 0.2.0) may have logged a full access key.

## Scope

This addon only receives casts from devices on the same local network. It does
not open any port to the internet and has no cloud component.
