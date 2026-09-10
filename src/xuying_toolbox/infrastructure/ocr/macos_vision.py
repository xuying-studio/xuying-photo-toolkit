"""通过轻量 C ABI 调用 Apple Vision 的 macOS OCR 适配器。"""

from __future__ import annotations

import ctypes
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from xuying_toolbox.domain.models.quickcut import NormalizedRect, OCRCandidate
from xuying_toolbox.domain.ports.ocr import OCRResult
from xuying_toolbox.domain.services.text_matching import (
    best_fuzzy_span,
    deduplicate_and_rank,
    exact_match_span,
)


class VisionBridgeError(RuntimeError):
    """Apple Vision 桥不可用或识别失败。"""


def default_bridge_candidates() -> tuple[Path, ...]:
    configured = os.environ.get("XUYING_VISION_BRIDGE")
    bundle_root = getattr(sys, "_MEIPASS", None)
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    if bundle_root:
        candidates.append(Path(cast(str, bundle_root)) / "native/libXuyingVision.dylib")
    candidates.append(
        Path(__file__).resolve().parents[4] / "build/native/libXuyingVision.dylib"
    )
    return tuple(candidate.resolve() for candidate in candidates)


class MacVisionOCRAdapter:
    def __init__(self, library_path: Path | None = None) -> None:
        self._library_path = library_path or next(
            (path for path in default_bridge_candidates() if path.is_file()),
            default_bridge_candidates()[0],
        )
        self._library: ctypes.CDLL | None = None

    @property
    def available(self) -> bool:
        return sys.platform == "darwin" and self._library_path.is_file()

    def _load(self) -> ctypes.CDLL:
        if sys.platform != "darwin":
            raise VisionBridgeError("Apple Vision 仅在 macOS 上可用。")
        if not self._library_path.is_file():
            raise VisionBridgeError(f"找不到 Apple Vision 组件：{self._library_path}")
        if self._library is None:
            library = ctypes.CDLL(str(self._library_path))
            library.XUQuickCutRecognize.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            library.XUQuickCutRecognize.restype = ctypes.c_void_p
            library.XUQuickCutFreeString.argtypes = [ctypes.c_void_p]
            library.XUQuickCutFreeString.restype = None
            self._library = library
        return self._library

    def recognize(self, image_path: Path, keyword: str) -> OCRResult:
        library = self._load()
        pointer = library.XUQuickCutRecognize(
            os.fsencode(image_path),
            keyword.encode("utf-8"),
        )
        if not pointer:
            raise VisionBridgeError("Apple Vision 没有返回结果。")
        try:
            payload = json.loads(ctypes.string_at(pointer).decode("utf-8"))
        finally:
            library.XUQuickCutFreeString(pointer)
        if not payload.get("ok"):
            raise VisionBridgeError(str(payload.get("error") or "Apple Vision 识别失败。"))

        candidates: list[OCRCandidate] = []
        for index, observation in enumerate(payload.get("observations", [])):
            candidate = self._candidate_from_observation(index, observation, keyword)
            if candidate is not None:
                candidates.append(candidate)
        return OCRResult(
            width=int(payload["width"]),
            height=int(payload["height"]),
            candidates=tuple(deduplicate_and_rank(candidates)),
        )

    @staticmethod
    def _candidate_from_observation(
        index: int,
        observation: dict[str, Any],
        keyword: str,
    ) -> OCRCandidate | None:
        text = str(observation.get("text", ""))
        exact_span = exact_match_span(text, keyword)
        fuzzy_span = None if exact_span else best_fuzzy_span(text, keyword)
        if exact_span is None and (fuzzy_span is None or fuzzy_span.similarity < 0.70):
            return None

        raw_box = observation.get("match_box") if exact_span else observation.get("box")
        if not isinstance(raw_box, dict):
            raw_box = observation.get("box")
        if not isinstance(raw_box, dict):
            return None
        box = NormalizedRect(
            float(raw_box.get("x", 0)),
            float(raw_box.get("y", 0)),
            float(raw_box.get("width", 0)),
            float(raw_box.get("height", 0)),
        ).clamped()
        return OCRCandidate(
            id=f"vision-{index}",
            text=text,
            box=box,
            confidence=float(observation.get("confidence", 0)),
            is_exact_match=exact_span is not None,
            similarity=1.0 if exact_span else fuzzy_span.similarity,
        )
