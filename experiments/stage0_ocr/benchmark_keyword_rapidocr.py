"""在真实截图目录上记录 RapidOCR 的关键词检测结果。"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import time
from importlib.metadata import version
from pathlib import Path

from PIL import Image
from rapidocr import RapidOCR


def normalized(text: str) -> str:
    return "".join(character.casefold() for character in text if character.isalnum())


def normalized_match(text: str, keyword: str) -> tuple[int, int] | None:
    source = normalized(text)
    target = normalized(keyword)
    start = source.find(target)
    return (start, len(target)) if target and start >= 0 else None


def normalized_box(points: object, width: int, height: int) -> dict[str, float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return {
        "x": round(min(xs) / width, 6),
        "y": round(min(ys) / height, 6),
        "width": round((max(xs) - min(xs)) / width, 6),
        "height": round((max(ys) - min(ys)) / height, 6),
    }


def keyword_box(line_box: dict[str, float], text: str, match: tuple[int, int]) -> dict[str, float]:
    source_length = max(len(normalized(text)), 1)
    start, length = match
    # RapidOCR 返回整行框；横排文字按字符比例估算关键词子框，供后端横向比较。
    return {
        "x": round(line_box["x"] + line_box["width"] * start / source_length, 6),
        "y": line_box["y"],
        "width": round(line_box["width"] * length / source_length, 6),
        "height": line_box["height"],
    }


def center_distance(box: dict[str, float]) -> float:
    center_x = box["x"] + box["width"] / 2
    center_y = box["y"] + box["height"] / 2
    return ((center_x - 0.5) ** 2 + (center_y - 0.5) ** 2) ** 0.5


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--keyword", default="AGI")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    files = sorted(
        path
        for path in args.input_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in {".jpg", ".jpeg", ".png", ".heic"}
    )
    init_started = time.perf_counter()
    engine = RapidOCR()
    init_ms = (time.perf_counter() - init_started) * 1000
    cases: list[dict[str, object]] = []

    for path in files:
        with Image.open(path) as image:
            image_width, image_height = image.size
        started = time.perf_counter()
        result = engine(str(path))
        elapsed_ms = (time.perf_counter() - started) * 1000
        lines: list[dict[str, object]] = []
        candidates: list[dict[str, object]] = []
        boxes = result.boxes if result.boxes is not None else []
        texts = result.txts if result.txts is not None else []
        scores = result.scores if result.scores is not None else []
        for points, text, score in zip(boxes, texts, scores, strict=True):
            line_box = normalized_box(points, image_width, image_height)
            lines.append({"text": text, "confidence": round(float(score), 6), "box": line_box})
            match = normalized_match(text, args.keyword)
            if match:
                box = keyword_box(line_box, text, match)
                candidates.append(
                    {
                        "text": args.keyword,
                        "source_text": text,
                        "confidence": round(float(score), 6),
                        "box": box,
                        "box_method": "proportional-line-estimate",
                        "center_distance": round(center_distance(box), 6),
                    }
                )
        candidates.sort(key=lambda item: item["center_distance"])
        cases.append(
            {
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "width": image_width,
                "height": image_height,
                "elapsed_ms": round(elapsed_ms, 2),
                "keyword_found": bool(candidates),
                "selected_candidate": candidates[0] if candidates else None,
                "candidates": candidates,
                "recognized_lines": lines,
            }
        )

    elapsed_values = [float(case["elapsed_ms"]) for case in cases]
    report = {
        "engine": "RapidOCR",
        "version": version("rapidocr"),
        "scope": "user-authorized-real-screenshots",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "keyword": args.keyword,
        "coordinate_convention": "top-left normalized",
        "source_count": len(cases),
        "found_count": sum(bool(case["keyword_found"]) for case in cases),
        "init_ms": round(init_ms, 2),
        "average_image_ms": round(statistics.mean(elapsed_values), 2) if elapsed_values else None,
        "cases": cases,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
