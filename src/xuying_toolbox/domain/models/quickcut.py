"""关键词快切的纯领域模型。"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True, slots=True)
class NormalizedRect:
    """以左上角为原点、范围为 0–1 的矩形。"""

    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def clamped(self) -> NormalizedRect:
        values = (self.x, self.y, self.width, self.height)
        if not all(math.isfinite(value) for value in values):
            return DEFAULT_TARGET_RECT
        width = min(max(self.width, 0.01), 1.0)
        height = min(max(self.height, 0.01), 1.0)
        return NormalizedRect(
            x=min(max(self.x, 0.0), 1.0 - width),
            y=min(max(self.y, 0.0), 1.0 - height),
            width=width,
            height=height,
        )


@dataclass(frozen=True, slots=True)
class ResolutionPreset:
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.width} × {self.height}"


class AspectRatioPreset(StrEnum):
    PORTRAIT = "9:16"
    LANDSCAPE = "16:9"
    SQUARE = "1:1"
    SOCIAL_PORTRAIT = "4:5"
    CLASSIC_PORTRAIT = "3:4"
    CUSTOM = "自定义"

    @property
    def default_resolution(self) -> ResolutionPreset:
        return {
            AspectRatioPreset.PORTRAIT: ResolutionPreset(1080, 1920),
            AspectRatioPreset.LANDSCAPE: ResolutionPreset(1920, 1080),
            AspectRatioPreset.SQUARE: ResolutionPreset(1080, 1080),
            AspectRatioPreset.SOCIAL_PORTRAIT: ResolutionPreset(1080, 1350),
            AspectRatioPreset.CLASSIC_PORTRAIT: ResolutionPreset(1080, 1440),
            AspectRatioPreset.CUSTOM: ResolutionPreset(1080, 1920),
        }[self]


class ExportMode(StrEnum):
    ALIGNED_PNG = "处理后 PNG"
    FRAME_SEQUENCE = "逐帧 PNG"
    MP4 = "MP4"


class RecognitionState(StrEnum):
    WAITING = "待识别"
    RECOGNIZING = "识别中"
    MATCHED = "已匹配"
    FUZZY_MATCHED = "模糊匹配"
    NO_MATCH = "未识别"
    FAILED = "识别失败"


DEFAULT_TARGET_RECT = NormalizedRect(0.33, 0.475, 0.34, 0.05)


@dataclass(frozen=True, slots=True)
class OCRCandidate:
    id: str
    text: str
    box: NormalizedRect
    confidence: float
    is_exact_match: bool
    similarity: float


@dataclass(frozen=True, slots=True)
class QuickCutQueueItem:
    id: str
    path: Path
    state: RecognitionState = RecognitionState.WAITING
    width: int = 0
    height: int = 0
    candidates: tuple[OCRCandidate, ...] = ()
    selected_candidate_id: str | None = None
    message: str = ""

    @property
    def selected_candidate(self) -> OCRCandidate | None:
        if self.selected_candidate_id is None:
            return None
        return next(
            (
                candidate
                for candidate in self.candidates
                if candidate.id == self.selected_candidate_id
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class AlignmentGeometry:
    scale: float
    origin_x: float
    origin_y: float
    drawn_width: float
    drawn_height: float


@dataclass(slots=True)
class ProjectSettings:
    aspect_ratio: AspectRatioPreset = AspectRatioPreset.PORTRAIT
    keyword: str = ""
    width: int = 1080
    height: int = 1920
    frame_rate: float = 30.0
    frames_per_image: int = 4
    target_rect: NormalizedRect = field(default_factory=lambda: DEFAULT_TARGET_RECT)
    export_mode: ExportMode = ExportMode.MP4

    @property
    def validation_message(self) -> str | None:
        if not (64 <= self.width <= 8192 and 64 <= self.height <= 8192):
            return "画面宽高需要在 64–8192 像素之间。"
        if self.width % 2 or self.height % 2:
            return "画面宽高必须是偶数。"
        if not math.isfinite(self.frame_rate) or not 1 <= self.frame_rate <= 120:
            return "帧率需要在 1–120fps 之间。"
        if not isinstance(self.frames_per_image, int) or not 1 <= self.frames_per_image <= 10_000:
            return "每张保持帧数需要是 1–10000 的整数。"
        return None
