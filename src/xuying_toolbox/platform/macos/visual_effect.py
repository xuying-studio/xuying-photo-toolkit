"""QQuickWindow 背后的 macOS 原生材质与减少动态效果适配。"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QWindow


def default_visuals_library_candidates() -> tuple[Path, ...]:
    configured = os.environ.get("XUYING_MAC_VISUALS_BRIDGE")
    bundle_root = getattr(sys, "_MEIPASS", None)
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    if bundle_root:
        candidates.append(Path(cast(str, bundle_root)) / "native/libXuyingMacVisuals.dylib")
    candidates.append(
        Path(__file__).resolve().parents[4] / "build/native/libXuyingMacVisuals.dylib"
    )
    return tuple(candidate.resolve() for candidate in candidates)


class MacVisualEffectAdapter:
    def __init__(self, library_path: Path | None = None) -> None:
        candidates = default_visuals_library_candidates()
        self._library_path = library_path or next(
            (path for path in candidates if path.is_file()),
            candidates[0],
        )
        self._library: ctypes.CDLL | None = None
        self._handle: int | None = None

    @property
    def available(self) -> bool:
        return sys.platform == "darwin" and self._library_path.is_file()

    @property
    def installed(self) -> bool:
        return self._handle is not None

    @property
    def handle(self) -> int | None:
        return self._handle

    def _load(self) -> ctypes.CDLL:
        if not self.available:
            raise RuntimeError("macOS 原生视觉组件不可用。")
        if self._library is None:
            library = ctypes.CDLL(str(self._library_path))
            library.XUMacVisualsInstall.argtypes = [ctypes.c_void_p]
            library.XUMacVisualsInstall.restype = ctypes.c_void_p
            library.XUMacVisualsSetActive.argtypes = [ctypes.c_void_p, ctypes.c_bool]
            library.XUMacVisualsSetActive.restype = None
            library.XUMacVisualsDestroy.argtypes = [ctypes.c_void_p]
            library.XUMacVisualsDestroy.restype = None
            library.XUMacVisualsPassesHitTest.argtypes = [ctypes.c_void_p]
            library.XUMacVisualsPassesHitTest.restype = ctypes.c_bool
            library.XUMacVisualsIsBehindContent.argtypes = [ctypes.c_void_p]
            library.XUMacVisualsIsBehindContent.restype = ctypes.c_bool
            library.XUMacVisualsUsesIntegratedTitleBar.argtypes = [ctypes.c_void_p]
            library.XUMacVisualsUsesIntegratedTitleBar.restype = ctypes.c_bool
            library.XUMacVisualsAllowsBackgroundWindowDrag.argtypes = [ctypes.c_void_p]
            library.XUMacVisualsAllowsBackgroundWindowDrag.restype = ctypes.c_bool
            library.XUMacSystemReduceMotion.argtypes = []
            library.XUMacSystemReduceMotion.restype = ctypes.c_bool
            self._library = library
        return self._library

    def install(self, window: QWindow) -> bool:
        if self._handle is not None:
            return True
        library = self._load()
        handle = library.XUMacVisualsInstall(ctypes.c_void_p(int(window.winId())))
        self._handle = int(handle) if handle else None
        return self._handle is not None

    def set_active(self, active: bool) -> None:
        if self._handle is not None:
            self._load().XUMacVisualsSetActive(ctypes.c_void_p(self._handle), active)

    def system_reduce_motion(self) -> bool:
        return bool(self._load().XUMacSystemReduceMotion())

    def passes_hit_test(self) -> bool:
        if self._handle is None:
            return False
        return bool(
            self._load().XUMacVisualsPassesHitTest(ctypes.c_void_p(self._handle))
        )

    def is_behind_content(self) -> bool:
        if self._handle is None:
            return False
        return bool(
            self._load().XUMacVisualsIsBehindContent(ctypes.c_void_p(self._handle))
        )

    def uses_integrated_title_bar(self) -> bool:
        if self._handle is None:
            return False
        return bool(
            self._load().XUMacVisualsUsesIntegratedTitleBar(
                ctypes.c_void_p(self._handle)
            )
        )

    def allows_background_window_drag(self) -> bool:
        if self._handle is None:
            return False
        return bool(
            self._load().XUMacVisualsAllowsBackgroundWindowDrag(
                ctypes.c_void_p(self._handle)
            )
        )

    def destroy(self) -> None:
        if self._handle is None:
            return
        self._load().XUMacVisualsDestroy(ctypes.c_void_p(self._handle))
        self._handle = None


class MacMotionMonitor(QObject):
    policyChanged = Signal(str)

    def __init__(
        self,
        adapter: MacVisualEffectAdapter,
        parent: QObject | None = None,
        *,
        interval_ms: int = 2_000,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._last_reduce_motion: bool | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.refresh)

    def start(self) -> None:
        self.refresh()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def refresh(self) -> None:
        reduce_motion = self._adapter.system_reduce_motion()
        if reduce_motion == self._last_reduce_motion:
            return
        self._last_reduce_motion = reduce_motion
        self.policyChanged.emit("reduced" if reduce_motion else "full")


__all__ = ["MacMotionMonitor", "MacVisualEffectAdapter"]
