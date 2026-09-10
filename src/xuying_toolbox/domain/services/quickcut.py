"""关键词快切的对齐与时间线算法。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from xuying_toolbox.domain.models.quickcut import AlignmentGeometry, NormalizedRect


def alignment_geometry(
    source_width: int,
    source_height: int,
    output_width: int,
    output_height: int,
    source_box: NormalizedRect | None,
    target_box: NormalizedRect,
) -> AlignmentGeometry:
    """计算把命中文字框移到目标框所需的等比缩放与偏移。"""

    if min(source_width, source_height, output_width, output_height) <= 0:
        raise ValueError("图片与画布尺寸必须大于零。")

    if source_box is None:
        scale = min(output_width / source_width, output_height / source_height)
        drawn_width = source_width * scale
        drawn_height = source_height * scale
        return AlignmentGeometry(
            scale=scale,
            origin_x=(output_width - drawn_width) / 2,
            origin_y=(output_height - drawn_height) / 2,
            drawn_width=drawn_width,
            drawn_height=drawn_height,
        )

    source = source_box.clamped()
    target = target_box.clamped()
    source_box_width = source.width * source_width
    target_box_width = target.width * output_width
    scale = target_box_width / source_box_width
    drawn_width = source_width * scale
    drawn_height = source_height * scale
    source_center_x = source.center_x * source_width * scale
    source_center_y = source.center_y * source_height * scale
    return AlignmentGeometry(
        scale=scale,
        origin_x=target.center_x * output_width - source_center_x,
        origin_y=target.center_y * output_height - source_center_y,
        drawn_width=drawn_width,
        drawn_height=drawn_height,
    )


def transformed_box(
    source_box: NormalizedRect,
    source_width: int,
    source_height: int,
    output_width: int,
    output_height: int,
    geometry: AlignmentGeometry,
) -> NormalizedRect:
    """把原图中的归一化框换算到输出画布。"""

    source = source_box.clamped()
    return NormalizedRect(
        x=(geometry.origin_x + source.x * source_width * geometry.scale) / output_width,
        y=(geometry.origin_y + source.y * source_height * geometry.scale) / output_height,
        width=source.width * source_width * geometry.scale / output_width,
        height=source.height * source_height * geometry.scale / output_height,
    )


def frame_rate_fraction(fps: float) -> Fraction:
    """保留常用 NTSC 小数帧率，其他帧率转为稳定有理数。"""

    for decimal, fraction in (
        (23.976, Fraction(24_000, 1_001)),
        (29.97, Fraction(30_000, 1_001)),
        (59.94, Fraction(60_000, 1_001)),
    ):
        if math.isclose(fps, decimal, rel_tol=0, abs_tol=1e-6):
            return fraction
    return Fraction(str(fps)).limit_denominator(100_000)


@dataclass(frozen=True, slots=True)
class Timeline:
    image_count: int
    frames_per_image: int
    fps: float

    def __post_init__(self) -> None:
        if self.image_count < 0:
            raise ValueError("图片数量不能小于零。")
        if not isinstance(self.frames_per_image, int) or not 1 <= self.frames_per_image <= 10_000:
            raise ValueError("每张保持帧数需要是 1–10000 的整数。")
        if not math.isfinite(self.fps) or not 1 <= self.fps <= 120:
            raise ValueError("帧率需要在 1–120fps 之间。")

    @property
    def total_frames(self) -> int:
        return self.image_count * self.frames_per_image

    @property
    def duration_seconds(self) -> float:
        return self.total_frames / self.fps

    @property
    def timecode(self) -> str:
        # 正数采用四舍五入，避免 Python 的银行家舍入影响毫秒显示。
        total_ms = math.floor(self.duration_seconds * 1_000 + 0.5)
        hours, remainder = divmod(total_ms, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, milliseconds = divmod(remainder, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    @property
    def summary(self) -> str:
        return f"约{self.duration_seconds:.2f}秒"
