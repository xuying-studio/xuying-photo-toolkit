"""XMP 文件适配器：读取与原子写入，RAW 只写侧车。"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from xuying_toolbox.domain.models.photo import RAW_EXTENSIONS
from xuying_toolbox.domain.services.xmp import (
    XMP_JPEG_HEADER,
    XmpProperties,
    find_jpeg_segment,
    insert_jpeg_xmp,
    read_properties,
    replace_jpeg_segment,
    update_properties,
)
from xuying_toolbox.infrastructure.filesystem.scanner import preferred_sidecar


def is_raw(path: Path) -> bool:
    return path.suffix.casefold() in RAW_EXTENSIONS


def read(path: Path) -> XmpProperties:
    if is_raw(path):
        sidecar = preferred_sidecar(path)
        return read_properties(sidecar.read_bytes() if sidecar.exists() else None)
    payload = read_jpeg_xmp_payload(path)
    return read_properties(payload[len(XMP_JPEG_HEADER) :] if payload else None)


def write(path: Path, rating: int | None, label: str | None) -> None:
    if is_raw(path):
        sidecar = preferred_sidecar(path)
        existing = sidecar.read_bytes() if sidecar.exists() else None
        updated = (
            update_properties(existing, rating, label)
            if existing
            else update_properties(None, rating, label)
        )
        _atomic_write(sidecar, updated)
        actual = read(path)
    else:
        content = path.read_bytes()
        segment = find_jpeg_segment(content)
        if segment:
            updated_payload = update_properties(
                segment.payload[len(XMP_JPEG_HEADER) :],
                rating,
                label,
            )
            updated = replace_jpeg_segment(
                content,
                segment,
                XMP_JPEG_HEADER + updated_payload,
            )
        else:
            updated = insert_jpeg_xmp(content, rating, label)
        _atomic_write(path, updated)
        actual = read(path)
    if rating is not None and actual.rating != rating:
        raise ValueError("XMP 星标写入后校验失败。")
    if label is not None and actual.label != label:
        raise ValueError("XMP 颜色标签写入后校验失败。")


def read_jpeg_xmp_payload(path: Path) -> bytes | None:
    """只读取 JPEG metadata 区域，不加载压缩像素数据。"""

    try:
        with path.open("rb") as file_obj:
            if file_obj.read(2) != b"\xff\xd8":
                return None
            while True:
                marker_prefix = file_obj.read(1)
                if not marker_prefix or marker_prefix != b"\xff":
                    return None
                marker_byte = file_obj.read(1)
                while marker_byte == b"\xff":
                    marker_byte = file_obj.read(1)
                if not marker_byte:
                    return None
                marker = marker_byte[0]
                if marker in {0xD9, 0xDA}:
                    return None
                if marker == 0x01 or 0xD0 <= marker <= 0xD8:
                    continue
                length_bytes = file_obj.read(2)
                if len(length_bytes) != 2:
                    return None
                segment_length = int.from_bytes(length_bytes, "big")
                if segment_length < 2:
                    return None
                payload_length = segment_length - 2
                if marker == 0xE1:
                    payload = file_obj.read(payload_length)
                    if len(payload) != payload_length:
                        return None
                    if payload.startswith(XMP_JPEG_HEADER):
                        return payload
                else:
                    file_obj.seek(payload_length, os.SEEK_CUR)
    except (OSError, PermissionError):
        return None


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            shutil.copystat(path, name)
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
