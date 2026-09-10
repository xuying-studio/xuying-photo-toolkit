"""在 Windows 上用同一夹具验证 Windows.Media.Ocr。"""

from __future__ import annotations

import asyncio
import json
import platform
import re
import statistics
import time
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).casefold()


async def recognize(path: Path, engine: object) -> list[str]:
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(path.read_bytes())
    await writer.store_async()
    writer.detach_stream()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    result = await engine.recognize_async(bitmap)
    return [line.text for line in result.lines]


async def async_main() -> None:
    import_start = time.perf_counter()
    from winrt.windows.globalization import Language
    from winrt.windows.media.ocr import OcrEngine

    import_ms = (time.perf_counter() - import_start) * 1000
    init_start = time.perf_counter()
    engine = OcrEngine.try_create_from_language(Language("zh-Hans-CN"))
    init_ms = (time.perf_counter() - init_start) * 1000
    if engine is None:
        available = [item.language_tag for item in OcrEngine.available_recognizer_languages]
        raise RuntimeError(f"简体中文 OCR 语言包不可用；当前可用语言：{available}")

    cases = json.loads((ROOT / "expected.json").read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for case in cases:
        started = time.perf_counter()
        texts = await recognize(ROOT / "fixtures" / case["file"], engine)
        elapsed_ms = (time.perf_counter() - started) * 1000
        joined = " ".join(texts)
        score = SequenceMatcher(None, normalize(case["expected"]), normalize(joined)).ratio()
        rows.append(
            {
                "file": case["file"],
                "expected": case["expected"],
                "recognized": texts,
                "similarity": round(score, 4),
                "elapsed_ms": round(elapsed_ms, 2),
            }
        )

    report = {
        "engine": "Windows.Media.Ocr",
        "scope": "synthetic-fixtures",
        "not_windows": False,
        "not_real_screenshots": True,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "import_ms": round(import_ms, 2),
        "init_ms": round(init_ms, 2),
        "average_image_ms": round(statistics.mean(row["elapsed_ms"] for row in rows), 2),
        "average_similarity": round(statistics.mean(row["similarity"] for row in rows), 4),
        "cases": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if platform.system() != "Windows":
        raise SystemExit("此验证脚本只能在 Windows 10/11 上运行。")
    asyncio.run(async_main())
