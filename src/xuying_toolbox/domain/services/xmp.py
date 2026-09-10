"""Adobe XMP 的纯字节解析与更新，不执行文件读写。"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from xml.etree import ElementTree

from xuying_toolbox.domain.models.photo import JpegXmpSegment

XMP_NAMESPACE = "http://ns.adobe.com/xap/1.0/"
XMP_JPEG_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
RE_RATING_ATTR = re.compile(
    rb'(?<![A-Za-z0-9_.:-])(?:xmp|xap):Rating\s*=\s*["\']\s*'
    rb'([0-5])(?:\.0+)?\s*["\']',
    re.IGNORECASE,
)
RE_RATING_ELEM = re.compile(
    rb"<(?:xmp|xap):Rating\b[^>]*>\s*"
    rb"([0-5])(?:\.0+)?\s*"
    rb"</(?:xmp|xap):Rating\s*>",
    re.IGNORECASE,
)
RE_LABEL_ATTR = re.compile(
    rb'(?<![A-Za-z0-9_.:-])(?:xmp|xap):Label\s*=\s*"([^"]*)"',
    re.IGNORECASE,
)
RE_LABEL_ATTR_SINGLE = re.compile(
    rb"(?<![A-Za-z0-9_.:-])(?:xmp|xap):Label\s*=\s*'([^']*)'",
    re.IGNORECASE,
)
RE_LABEL_ELEM = re.compile(
    rb"<(?:xmp|xap):Label\b[^>]*>\s*([^<]*?)\s*"
    rb"</(?:xmp|xap):Label\s*>",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class XmpProperties:
    rating: int
    label: str | None


def read_properties(content: bytes | None) -> XmpProperties:
    return XmpProperties(_read_rating(content), _read_label(content))


def make_xmp(rating: int | None, label: str | None) -> bytes:
    rating_element = f"\n   <xmp:Rating>{rating}</xmp:Rating>" if rating is not None else ""
    label_element = f"\n   <xmp:Label>{html.escape(label)}</xmp:Label>" if label is not None else ""
    xml = f'''<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:xmp="{XMP_NAMESPACE}">{rating_element}{label_element}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''
    return xml.encode()


def update_properties(
    content: bytes | None,
    rating: int | None,
    label: str | None,
) -> bytes:
    """更新已有 XMP；无法安全插入未知结构时拒绝写入。"""

    if content is None:
        return make_xmp(rating, label)
    updated = content
    if rating is not None:
        updated, supported = _replace_or_insert(updated, "Rating", str(rating))
        if not supported:
            raise ValueError("现有 XMP 无法安全更新 Rating，已停止写入。")
    if label is not None:
        updated, supported = _replace_or_insert(updated, "Label", label)
        if not supported:
            raise ValueError("现有 XMP 无法安全更新 Label，已停止写入。")
    return updated


def find_jpeg_segment(content: bytes) -> JpegXmpSegment | None:
    if not content.startswith(b"\xff\xd8"):
        return None
    position = 2
    while position < len(content):
        if content[position] != 0xFF:
            return None
        while position < len(content) and content[position] == 0xFF:
            position += 1
        if position >= len(content):
            return None
        marker = content[position]
        start = position - 1
        position += 1
        if marker in {0xD9, 0xDA}:
            return None
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            continue
        if position + 2 > len(content):
            return None
        segment_length = int.from_bytes(content[position : position + 2], "big")
        end = position + segment_length
        if segment_length < 2 or end > len(content):
            return None
        payload = content[position + 2 : end]
        if marker == 0xE1 and payload.startswith(XMP_JPEG_HEADER):
            return JpegXmpSegment(start, end, payload)
        position = end
    return None


def replace_jpeg_segment(
    content: bytes,
    segment: JpegXmpSegment,
    payload: bytes,
) -> bytes:
    segment_length = len(payload) + 2
    if segment_length > 65535:
        raise ValueError("XMP 数据过大，无法写入 JPG。")
    replacement = b"\xff\xe1" + segment_length.to_bytes(2, "big") + payload
    return content[: segment.start] + replacement + content[segment.end :]


def insert_jpeg_xmp(
    content: bytes,
    rating: int | None,
    label: str | None,
) -> bytes:
    if not content.startswith(b"\xff\xd8"):
        raise ValueError("目标 JPG 文件头无效，已停止写入。")
    payload = XMP_JPEG_HEADER + make_xmp(rating, label)
    segment_length = len(payload) + 2
    if segment_length > 65535:
        raise ValueError("XMP 数据过大，无法写入 JPG。")
    segment = b"\xff\xe1" + segment_length.to_bytes(2, "big") + payload
    return content[:2] + segment + content[2:]


def _xml_value(content: bytes | None, property_name: str) -> str | None:
    if not content:
        return None
    try:
        root = ElementTree.fromstring(content)
    except (ElementTree.ParseError, ValueError):
        return None
    qualified_name = f"{{{XMP_NAMESPACE}}}{property_name}"
    for element in root.iter():
        value = element.attrib.get(qualified_name)
        if value is not None:
            return value
        if element.tag == qualified_name and element.text is not None:
            return element.text
    return None


def _xmp_prefix(content: bytes | None) -> bytes | None:
    if not content:
        return None
    pattern = re.compile(
        rb"xmlns:([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*(['\"])"
        + re.escape(XMP_NAMESPACE.encode("ascii"))
        + rb"\2",
        re.IGNORECASE,
    )
    match = pattern.search(content)
    return match.group(1) if match else None


def _parse_rating(value: str | None) -> int:
    if value is None:
        return 0
    match = re.fullmatch(r"\s*([0-5])(?:\.0+)?\s*", value)
    return int(match.group(1)) if match else 0


def _read_rating(content: bytes | None) -> int:
    if not content:
        return 0
    xml_rating = _xml_value(content, "Rating")
    if xml_rating is not None:
        return _parse_rating(xml_rating)
    match = RE_RATING_ATTR.search(content) or RE_RATING_ELEM.search(content)
    return int(match.group(1)) if match else 0


def _read_label(content: bytes | None) -> str | None:
    if not content:
        return None
    xml_label = _xml_value(content, "Label")
    if xml_label is not None:
        return xml_label or None
    match = (
        RE_LABEL_ATTR.search(content)
        or RE_LABEL_ATTR_SINGLE.search(content)
        or RE_LABEL_ELEM.search(content)
    )
    if not match:
        return None
    value = match.group(1).decode("utf-8", errors="replace")
    return html.unescape(value) or None


def _replace_or_insert(
    content: bytes,
    property_name: str,
    value: str,
) -> tuple[bytes, bool]:
    escaped = html.escape(value, quote=True).encode()
    patterns = (
        (RE_RATING_ATTR, RE_RATING_ELEM)
        if property_name == "Rating"
        else (RE_LABEL_ATTR, RE_LABEL_ATTR_SINGLE, RE_LABEL_ELEM)
    )
    for pattern in patterns:
        match = pattern.search(content)
        if match:
            if match.group(1) == escaped:
                return content, True
            return content[: match.start(1)] + escaped + content[match.end(1) :], True

    prefix = _xmp_prefix(content)
    if prefix is None:
        return content, False
    start = content.find(b"<rdf:Description")
    tag_end = content.find(b">", start)
    if start < 0 or tag_end < 0:
        return content, False
    element_name = prefix + b":" + property_name.encode()
    element = b"\n   <" + element_name + b">" + escaped + b"</" + element_name + b">"
    if content[tag_end - 1 : tag_end] == b"/":
        opening = content[start : tag_end - 1] + b">"
        replacement = opening + element + b"\n  </rdf:Description>"
        return content[:start] + replacement + content[tag_end + 1 :], True
    return content[: tag_end + 1] + element + content[tag_end + 1 :], True
