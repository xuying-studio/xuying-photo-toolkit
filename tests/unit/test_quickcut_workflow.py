"""关键词快切应用编排测试。"""

from __future__ import annotations

from pathlib import Path

from xuying_toolbox.application.quickcut import QuickCutUseCase
from xuying_toolbox.domain.models.quickcut import (
    NormalizedRect,
    OCRCandidate,
    ProjectSettings,
    RecognitionState,
)
from xuying_toolbox.domain.ports.ocr import OCRResult
from xuying_toolbox.domain.ports.quickcut_export import QuickCutExportResult


class FakeOCR:
    available = True

    def __init__(self) -> None:
        self.calls = 0

    def recognize(self, image_path: Path, keyword: str) -> OCRResult:
        self.calls += 1
        if image_path.name == "bad.png":
            raise RuntimeError("损坏图片")
        if image_path.name == "empty.png":
            return OCRResult(100, 50, ())
        candidate = OCRCandidate(
            id="candidate",
            text=keyword,
            box=NormalizedRect(0.4, 0.4, 0.2, 0.1),
            confidence=0.9,
            is_exact_match=True,
            similarity=1,
        )
        return OCRResult(100, 50, (candidate,))


class FakeExporter:
    def export(self, sources, settings, destination, progress) -> QuickCutExportResult:
        return QuickCutExportResult(destination, (), len(sources) * settings.frames_per_image)


def test_recognition_keeps_per_image_failures_and_content_cache(tmp_path: Path) -> None:
    paths = [tmp_path / name for name in ("ok.png", "empty.png", "bad.png")]
    for path in paths:
        path.write_bytes(path.name.encode())
    ocr = FakeOCR()
    use_case = QuickCutUseCase(ocr, FakeExporter())
    items = use_case.new_items(paths)

    first = use_case.recognize(items, "AGI", lambda *_args: None)
    second = use_case.recognize(items, "AGI", lambda *_args: None)

    assert [item.state for item in first] == [
        RecognitionState.MATCHED,
        RecognitionState.NO_MATCH,
        RecognitionState.FAILED,
    ]
    assert first[0].selected_candidate is not None
    assert first[1].message == "没有识别到关键词，将按原图居中输出"
    assert ocr.calls == 4
    assert second[0].state is RecognitionState.MATCHED


def test_replacing_same_path_invalidates_ocr_cache(tmp_path: Path) -> None:
    path = tmp_path / "ok.png"
    path.write_bytes(b"first")
    ocr = FakeOCR()
    use_case = QuickCutUseCase(ocr, FakeExporter())
    items = use_case.new_items([path])
    use_case.recognize(items, "AGI", lambda *_args: None)

    path.write_bytes(b"second")
    use_case.recognize(items, "AGI", lambda *_args: None)

    assert ocr.calls == 2


def test_export_uses_selected_candidate_box(tmp_path: Path) -> None:
    path = tmp_path / "ok.png"
    path.write_bytes(b"fixture")
    use_case = QuickCutUseCase(FakeOCR(), FakeExporter())
    items = use_case.recognize(
        use_case.new_items([path]),
        "AGI",
        lambda *_args: None,
    )

    result = use_case.export(items, ProjectSettings(), tmp_path, lambda *_args: None)

    assert result.total_frames == 4
