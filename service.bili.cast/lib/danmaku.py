"""Download Bilibili danmaku XML and convert it to a Kodi-friendly ASS file.

The collision/placement approach is based on the MIT-licensed Macast nirvana
plugin, adapted for a 1920x1080 canvas and a configurable top area.
"""

import os
import xml.etree.ElementTree as ET

from .bili_api import get_danmaku_xml
from .storage import addon_data_dir

DEFAULT_AREA = 0.25
DEFAULT_FONT_SIZE = 48
DEFAULT_OPACITY = 0.85
DEFAULT_MAX_LINES = 4
PLAY_RES_X = 1920
PLAY_RES_Y = 1080
SCROLL_SECONDS = 10.0
FIXED_SECONDS = 4.0
MAX_COMMENTS = 12000


def _text_width(text, font_size):
    width = 0
    for char in text:
        width += font_size if ord(char) > 0x2E80 else font_size * 0.58
    return max(1, int(width))


def _escape_text(text):
    text = (text or "").replace("\\", "\\\\")
    text = text.replace("{", "\\{").replace("}", "\\}")
    text = text.replace("\r", "").replace("\n", "\\N")
    return text


def _ass_color(color_int, opacity):
    try:
        color_int = int(color_int)
    except (TypeError, ValueError):
        color_int = 0xFFFFFF
    color_int &= 0xFFFFFF
    red = (color_int >> 16) & 0xFF
    green = (color_int >> 8) & 0xFF
    blue = color_int & 0xFF
    # ASS alpha is inverted: 0x00 is opaque, 0xFF is transparent.
    alpha = int((1.0 - max(0.0, min(1.0, opacity))) * 255)
    # ASS is \c&HAABBGGRR&.
    return "\\c&H%02X%02X%02X%02X&" % (alpha, blue, green, red)


def _sec_to_ass(seconds):
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return "%d:%02d:%05.2f" % (hours, minutes, secs)


def _line_count(area, font_size):
    height = int(PLAY_RES_Y * area)
    line_height = max(font_size + 12, 1)
    return max(1, min(DEFAULT_MAX_LINES, height // line_height)), line_height, height


def convert_xml(xml_bytes, output_path, area=DEFAULT_AREA,
                font_size=DEFAULT_FONT_SIZE, opacity=DEFAULT_OPACITY,
                max_lines=None):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("invalid danmaku xml: %s" % exc)

    if max_lines is not None:
        line_height = max(font_size + 12, 1)
        area_height = int(PLAY_RES_Y * max(0.05, min(1.0, area)))
        max_by_area = max(1, area_height // line_height)
        lines = max(1, min(int(max_lines), max_by_area))
        area_height = min(PLAY_RES_Y, lines * line_height)
    else:
        lines, line_height, area_height = _line_count(area, font_size)

    scroll_free = [0.0] * lines
    top_free = [0.0] * lines
    bottom_free = [0.0] * lines

    comments = []
    for node in root.findall("d"):
        raw = node.get("p") or ""
        text = node.text or ""
        if not raw or not text.strip():
            continue
        fields = raw.split(",")
        if len(fields) < 4:
            continue
        try:
            start = float(fields[0])
            kind = int(fields[1])
            color = int(fields[3])
        except (TypeError, ValueError):
            continue
        if kind >= 7:
            continue
        comments.append((start, kind, color, text.strip()))

    comments.sort(key=lambda item: item[0])
    if len(comments) > MAX_COMMENTS:
        # Keep an even sample instead of only the beginning of the video.
        step = max(1, len(comments) // MAX_COMMENTS)
        comments = comments[::step][:MAX_COMMENTS]

    events = []
    for start, kind, color, text in comments:
        escaped = _escape_text(text)
        width = _text_width(text, font_size)
        color_tag = _ass_color(color, opacity)
        outline = "\\bord2\\shad0"
        font_tag = "\\fs%d" % font_size

        if kind == 5:
            index = _find_slot(top_free, start)
            if index is None:
                continue
            top_free[index] = start + FIXED_SECONDS
            y = index * line_height + line_height
            effect = "\\an8\\pos(%d,%d)" % (PLAY_RES_X // 2, y)
            end = start + FIXED_SECONDS
        elif kind == 4:
            index = _find_slot(bottom_free, start)
            if index is None:
                continue
            bottom_free[index] = start + FIXED_SECONDS
            y = area_height - index * line_height
            effect = "\\an2\\pos(%d,%d)" % (PLAY_RES_X // 2, max(line_height, y))
            end = start + FIXED_SECONDS
        else:
            index = _find_scroll_slot(scroll_free, start, width)
            if index is None:
                continue
            scroll_free[index] = start + SCROLL_SECONDS
            y = index * line_height + line_height
            effect = "\\move(%d,%d,%d,%d)" % (PLAY_RES_X, y, -width, y)
            end = start + SCROLL_SECONDS

        events.append(
            "Dialogue: 0,%s,%s,Default,,0,0,0,,{%s%s%s%s}%s"
            % (
                _sec_to_ass(start),
                _sec_to_ass(end),
                effect,
                font_tag,
                color_tag,
                outline,
                escaped,
            )
        )

    header = """[Script Info]
Title: Bilibili Danmaku
ScriptType: V4.00+
Collisions: Normal
PlayResX: %d
PlayResY: %d
Timer: 100.0
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default, sans-serif, %d, &H30FFFFFF, &H30FFFFFF, &H30000000, &H30000000, 0, 0, 0, 0, 100, 100, 0, 0, 1, 2, 0, 7, 0, 0, 0, 0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" % (PLAY_RES_X, PLAY_RES_Y, font_size)

    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(header)
        handle.write("\n".join(events))
        handle.write("\n")
    return output_path, len(events)


def _find_slot(free_at, start):
    for index, value in enumerate(free_at):
        if start >= value:
            return index
    return None


def _find_scroll_slot(free_at, start, width):
    # A line can be reused once the previous comment has moved far enough left
    # for the new comment to enter without overlapping.
    text_time = (PLAY_RES_X * SCROLL_SECONDS) / (PLAY_RES_X + width)
    for index, value in enumerate(free_at):
        if start + text_time >= value:
            return index
    return None


def download_and_convert(cid, output_path=None, area=DEFAULT_AREA,
                         font_size=DEFAULT_FONT_SIZE, opacity=DEFAULT_OPACITY,
                         max_lines=None, timeout=15):
    if output_path is None:
        output_path = os.path.join(
            addon_data_dir(), "danmaku_%s.ass" % str(cid)
        )
    xml_bytes = get_danmaku_xml(cid, timeout=timeout)
    return convert_xml(
        xml_bytes,
        output_path,
        area=area,
        font_size=font_size,
        opacity=opacity,
        max_lines=max_lines,
    )
