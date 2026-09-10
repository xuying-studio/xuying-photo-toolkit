"""Windows 阶段 0 OCR 基准；后端失败时仍写出结构化 JSON。"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import statistics
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

from PIL import Image

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}


def normalized(text: str) -> str:
    return "".join(character.casefold() for character in text if character.isalnum())


def match_span(text: str, keyword: str) -> tuple[int, int] | None:
    source = normalized(text)
    target = normalized(keyword)
    start = source.find(target)
    return (start, len(target)) if target and start >= 0 else None


def center_distance(box: dict[str, float]) -> float:
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    return ((center_x - 0.5) ** 2 + (center_y - 0.5) ** 2) ** 0.5


def pixel_box(
    x: float,
    y: float,
    width: float,
    height: float,
    image_size: tuple[int, int],
) -> dict[str, float]:
    image_width, image_height = image_size
    return {
        "x": round(x / image_width, 6),
        "y": round(y / image_height, 6),
        "width": round(width / image_width, 6),
        "height": round(height / image_height, 6),
    }


def rapid_line_box(points: Any, image_size: tuple[int, int]) -> dict[str, float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return pixel_box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys), image_size)


def rapid_keyword_box(
    line_box: dict[str, float],
    text: str,
    span: tuple[int, int],
) -> dict[str, float]:
    source_length = max(len(normalized(text)), 1)
    start, length = span
    # RapidOCR 返回整行框；横排文字按字符比例估算关键词子框。
    return {
        "x": round(line_box["x"] + line_box["width"] * start / source_length, 6),
        "y": line_box["y"],
        "width": round(line_box["width"] * length / source_length, 6),
        "height": line_box["height"],
    }


def base_case(path: Path) -> tuple[dict[str, Any], tuple[int, int]]:
    with Image.open(path) as image:
        size = image.size
    return (
        {
            "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "width": size[0],
            "height": size[1],
        },
        size,
    )


def run_rapidocr(files: list[Path], keyword: str) -> dict[str, Any]:
    from rapidocr import RapidOCR

    init_started = time.perf_counter()
    engine = RapidOCR()
    init_ms = (time.perf_counter() - init_started) * 1000
    cases: list[dict[str, Any]] = []

    for path in files:
        item, size = base_case(path)
        try:
            started = time.perf_counter()
            output = engine(str(path))
            elapsed_ms = (time.perf_counter() - started) * 1000
            lines: list[dict[str, Any]] = []
            candidates: list[dict[str, Any]] = []
            boxes = output.boxes if output.boxes is not None else []
            texts = output.txts if output.txts is not None else []
            scores = output.scores if output.scores is not None else []
            for points, text, score in zip(boxes, texts, scores, strict=True):
                line_box = rapid_line_box(points, size)
                lines.append(
                    {
                        "text": text,
                        "confidence": round(float(score), 6),
                        "box": line_box,
                    }
                )
                span = match_span(text, keyword)
                if span:
                    box = rapid_keyword_box(line_box, text, span)
                    candidates.append(
                        {
                            "text": keyword,
                            "source_text": text,
                            "confidence": round(float(score), 6),
                            "box": box,
                            "box_method": "proportional-line-estimate",
                            "center_distance": round(center_distance(box), 6),
                        }
                    )
            candidates.sort(key=lambda candidate: candidate["center_distance"])
            item.update(
                {
                    "status": "passed",
                    "elapsed_ms": round(elapsed_ms, 2),
                    "keyword_found": bool(candidates),
                    "selected_candidate": candidates[0] if candidates else None,
                    "candidates": candidates,
                    "recognized_lines": lines,
                }
            )
        # 单张图片失败必须进入结果，不能中断剩余 20 张。
        except Exception as exc:  # noqa: BLE001
            item.update(
                {
                    "status": "failed",
                    "keyword_found": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        cases.append(item)

    elapsed = [float(case["elapsed_ms"]) for case in cases if case.get("status") == "passed"]
    return {
        "status": "passed"
        if cases and all(case["status"] == "passed" for case in cases)
        else "partial",
        "engine": "RapidOCR",
        "version": version("rapidocr"),
        "init_ms": round(init_ms, 2),
        "average_image_ms": round(statistics.mean(elapsed), 2) if elapsed else None,
        "source_count": len(cases),
        "found_count": sum(bool(case.get("keyword_found")) for case in cases),
        "cases": cases,
    }


async def read_windows_bitmap(path: Path) -> Any:
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(path.read_bytes())
    await writer.store_async()
    writer.detach_stream()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    return await decoder.get_software_bitmap_async()


async def run_windows_media_ocr(files: list[Path], keyword: str) -> dict[str, Any]:
    from winrt.windows.globalization import Language
    from winrt.windows.media.ocr import OcrEngine

    init_started = time.perf_counter()
    engine = OcrEngine.try_create_from_language(Language("zh-Hans-CN"))
    init_ms = (time.perf_counter() - init_started) * 1000
    if engine is None:
        available = [language.language_tag for language in OcrEngine.available_recognizer_languages]
        raise RuntimeError(f"简体中文 OCR 语言包不可用；当前语言：{available}")

    cases: list[dict[str, Any]] = []
    for path in files:
        item, size = base_case(path)
        try:
            started = time.perf_counter()
            bitmap = await read_windows_bitmap(path)
            output = await engine.recognize_async(bitmap)
            elapsed_ms = (time.perf_counter() - started) * 1000
            lines: list[dict[str, Any]] = []
            candidates: list[dict[str, Any]] = []
            for line in output.lines:
                words: list[dict[str, Any]] = []
                for word in line.words:
                    rect = word.bounding_rect
                    box = pixel_box(rect.x, rect.y, rect.width, rect.height, size)
                    words.append({"text": word.text, "box": box})
                    if match_span(word.text, keyword):
                        candidates.append(
                            {
                                "text": keyword,
                                "source_text": word.text,
                                "confidence": None,
                                "box": box,
                                "box_method": "windows-word-box",
                                "center_distance": round(center_distance(box), 6),
                            }
                        )
                lines.append({"text": line.text, "words": words})
            candidates.sort(key=lambda candidate: candidate["center_distance"])
            item.update(
                {
                    "status": "passed",
                    "elapsed_ms": round(elapsed_ms, 2),
                    "keyword_found": bool(candidates),
                    "selected_candidate": candidates[0] if candidates else None,
                    "candidates": candidates,
                    "recognized_lines": lines,
                }
            )
        # 单张图片失败必须进入结果，不能中断剩余 20 张。
        except Exception as exc:  # noqa: BLE001
            item.update(
                {
                    "status": "failed",
                    "keyword_found": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        cases.append(item)

    elapsed = [float(case["elapsed_ms"]) for case in cases if case.get("status") == "passed"]
    return {
        "status": "passed"
        if cases and all(case["status"] == "passed" for case in cases)
        else "partial",
        "engine": "Windows.Media.Ocr",
        "version": version("winrt-Windows.Media.Ocr"),
        "init_ms": round(init_ms, 2),
        "average_image_ms": round(statistics.mean(elapsed), 2) if elapsed else None,
        "source_count": len(cases),
        "found_count": sum(bool(case.get("keyword_found")) for case in cases),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, choices=["rapidocr", "windows_media_ocr"])
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--keyword", default="AGI")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    files = sorted(
        path
        for path in args.input_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in ALLOWED_EXTENSIONS
    )

    report: dict[str, Any] = {
        "status": "failed",
        "engine": args.backend,
        "scope": "user-authorized-real-screenshots",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "keyword": args.keyword,
        "coordinate_convention": "top-left normalized",
        "source_count": len(files),
    }
    try:
        if not files:
            raise RuntimeError("input/real 中没有支持的图片。")
        if args.backend == "rapidocr":
            result = run_rapidocr(files, args.keyword)
        else:
            result = asyncio.run(run_windows_media_ocr(files, args.keyword))
        report.update(result)
    # 后端初始化失败也要落盘，供 Mac 端判断语言包或包身份问题。
    except Exception as exc:  # noqa: BLE001
        report["error"] = f"{type(exc).__name__}: {exc}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
