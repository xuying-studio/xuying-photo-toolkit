"""Apple Vision 动态库的真实集成测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from xuying_toolbox.infrastructure.ocr.macos_vision import (
    MacVisionOCRAdapter,
    VisionBridgeError,
)


@pytest.mark.skipif(sys.platform != "darwin", reason="仅在 macOS 验证 Apple Vision")
def test_adapter_reports_missing_bridge(tmp_path: Path) -> None:
    adapter = MacVisionOCRAdapter(tmp_path / "missing.dylib")

    assert not adapter.available
    with pytest.raises(VisionBridgeError, match="找不到 Apple Vision 组件"):
        adapter.recognize(tmp_path / "image.png", "AGI")


@pytest.mark.skipif(sys.platform != "darwin", reason="仅在 macOS 验证 Apple Vision")
def test_vision_recognizes_stage0_fixture() -> None:
    adapter = MacVisionOCRAdapter()
    fixture = Path(__file__).parents[2] / "experiments/stage0_ocr/fixtures/03_mixed.png"

    assert adapter.available
    result = adapter.recognize(fixture, "Wedding 2026")

    assert (result.width, result.height) == (1000, 320)
    assert result.candidates
    assert result.candidates[0].is_exact_match
    assert result.candidates[0].box.y < 1
