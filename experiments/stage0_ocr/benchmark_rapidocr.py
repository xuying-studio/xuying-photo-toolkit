"""在统一脱敏夹具上记录 RapidOCR 的识别结果与耗时。"""

from __future__ import annotations

import json
import platform
import re
import statistics
import time
from difflib import SequenceMatcher
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).casefold()


def main() -> None:
    import_start = time.perf_counter()
    from rapidocr import RapidOCR

    import_ms = (time.perf_counter() - import_start) * 1000
    init_start = time.perf_counter()
    engine = RapidOCR()
    init_ms = (time.perf_counter() - init_start) * 1000

    cases = json.loads((ROOT / "expected.json").read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for case in cases:
        started = time.perf_counter()
        result = engine(str(ROOT / "fixtures" / case["file"]))
        elapsed_ms = (time.perf_counter() - started) * 1000
        texts = list(result.txts or [])
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
        "engine": "RapidOCR",
        "version": version("rapidocr"),
        "scope": "synthetic-fixtures",
        "not_windows": platform.system() != "Windows",
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
    main()
