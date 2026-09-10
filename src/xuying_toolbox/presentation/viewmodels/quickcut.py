"""关键词快切的 Qt 状态、后台任务与 QML 交互边界。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from xuying_toolbox.application.quickcut import QuickCutUseCase
from xuying_toolbox.domain.models.quickcut import (
    DEFAULT_TARGET_RECT,
    AspectRatioPreset,
    ExportMode,
    NormalizedRect,
    QuickCutQueueItem,
)
from xuying_toolbox.domain.services.quickcut import alignment_geometry, transformed_box
from xuying_toolbox.infrastructure.imaging.quickcut_renderer import (
    ImageRenderError,
    QtQuickCutRenderer,
)
from xuying_toolbox.infrastructure.persistence.quickcut_settings import (
    JsonQuickCutSettingsStore,
)
from xuying_toolbox.presentation.models.quickcut_items import QuickCutItemsModel
from xuying_toolbox.presentation.quickcut_preview import QuickCutPreviewProvider
from xuying_toolbox.presentation.task_runner import TaskRunner


class QuickCutViewModel(QObject):
    stateChanged = Signal()
    notificationRequested = Signal(str, str)
    actionCompleted = Signal(str, int)

    def __init__(
        self,
        use_case: QuickCutUseCase,
        settings_store: JsonQuickCutSettingsStore,
        preview_provider: QuickCutPreviewProvider,
        renderer: QtQuickCutRenderer,
        parent: QObject | None = None,
        *,
        task_runner: TaskRunner | None = None,
    ) -> None:
        super().__init__(parent)
        self._use_case = use_case
        self._settings_store = settings_store
        self._preview_provider = preview_provider
        self._renderer = renderer
        self._runner = task_runner or TaskRunner(self)
        self._model = QuickCutItemsModel(self)
        self._settings = settings_store.load()
        # 旧验收样例可能遗留 AGI，不再将它当作用户的默认关键词。
        if self._settings.keyword.strip().casefold() == "agi":
            self._settings.keyword = ""
        self._items: tuple[QuickCutQueueItem, ...] = ()
        self._selected_index = -1
        self._phase = "idle"
        self._status_text = "请先导入关键词截图"
        self._progress_current = 0
        self._progress_total = 0
        self._preview_revision = 0
        self._active_action = ""

        self._runner.progress.connect(self._on_progress)
        self._runner.succeeded.connect(self._on_succeeded)
        self._runner.failed.connect(self._on_failed)
        self._runner.cancelled.connect(self._on_cancelled)
        self._runner.finished.connect(self._on_finished)

    @Property(QObject, constant=True)
    def itemsModel(self) -> QObject:
        return self._model

    @Property(int, notify=stateChanged)
    def itemCount(self) -> int:
        return len(self._items)

    @Property(int, notify=stateChanged)
    def selectedIndex(self) -> int:
        return self._selected_index

    @Property(str, notify=stateChanged)
    def phase(self) -> str:
        return self._phase

    @Property(str, notify=stateChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._runner.running

    @Property(float, notify=stateChanged)
    def progressValue(self) -> float:
        return self._progress_current / self._progress_total if self._progress_total else 0.0

    @Property(str, notify=stateChanged)
    def keyword(self) -> str:
        return self._settings.keyword

    @Property(int, notify=stateChanged)
    def aspectRatioIndex(self) -> int:
        return list(AspectRatioPreset).index(self._settings.aspect_ratio)

    @Property(int, notify=stateChanged)
    def outputWidth(self) -> int:
        return self._settings.width

    @Property(int, notify=stateChanged)
    def outputHeight(self) -> int:
        return self._settings.height

    @Property(float, notify=stateChanged)
    def frameRate(self) -> float:
        return self._settings.frame_rate

    @Property(int, notify=stateChanged)
    def framesPerImage(self) -> int:
        return self._settings.frames_per_image

    @Property(int, notify=stateChanged)
    def exportModeIndex(self) -> int:
        return list(ExportMode).index(self._settings.export_mode)

    @Property(float, notify=stateChanged)
    def targetX(self) -> float:
        return self._settings.target_rect.x

    @Property(float, notify=stateChanged)
    def targetY(self) -> float:
        return self._settings.target_rect.y

    @Property(float, notify=stateChanged)
    def targetWidth(self) -> float:
        return self._settings.target_rect.width

    @Property(float, notify=stateChanged)
    def targetHeight(self) -> float:
        return self._settings.target_rect.height

    @Property(str, notify=stateChanged)
    def previewUrl(self) -> str:
        return f"image://quickcut-preview/current?revision={self._preview_revision}"

    @Property("QStringList", notify=stateChanged)
    def candidateLabels(self) -> list[str]:
        item = self._selected_item()
        if item is None:
            return []
        return [
            f"{index + 1} · {'精确' if candidate.is_exact_match else '接近'} · "
            f"{candidate.confidence:.0%} · {candidate.text}"
            for index, candidate in enumerate(item.candidates)
        ]

    @Property(int, notify=stateChanged)
    def selectedCandidateIndex(self) -> int:
        item = self._selected_item()
        if item is None or item.selected_candidate_id is None:
            return -1
        return next(
            (
                index
                for index, candidate in enumerate(item.candidates)
                if candidate.id == item.selected_candidate_id
            ),
            -1,
        )

    @Property(bool, notify=stateChanged)
    def canRecognize(self) -> bool:
        ready = self._items and self._settings.keyword.strip() and self._use_case.ocr_available
        return bool(ready) and not self.busy

    @Property(bool, notify=stateChanged)
    def canExport(self) -> bool:
        return bool(self._items and self._settings.keyword.strip()) and not self.busy

    @Slot("QVariantList")
    def addFileUrls(self, values: list[Any]) -> None:
        urls = [value if isinstance(value, QUrl) else QUrl(str(value)) for value in values]
        self._add_paths([Path(url.toLocalFile()) for url in urls if url.isLocalFile()])

    @Slot(QUrl)
    def addFolderUrl(self, value: QUrl) -> None:
        if value.isLocalFile():
            self._add_paths([Path(value.toLocalFile())])

    def _add_paths(self, paths: list[Path]) -> None:
        if self.busy:
            return
        result = self._use_case.add_inputs(paths, tuple(item.path for item in self._items))
        self._items += self._use_case.new_items(result.added)
        self._model.set_items(self._items)
        if self._selected_index < 0 and self._items:
            self._select_index(0)
        self._status_text = f"已导入 {len(result.added)} 张图片"
        if result.duplicates or result.ignored:
            self._status_text += f"，跳过 {result.duplicates + result.ignored} 项"
        self._phase = "ready" if self._items else "idle"
        self.stateChanged.emit()

    @Slot(int)
    def selectIndex(self, index: int) -> None:
        self._select_index(index)

    @Slot(int)
    def selectRelative(self, delta: int) -> None:
        """用键盘切换当前预览图片，不改变队列顺序。"""

        if not self._items:
            return
        base_index = self._selected_index if self._selected_index >= 0 else 0
        target = max(0, min(base_index + delta, len(self._items) - 1))
        if target != self._selected_index:
            self._select_index(target)

    def _select_index(self, index: int) -> None:
        if not 0 <= index < len(self._items):
            return
        self._selected_index = index
        self._model.set_selected_index(index)
        self._refresh_preview()
        self.stateChanged.emit()

    @Slot(int)
    def removeIndex(self, index: int) -> None:
        if self.busy or not 0 <= index < len(self._items):
            return
        mutable = list(self._items)
        mutable.pop(index)
        self._items = tuple(mutable)
        self._selected_index = min(self._selected_index, len(self._items) - 1)
        self._model.set_items(self._items)
        self._model.set_selected_index(self._selected_index)
        self._refresh_preview()
        self._status_text = f"队列中有 {len(self._items)} 张图片"
        self.stateChanged.emit()

    @Slot(int, int)
    def moveIndex(self, index: int, delta: int) -> None:
        target = index + delta
        if self.busy or not 0 <= index < len(self._items) or not 0 <= target < len(self._items):
            return
        mutable = list(self._items)
        selected_id = self._selected_item().id if self._selected_item() else None
        item = mutable.pop(index)
        mutable.insert(target, item)
        self._items = tuple(mutable)
        self._selected_index = next(
            (
                current_index
                for current_index, current in enumerate(self._items)
                if current.id == selected_id
            ),
            -1,
        )
        self._model.move_item(index, target)
        self._model.set_selected_index(self._selected_index)
        self.stateChanged.emit()

    @Slot(str, str)
    def moveItem(self, dragged_id: str, target_id: str) -> None:
        if self.busy or dragged_id == target_id:
            return
        source = next(
            (index for index, item in enumerate(self._items) if item.id == dragged_id),
            -1,
        )
        target = next(
            (index for index, item in enumerate(self._items) if item.id == target_id),
            -1,
        )
        if source < 0 or target < 0:
            return
        mutable = list(self._items)
        selected_id = self._selected_item().id if self._selected_item() else None
        item = mutable.pop(source)
        mutable.insert(target, item)
        self._items = tuple(mutable)
        self._selected_index = next(
            (
                index
                for index, current in enumerate(self._items)
                if current.id == selected_id
            ),
            -1,
        )
        self._model.move_item(source, target)
        self._model.set_selected_index(self._selected_index)
        self.stateChanged.emit()

    @Slot(str)
    def setKeyword(self, value: str) -> None:
        self._settings.keyword = value
        self._persist_settings()
        self.stateChanged.emit()

    @Slot(int)
    def setAspectRatio(self, index: int) -> None:
        presets = list(AspectRatioPreset)
        if not 0 <= index < len(presets):
            return
        preset = presets[index]
        self._settings.aspect_ratio = preset
        if preset is not AspectRatioPreset.CUSTOM:
            resolution = preset.default_resolution
            self._settings.width = resolution.width
            self._settings.height = resolution.height
        self._settings.target_rect = self._recognized_target_rect()
        self._settings_changed()

    @Slot(str, str)
    def setResolution(self, width: str, height: str) -> None:
        try:
            self._settings.width = int(width)
            self._settings.height = int(height)
        except ValueError:
            self._status_text = "请输入有效的画面宽高。"
            self.stateChanged.emit()
            return
        self._settings_changed()

    @Slot(str)
    def setFrameRate(self, value: str) -> None:
        try:
            self._settings.frame_rate = float(value)
        except ValueError:
            self._status_text = "请输入有效帧率。"
            self.stateChanged.emit()
            return
        self._settings_changed()

    @Slot(str)
    def setFramesPerImage(self, value: str) -> None:
        try:
            self._settings.frames_per_image = int(value)
        except ValueError:
            self._status_text = "请输入有效帧数。"
            self.stateChanged.emit()
            return
        self._settings_changed()

    @Slot(int)
    def setExportMode(self, index: int) -> None:
        modes = list(ExportMode)
        if 0 <= index < len(modes):
            self._settings.export_mode = modes[index]
            self._settings_changed(refresh_preview=False)

    @Slot(float, float, float, float)
    def updateTargetRect(self, x: float, y: float, width: float, height: float) -> None:
        self._settings.target_rect = NormalizedRect(x, y, width, height).clamped()
        self._settings_changed()

    @Slot()
    def resetTargetRect(self) -> None:
        self._settings.target_rect = self._recognized_target_rect()
        self._settings_changed()

    @Slot(int)
    def selectCandidate(self, index: int) -> None:
        item = self._selected_item()
        if item is None or not 0 <= index < len(item.candidates):
            return
        mutable = list(self._items)
        mutable[self._selected_index] = self._use_case.select_candidate(
            item,
            item.candidates[index].id,
        )
        self._items = tuple(mutable)
        self._model.set_items(self._items)
        self._model.set_selected_index(self._selected_index)
        # 用户改选 OCR 候选时，让唯一对齐框完整包住新候选。
        self._settings.target_rect = self._recognized_target_rect()
        self._persist_settings()
        self._refresh_preview()
        self.stateChanged.emit()

    @Slot()
    def recognizeAll(self) -> None:
        if not self.canRecognize:
            return
        items = self._items
        keyword = self._settings.keyword
        self._start(
            "recognize",
            lambda progress: self._use_case.recognize(items, keyword, progress),
            "recognizing",
            "正在准备 Apple Vision 识别…",
        )

    @Slot(QUrl)
    def exportToFolder(self, destination: QUrl) -> None:
        if not self.canExport or not destination.isLocalFile():
            return
        items = self._items
        settings = replace(self._settings)
        path = Path(destination.toLocalFile())
        self._start(
            "export",
            lambda progress: self._use_case.export(items, settings, path, progress),
            "exporting",
            "正在准备导出…",
        )

    @Slot()
    def cancel(self) -> None:
        if self._runner.cancel():
            self._status_text = "正在取消…"
            self.stateChanged.emit()

    def _start(self, action: str, operation, phase: str, status: str) -> None:
        self._active_action = action
        self._phase = phase
        self._status_text = status
        self._progress_current = 0
        self._progress_total = 0
        if self._runner.start(operation, cancellable=True):
            self.stateChanged.emit()

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, message: str) -> None:
        self._progress_current = current
        self._progress_total = total
        self._status_text = message
        self.stateChanged.emit()

    @Slot(object)
    def _on_succeeded(self, result: Any) -> None:
        if self._active_action == "recognize":
            self._items = tuple(result)
            self._model.set_items(self._items)
            self._model.set_selected_index(self._selected_index)
            # 首次识别后以原图等比预览中的完整 OCR 范围初始化对齐框。
            self._settings.target_rect = self._recognized_target_rect()
            self._persist_settings()
            warnings = sum(1 for item in self._items if item.message)
            self._status_text = "识别完成" + (f"，{warnings} 张图片需要留意" if warnings else "")
            self._phase = "ready"
            self._refresh_preview()
            self.actionCompleted.emit("recognize", len(self._items))
        elif self._active_action == "export":
            self._phase = "completed"
            self._status_text = f"导出完成：{result.directory}"
            self.notificationRequested.emit("关键词快切已导出。", "success")
            self.actionCompleted.emit("export", int(result.total_frames))
        self.stateChanged.emit()

    @Slot(str, str)
    def _on_failed(self, _exception_name: str, message: str) -> None:
        self._phase = "failed"
        self._status_text = message or "操作失败，请重试。"
        self.notificationRequested.emit(self._status_text, "error")
        self.stateChanged.emit()

    @Slot()
    def _on_cancelled(self) -> None:
        self._phase = "ready" if self._items else "idle"
        self._status_text = "操作已取消，现有项目未改变"
        self.stateChanged.emit()

    @Slot()
    def _on_finished(self) -> None:
        self._active_action = ""
        self.stateChanged.emit()

    def _settings_changed(self, *, refresh_preview: bool = True) -> None:
        if message := self._settings.validation_message:
            self._status_text = message
        else:
            self._persist_settings()
            if refresh_preview:
                self._refresh_preview()
        self.stateChanged.emit()

    def _persist_settings(self) -> None:
        try:
            self._settings_store.save(self._settings)
        except (OSError, ValueError):
            pass

    def _selected_item(self) -> QuickCutQueueItem | None:
        if 0 <= self._selected_index < len(self._items):
            return self._items[self._selected_index]
        return None

    def _recognized_target_rect(self) -> NormalizedRect:
        """返回当前 OCR 完整范围在未对齐画布中的位置。"""

        item = self._selected_item()
        candidate = item.selected_candidate if item is not None else None
        if (
            item is None
            or candidate is None
            or min(item.width, item.height, self._settings.width, self._settings.height) <= 0
        ):
            return DEFAULT_TARGET_RECT
        natural_geometry = alignment_geometry(
            item.width,
            item.height,
            self._settings.width,
            self._settings.height,
            None,
            DEFAULT_TARGET_RECT,
        )
        return transformed_box(
            candidate.box,
            item.width,
            item.height,
            self._settings.width,
            self._settings.height,
            natural_geometry,
        ).clamped()

    def _refresh_preview(self) -> None:
        item = self._selected_item()
        if item is None or self._settings.validation_message:
            self._preview_provider.clear()
        else:
            try:
                # 预览限制长边，导出仍使用完整设置分辨率。
                scale = min(1.0, 1200 / max(self._settings.width, self._settings.height))
                width = max(64, int(self._settings.width * scale) // 2 * 2)
                height = max(64, int(self._settings.height * scale) // 2 * 2)
                preview_settings = replace(self._settings, width=width, height=height)
                image = self._renderer.render(
                    item.path,
                    item.selected_candidate.box if item.selected_candidate else None,
                    preview_settings,
                )
                self._preview_provider.set_image(image)
            except ImageRenderError as exc:
                self._preview_provider.clear()
                self._status_text = str(exc)
        self._preview_revision += 1


__all__ = ["QuickCutViewModel"]
