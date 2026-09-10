"""关键词快切识别与导出的应用编排。"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from xuying_toolbox.application.quickcut.input_queue import (
    InputQueueResult,
    QuickCutInputQueueUseCase,
)
from xuying_toolbox.domain.models.quickcut import (
    ProjectSettings,
    QuickCutQueueItem,
    RecognitionState,
)
from xuying_toolbox.domain.ports.ocr import OCRProvider, OCRResult
from xuying_toolbox.domain.ports.quickcut_export import (
    QuickCutExportProvider,
    QuickCutExportResult,
    QuickCutExportSource,
)
from xuying_toolbox.domain.ports.quickcut_input import QuickCutInputExpander
from xuying_toolbox.domain.services.progress import ProgressCallback


class QuickCutUseCase:
    def __init__(
        self,
        ocr: OCRProvider,
        exporter: QuickCutExportProvider,
        input_expander: QuickCutInputExpander | None = None,
    ) -> None:
        self._ocr = ocr
        self._exporter = exporter
        self._input_queue = (
            QuickCutInputQueueUseCase(input_expander) if input_expander is not None else None
        )
        self._ocr_cache: dict[tuple[str, str], OCRResult] = {}

    @property
    def ocr_available(self) -> bool:
        return self._ocr.available

    def new_items(self, paths: list[Path]) -> tuple[QuickCutQueueItem, ...]:
        return tuple(
            QuickCutQueueItem(id=str(uuid4()), path=path)
            for path in paths
        )

    def add_inputs(
        self,
        inputs: list[Path],
        existing: tuple[Path, ...] = (),
    ) -> InputQueueResult:
        if self._input_queue is None:
            raise RuntimeError("未配置图片输入适配器。")
        return self._input_queue.add(inputs, existing)

    def recognize(
        self,
        items: tuple[QuickCutQueueItem, ...],
        keyword: str,
        progress: ProgressCallback,
    ) -> tuple[QuickCutQueueItem, ...]:
        keyword = keyword.strip()
        if not keyword:
            raise ValueError("请输入要锁定的关键词。")
        if not items:
            raise ValueError("请先导入图片。")

        results: list[QuickCutQueueItem] = []
        for index, item in enumerate(items):
            progress(index, len(items), f"正在识别 {index + 1}/{len(items)}：{item.path.name}")
            try:
                cache_key = (self._content_fingerprint(item.path), keyword.casefold())
                result = self._ocr_cache.get(cache_key)
                if result is None:
                    result = self._ocr.recognize(item.path, keyword)
                    self._ocr_cache[cache_key] = result
                first = result.candidates[0] if result.candidates else None
                if first is None:
                    state = RecognitionState.NO_MATCH
                    message = "没有识别到关键词，将按原图居中输出"
                elif first.is_exact_match:
                    state = RecognitionState.MATCHED
                    message = ""
                else:
                    state = RecognitionState.FUZZY_MATCHED
                    message = "未找到完全一致文字，已使用最接近结果"
                results.append(
                    replace(
                        item,
                        state=state,
                        width=result.width,
                        height=result.height,
                        candidates=result.candidates,
                        selected_candidate_id=first.id if first else None,
                        message=message,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    replace(
                        item,
                        state=RecognitionState.FAILED,
                        candidates=(),
                        selected_candidate_id=None,
                        message=str(exc) or "识别失败。",
                    )
                )
        progress(len(items), len(items), "识别完成")
        return tuple(results)

    def export(
        self,
        items: tuple[QuickCutQueueItem, ...],
        settings: ProjectSettings,
        destination: Path,
        progress: ProgressCallback,
    ) -> QuickCutExportResult:
        sources = tuple(
            QuickCutExportSource(
                path=item.path,
                source_box=item.selected_candidate.box if item.selected_candidate else None,
            )
            for item in items
        )
        return self._exporter.export(sources, settings, destination, progress)

    @staticmethod
    def select_candidate(item: QuickCutQueueItem, candidate_id: str) -> QuickCutQueueItem:
        candidate = next(
            (candidate for candidate in item.candidates if candidate.id == candidate_id),
            None,
        )
        if candidate is None:
            return item
        state = (
            RecognitionState.MATCHED
            if candidate.is_exact_match
            else RecognitionState.FUZZY_MATCHED
        )
        return replace(item, selected_candidate_id=candidate.id, state=state)

    @staticmethod
    def _content_fingerprint(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
