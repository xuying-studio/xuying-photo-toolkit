"""v1.4.0 关键词快切纯算法的脱敏等价测试。"""

from __future__ import annotations

from fractions import Fraction

import pytest

from xuying_toolbox.domain.models.quickcut import (
    AspectRatioPreset,
    NormalizedRect,
    OCRCandidate,
    ProjectSettings,
)
from xuying_toolbox.domain.services.quickcut import (
    Timeline,
    alignment_geometry,
    frame_rate_fraction,
    transformed_box,
)
from xuying_toolbox.domain.services.text_matching import (
    best_fuzzy_span,
    deduplicate_and_rank,
    exact_match_span,
    is_accepted_similarity,
    normalized_characters,
)


def test_normalized_rect_clamps_position_and_minimum_size() -> None:
    assert NormalizedRect(-1, 2, 0, 4).clamped() == NormalizedRect(0, 0, 0.01, 1)
    assert NormalizedRect(0.95, 0.95, 0.2, 0.2).clamped() == NormalizedRect(
        0.8,
        0.8,
        0.2,
        0.2,
    )


def test_matched_keyword_aligns_to_target_center_and_width() -> None:
    source = NormalizedRect(0.4, 0.3, 0.2, 0.05)
    target = NormalizedRect(0.25, 0.45, 0.5, 0.08)
    geometry = alignment_geometry(1080, 1920, 1080, 1920, source, target)
    transformed = transformed_box(source, 1080, 1920, 1080, 1920, geometry)

    assert transformed.center_x == pytest.approx(target.center_x)
    assert transformed.center_y == pytest.approx(target.center_y)
    assert transformed.width == pytest.approx(target.width)


def test_missing_keyword_uses_aspect_fit() -> None:
    geometry = alignment_geometry(
        1000,
        1000,
        1080,
        1920,
        None,
        NormalizedRect(0.25, 0.45, 0.5, 0.08),
    )

    assert geometry.drawn_width == pytest.approx(1080)
    assert geometry.drawn_height == pytest.approx(1080)
    assert geometry.origin_y == pytest.approx(420)


def test_text_matching_ignores_spacing_punctuation_and_case() -> None:
    assert normalized_characters(" Wedding·婚礼 2026 ") == tuple("wedding婚礼2026")
    assert exact_match_span("今日关键词：幸 福定格", "幸福定格") is not None
    assert exact_match_span("AGI Wedding", "agi") == (0, 3)


def test_fuzzy_matching_and_threshold_boundary() -> None:
    span = best_fuzzy_span("abcXXXghij", "abcdefghij")

    assert span is not None
    assert span.similarity == pytest.approx(0.7)
    assert is_accepted_similarity(0.70)
    assert not is_accepted_similarity(0.699999)


def test_exact_candidates_win_then_rank_nearest_center_and_deduplicate() -> None:
    far = OCRCandidate(
        id="far",
        text="AGI",
        box=NormalizedRect(0.05, 0.05, 0.1, 0.05),
        confidence=0.9,
        is_exact_match=True,
        similarity=1,
    )
    near = OCRCandidate(
        id="near",
        text="AGI",
        box=NormalizedRect(0.45, 0.475, 0.1, 0.05),
        confidence=0.8,
        is_exact_match=True,
        similarity=1,
    )
    duplicate = OCRCandidate(
        id="duplicate",
        text="AGI",
        box=NormalizedRect(0.4501, 0.4751, 0.1, 0.05),
        confidence=0.7,
        is_exact_match=True,
        similarity=1,
    )
    fuzzy = OCRCandidate(
        id="fuzzy",
        text="A6I",
        box=NormalizedRect(0.49, 0.49, 0.1, 0.05),
        confidence=0.99,
        is_exact_match=False,
        similarity=0.8,
    )

    ranked = deduplicate_and_rank([far, duplicate, fuzzy, near])

    assert [candidate.id for candidate in ranked] == ["near", "far"]


def test_all_aspect_ratio_presets_and_default_resolutions() -> None:
    assert [preset.value for preset in AspectRatioPreset] == [
        "9:16",
        "16:9",
        "1:1",
        "4:5",
        "3:4",
        "自定义",
    ]
    assert AspectRatioPreset.PORTRAIT.default_resolution.label == "1080 × 1920"
    assert AspectRatioPreset.LANDSCAPE.default_resolution.label == "1920 × 1080"
    assert AspectRatioPreset.SQUARE.default_resolution.label == "1080 × 1080"
    assert AspectRatioPreset.SOCIAL_PORTRAIT.default_resolution.label == "1080 × 1350"
    assert AspectRatioPreset.CLASSIC_PORTRAIT.default_resolution.label == "1080 × 1440"


def test_project_settings_reject_invalid_video_values() -> None:
    assert ProjectSettings().validation_message is None
    assert ProjectSettings(width=1079).validation_message == "画面宽高必须是偶数。"
    assert ProjectSettings(frame_rate=0).validation_message == "帧率需要在 1–120fps 之间。"
    assert ProjectSettings(frames_per_image=10_001).validation_message == (
        "每张保持帧数需要是 1–10000 的整数。"
    )


def test_timeline_preserves_fractional_frame_rates_and_rounds_timecode() -> None:
    timeline = Timeline(image_count=26, frames_per_image=4, fps=30)
    fractional = Timeline(image_count=10, frames_per_image=3, fps=29.97)

    assert timeline.total_frames == 104
    assert timeline.duration_seconds == pytest.approx(104 / 30)
    assert timeline.timecode == "00:00:03.467"
    assert timeline.summary == "约3.47秒"
    assert fractional.duration_seconds == pytest.approx(30 / 29.97)
    assert frame_rate_fraction(23.976) == Fraction(24_000, 1_001)
    assert frame_rate_fraction(29.97) == Fraction(30_000, 1_001)
    assert frame_rate_fraction(59.94) == Fraction(60_000, 1_001)


@pytest.mark.parametrize(
    ("image_count", "frames_per_image", "fps"),
    [(-1, 4, 30), (1, 0, 30), (1, 10_001, 30), (1, 4, 0), (1, 4, 120.01)],
)
def test_timeline_rejects_invalid_values(
    image_count: int,
    frames_per_image: int,
    fps: float,
) -> None:
    with pytest.raises(ValueError):
        Timeline(image_count, frames_per_image, fps)
