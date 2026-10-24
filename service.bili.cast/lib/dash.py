"""Build a minimal DASH MPD for Bilibili's separated video/audio streams.

Bilibili's TV API returns ``durl`` (muxed, capped at 720P) and, when
``fnval=4048`` is requested, a DASH manifest with 1080P video and audio.
Kodi's ``inputstream.adaptive`` can play the DASH streams if we describe them
as an on-demand MPD with ``SegmentBase`` byte ranges.
"""

import os
import xml.sax.saxutils as saxutils

from .log import log
from .storage import addon_data_dir

DEFAULT_MAX_QN = 80
AVC = 7
HEVC = 12
AV1 = 13


def _iso_duration(seconds):
    try:
        seconds = max(0.0, float(seconds))
    except (TypeError, ValueError):
        seconds = 0.0
    return "PT%.3fS" % seconds


def _codec_rank(codecid):
    # Prefer AVC: the N1's Amlogic decoder handles it reliably and Kodi's
    # MediaCodec path is happiest with it.  HEVC is the fallback; AV1 is not
    # hardware decoded on this box.
    return {AVC: 0, HEVC: 1, AV1: 9}.get(codecid, 5)


def select_video(dash, max_qn=DEFAULT_MAX_QN):
    videos = [item for item in (dash.get("video") or []) if item.get("base_url")]
    if not videos:
        return None
    candidates = []
    for item in videos:
        try:
            qn = int(item.get("id", 0))
        except (TypeError, ValueError):
            continue
        if qn > max_qn:
            continue
        segment = item.get("segment_base") or {}
        if not segment.get("initialization") or not segment.get("index_range"):
            continue
        candidates.append((qn, _codec_rank(item.get("codecid")), item))
    if not candidates:
        return None
    # Highest quality first, then the most compatible codec.
    candidates.sort(key=lambda entry: (-entry[0], entry[1]))
    return candidates[0][2]


def select_audio(dash):
    audios = [item for item in (dash.get("audio") or []) if item.get("base_url")]
    if not audios:
        return None
    usable = []
    for item in audios:
        segment = item.get("segment_base") or {}
        if not segment.get("initialization") or not segment.get("index_range"):
            continue
        try:
            bandwidth = int(item.get("bandwidth", 0))
        except (TypeError, ValueError):
            bandwidth = 0
        usable.append((bandwidth, item))
    if not usable:
        return None
    usable.sort(key=lambda entry: -entry[0])
    return usable[0][1]


def _representation(item, kind):
    segment = item.get("segment_base") or {}
    attrs = {
        "id": str(item.get("id", "0")),
        "bandwidth": str(item.get("bandwidth", 0)),
    }
    if kind == "video":
        attrs["width"] = str(item.get("width", 0))
        attrs["height"] = str(item.get("height", 0))
        if item.get("codecs"):
            attrs["codecs"] = item["codecs"]
        if item.get("frame_rate"):
            attrs["frameRate"] = item["frame_rate"]
    else:
        if item.get("codecs"):
            attrs["codecs"] = item["codecs"]
        if item.get("audio_sampling_rate"):
            attrs["audioSamplingRate"] = str(item["audio_sampling_rate"])

    attr_text = " ".join(
        '%s="%s"' % (key, saxutils.escape(str(value), {'"': "&quot;"}))
        for key, value in attrs.items()
    )
    lines = [
        "      <Representation %s>" % attr_text,
        "        <BaseURL>%s</BaseURL>" % saxutils.escape(item["base_url"]),
        '        <SegmentBase indexRange="%s">'
        % saxutils.escape(str(segment.get("index_range", ""))),
        '          <Initialization range="%s"/>'
        % saxutils.escape(str(segment.get("initialization", ""))),
        "        </SegmentBase>",
        "      </Representation>",
    ]
    return "\n".join(lines)


def build_mpd(dash, duration, video, audio):
    duration_text = _iso_duration(duration)
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"',
        '     type="static"',
        '     mediaPresentationDuration="%s"' % duration_text,
        '     minBufferTime="PT1.5S"',
        '     profiles="urn:mpeg:dash:profile:isoff-on-demand:2011">',
        '  <Period id="0" duration="%s">' % duration_text,
        '    <AdaptationSet id="0" contentType="video" mimeType="video/mp4"',
        '                   segmentAlignment="true" startWithSAP="1"',
        '                   maxWidth="%s" maxHeight="%s">'
        % (video.get("width", 0), video.get("height", 0)),
        _representation(video, "video"),
        "    </AdaptationSet>",
        '    <AdaptationSet id="1" contentType="audio" mimeType="audio/mp4"',
        '                   segmentAlignment="true" lang="und">',
        _representation(audio, "audio"),
        "    </AdaptationSet>",
        "  </Period>",
        "</MPD>",
        "",
    ]
    return "\n".join(lines)


def write_mpd(cid, dash, duration, max_qn=DEFAULT_MAX_QN):
    video = select_video(dash, max_qn=max_qn)
    audio = select_audio(dash)
    if video is None or audio is None:
        return None, None
    content = build_mpd(dash, duration, video, audio)
    path = os.path.join(
        addon_data_dir(),
        "dash_%s_%s.mpd" % (str(cid), video.get("id", "0")),
    )
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
    except OSError as exc:
        log("write MPD failed: %s" % exc, "warning")
        return None, None
    log(
        "DASH MPD: video=%s %sx%s %s audio=%s duration=%s"
        % (
            video.get("id"),
            video.get("width"),
            video.get("height"),
            video.get("codecs"),
            audio.get("id"),
            duration,
        ),
        "info",
    )
    return path, video
