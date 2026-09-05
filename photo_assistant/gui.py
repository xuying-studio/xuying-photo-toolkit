"""旭影工具箱 Tkinter 图形界面。"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Callable

from . import __version__
from . import core


WINDOW_TITLE = "旭影工具箱"
# 改名后按新旧顺序迁移外观配置，后续只写入“旭影工具箱”目录。
LEGACY_WINDOW_TITLES = (
    "旭影的摄影工具集-关键词内嵌版",
    "旭影的摄影工具集",
)
MAX_PREVIEW_ROWS = 1000
MAX_ACTIVITY_ROWS = 300
SIDEBAR_BREAKPOINT = 1120
SIDEBAR_EXPANDED_WIDTH = 220
SIDEBAR_COMPACT_WIDTH = 160
KEYWORD_QUICKCUT_LIBRARY_NAME = "libKeywordAlignerBridge.dylib"
KEYWORD_QUICKCUT_MIN_MACOS = (13, 0)
VIBRANCY_LIBRARY_NAME = "libxuying_vibrancy.dylib"
MACOS_VIBRANCY_MATERIAL = 21
POINTER_CURSOR = "hand2" if sys.platform == "win32" else "pointinghand"
UI_CONFIG_FILE = (
    core.app_data_dir(WINDOW_TITLE)
    / "ui_config.json"
)
LEGACY_UI_CONFIG_FILES = tuple(
    core.app_data_dir(title) / "ui_config.json"
    for title in LEGACY_WINDOW_TITLES
)

DEFAULT_SKIN_ID = "professional_dark"

PROFESSIONAL_DARK_PALETTE = {
    "window": "#0B0E14",
    "chrome": "#0D1118",
    "surface": "#0B0E14",
    "panel": "#141923",
    "panel_alt": "#1A202B",
    "border": "#282D36",
    "table_grid": "#2A303B",
    "panel_highlight": "#303743",
    "shadow": "#07090D",
    "text": "#F5F7FA",
    "title": "#F5F7FA",
    "secondary": "#8B93A5",
    "tertiary": "#626B7D",
    "accent": "#2F6BFF",
    "accent_active": "#2457D6",
    "accent_text": "#FFFFFF",
    "accent_soft": "#182A53",
    "glow": "#2F6BFF",
    "glow_soft": "#182A53",
    "danger": "#EF4444",
    "danger_active": "#DC2626",
    "danger_soft": "#3A1C22",
    "warning": "#F59E0B",
    "warning_soft": "#3B2B12",
    "selection": "#1D3975",
    "success": "#22C55E",
    "success_soft": "#153923",
    "panel_radius": 16,
    "control_radius": 11,
}

NEBULA_NAVY_PALETTE = {
    "window": "#070B1A",
    "chrome": "#0C1228",
    "surface": "#0A1024",
    "panel": "#101A35",
    "panel_alt": "#162345",
    "border": "#26365F",
    "table_grid": "#243252",
    "panel_highlight": "#405FC5",
    "shadow": "#040612",
    "text": "#F5F7FF",
    "title": "#7EA0FF",
    "secondary": "#95A2C3",
    "tertiary": "#65739B",
    "accent": "#5A6FFF",
    "accent_active": "#4457DD",
    "accent_text": "#FFFFFF",
    "accent_soft": "#202D68",
    "glow": "#6D5DFB",
    "glow_soft": "#1D2053",
    "danger": "#EF4444",
    "danger_active": "#DC2626",
    "danger_soft": "#3A1C2D",
    "warning": "#F59E0B",
    "warning_soft": "#3B2B18",
    "selection": "#263E8A",
    "success": "#22C55E",
    "success_soft": "#153B31",
    "panel_radius": 18,
    "control_radius": 12,
}

LIQUID_GLASS_PALETTE = {
    "window": "#132536",
    "chrome": "#172B3D",
    "surface": "#132536",
    "panel": "#1B3449",
    "panel_alt": "#29485E",
    "border": "#54748B",
    "table_grid": "#38566A",
    "panel_highlight": "#7393A8",
    "shadow": "#091722",
    "text": "#F4FBFF",
    "title": "#DDF8FF",
    "secondary": "#B5CAD6",
    "tertiary": "#7E9AAA",
    "accent": "#6ADCF4",
    "accent_active": "#4EC0D7",
    "accent_text": "#06212A",
    "accent_soft": "#254B5C",
    "glow": "#83E8FF",
    "glow_soft": "#254B5C",
    "danger": "#FF7B7B",
    "danger_active": "#F25C5C",
    "danger_soft": "#532D36",
    "warning": "#FFD56A",
    "warning_soft": "#554824",
    "selection": "#35677D",
    "success": "#58D9A2",
    "success_soft": "#244C40",
    "panel_radius": 22,
    "control_radius": 16,
}

BENTO_MODULAR_PALETTE = {
    "window": "#11100E",
    "chrome": "#171614",
    "surface": "#11100E",
    "panel": "#201F1C",
    "panel_alt": "#2A2823",
    "border": "#464137",
    "table_grid": "#35322C",
    "panel_highlight": "#5A5142",
    "shadow": "#080706",
    "text": "#F4F0E7",
    "title": "#FFD18A",
    "secondary": "#B5AB9B",
    "tertiary": "#81796D",
    "accent": "#E68A2E",
    "accent_active": "#C96D16",
    "accent_text": "#1A1108",
    "accent_soft": "#4B321B",
    "glow": "#D4FF5D",
    "glow_soft": "#354220",
    "danger": "#FF6B62",
    "danger_active": "#E64E45",
    "danger_soft": "#4A2420",
    "warning": "#F3C64E",
    "warning_soft": "#433719",
    "selection": "#5E4021",
    "success": "#9DDA5E",
    "success_soft": "#2D4120",
    "panel_radius": 18,
    "control_radius": 10,
}

EDITORIAL_MINIMAL_PALETTE = {
    "window": "#EEE9DF",
    "chrome": "#E5DED2",
    "surface": "#EEE9DF",
    "panel": "#FAF7F0",
    "panel_alt": "#E8E1D6",
    "border": "#B9B0A3",
    "table_grid": "#CDC4B7",
    "panel_highlight": "#FFFFFF",
    "shadow": "#CFC6B8",
    "text": "#1E1C19",
    "title": "#1E1C19",
    "secondary": "#655F57",
    "tertiary": "#817A71",
    "accent": "#A62D2A",
    "accent_active": "#84211F",
    "accent_text": "#FFFFFF",
    "accent_soft": "#E9C8C3",
    "glow": "#A62D2A",
    "glow_soft": "#E9C8C3",
    "danger": "#B42318",
    "danger_active": "#8F1C13",
    "danger_soft": "#F2D5D0",
    "warning": "#8A5B00",
    "warning_soft": "#F4E8CA",
    "selection": "#E7CCC8",
    "success": "#26734D",
    "success_soft": "#D8EADD",
    "panel_radius": 3,
    "control_radius": 2,
}

AURORA_SPATIAL_PALETTE = {
    "window": "#080B19",
    "chrome": "#0E1126",
    "surface": "#0A0E20",
    "panel": "#151A39",
    "panel_alt": "#242451",
    "border": "#4B4F7B",
    "table_grid": "#34375D",
    "panel_highlight": "#6C68A1",
    "shadow": "#030511",
    "text": "#F6F2FF",
    "title": "#C9C2FF",
    "secondary": "#AAA6C8",
    "tertiary": "#777699",
    "accent": "#8F7DFF",
    "accent_active": "#7360E5",
    "accent_text": "#FFFFFF",
    "accent_soft": "#332C70",
    "glow": "#4CE5D0",
    "glow_soft": "#174C4C",
    "danger": "#FF6D92",
    "danger_active": "#E64B75",
    "danger_soft": "#4A2038",
    "warning": "#F4C95D",
    "warning_soft": "#453A1D",
    "selection": "#42398C",
    "success": "#4CE5D0",
    "success_soft": "#164943",
    "panel_radius": 18,
    "control_radius": 12,
}

SOFT_3D_PALETTE = {
    "window": "#DFE6F1",
    "chrome": "#D6DEEA",
    "surface": "#DFE6F1",
    "panel": "#E7EDF6",
    "panel_alt": "#F1F5FA",
    "border": "#AAB7C8",
    "table_grid": "#C5CFDC",
    "panel_highlight": "#FFFFFF",
    "shadow": "#C0CAD9",
    "text": "#354052",
    "title": "#44405E",
    "secondary": "#667287",
    "tertiary": "#818DA0",
    "accent": "#6E65C7",
    "accent_active": "#574FAE",
    "accent_text": "#FFFFFF",
    "accent_soft": "#D5D2F1",
    "glow": "#8A80E2",
    "glow_soft": "#D5D2F1",
    "danger": "#B94C61",
    "danger_active": "#9F384C",
    "danger_soft": "#F0D5DC",
    "warning": "#9A5C22",
    "warning_soft": "#F3E3D1",
    "selection": "#D2D0F2",
    "success": "#34785A",
    "success_soft": "#D6E9DF",
    "panel_radius": 22,
    "control_radius": 14,
}

SKIN_PALETTES = {
    "professional_dark": PROFESSIONAL_DARK_PALETTE,
    "nebula_navy": NEBULA_NAVY_PALETTE,
    "liquid_glass": LIQUID_GLASS_PALETTE,
    "bento_modular": BENTO_MODULAR_PALETTE,
    "editorial_minimal": EDITORIAL_MINIMAL_PALETTE,
    "aurora_spatial": AURORA_SPATIAL_PALETTE,
    "soft_3d": SOFT_3D_PALETTE,
}

SKIN_LABELS = {
    "professional_dark": ("专业深黑", "克制、清晰的高密度深色工作界面"),
    "nebula_navy": ("星雾深蓝", "深海军蓝层级与柔和蓝紫环境光"),
    "liquid_glass": ("流光玻璃", "轻盈通透的蓝灰玻璃材质与高亮边缘"),
    "bento_modular": ("模块拼盘", "暖橙强调色与清晰的模块化工作区"),
    "editorial_minimal": ("编辑部极简", "纸张暖白、细线层级与摄影杂志气质"),
    "aurora_spatial": ("极光空间", "深夜空间层级与紫绿极光状态光"),
    "soft_3d": ("柔软三维", "浅灰蓝浮雕层级与柔和低饱和控件"),
}

SKIN_ORDER = (
    "professional_dark",
    "nebula_navy",
    "liquid_glass",
    "bento_modular",
    "editorial_minimal",
    "aurora_spatial",
    "soft_3d",
)
GLASS_SKIN_IDS = frozenset(("nebula_navy", "liquid_glass", "aurora_spatial"))

# 保留原常量名称，兼容现有测试和外部扩展。
DARK_PALETTE = PROFESSIONAL_DARK_PALETTE

_NATIVE_VIBRANCY_LIBRARY: ctypes.CDLL | None = None
_NATIVE_VIBRANCY_LOAD_ATTEMPTED = False
_KEYWORD_QUICKCUT_LIBRARY: ctypes.CDLL | None = None
_KEYWORD_QUICKCUT_LIBRARY_PATH: Path | None = None


def _load_native_vibrancy_library() -> ctypes.CDLL | None:
    """加载可选 macOS 原生磨砂桥接；失败时保持纯 Tk 降级。"""

    global _NATIVE_VIBRANCY_LIBRARY, _NATIVE_VIBRANCY_LOAD_ATTEMPTED
    if sys.platform != "darwin":
        return None
    if _NATIVE_VIBRANCY_LOAD_ATTEMPTED:
        return _NATIVE_VIBRANCY_LIBRARY
    _NATIVE_VIBRANCY_LOAD_ATTEMPTED = True
    candidates: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / VIBRANCY_LIBRARY_NAME)
    project_dir = Path(__file__).resolve().parent.parent
    candidates.append(project_dir / "build" / "native" / VIBRANCY_LIBRARY_NAME)
    candidates.append(
        Path(sys.executable).resolve().parent.parent
        / "Frameworks"
        / VIBRANCY_LIBRARY_NAME
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            library = ctypes.CDLL(str(candidate))
            library.XUApplyVibrancy.argtypes = [ctypes.c_char_p, ctypes.c_int]
            library.XUApplyVibrancy.restype = None
            library.XURemoveVibrancy.argtypes = [ctypes.c_char_p]
            library.XURemoveVibrancy.restype = None
            _NATIVE_VIBRANCY_LIBRARY = library
            return library
        except (OSError, AttributeError):
            continue
    return None


def _set_native_vibrancy(window: tk.Tk | tk.Toplevel, enabled: bool) -> bool:
    """为指定 Tk 窗口启用或移除 macOS 系统磨砂材质。"""

    library = _load_native_vibrancy_library()
    if library is None:
        return False
    try:
        window.update_idletasks()
        title = window.title().encode("utf-8")
        if enabled:
            window.attributes("-transparent", True)
            library.XUApplyVibrancy(title, MACOS_VIBRANCY_MATERIAL)
        else:
            library.XURemoveVibrancy(title)
            window.attributes("-transparent", False)
        return True
    except (tk.TclError, OSError, ValueError):
        return False


def _display_filename(value: str | Path) -> str:
    """仅返回表格展示需要的文件名，内部路径保持不变。"""

    return Path(value).name or str(value)


def _resolve_keyword_quickcut_library() -> Path | None:
    """查找打包内置或开发环境中的关键词快切原生桥接。"""

    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        contents = Path(sys.executable).resolve().parent.parent
        candidates.append(contents / "Frameworks" / KEYWORD_QUICKCUT_LIBRARY_NAME)
    configured = os.environ.get("KEYWORD_QUICKCUT_LIBRARY", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    project_dir = Path(__file__).resolve().parent.parent
    candidates.append(project_dir / "build" / "native" / KEYWORD_QUICKCUT_LIBRARY_NAME)
    candidates.append(
        project_dir
        / "build"
        / "keyword_aligner"
        / "arm64-apple-macosx"
        / "release"
        / KEYWORD_QUICKCUT_LIBRARY_NAME
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _keyword_quickcut_support(
    library_path: Path | None,
    *,
    platform_name: str | None = None,
    machine: str | None = None,
    mac_version: str | None = None,
) -> tuple[bool, str]:
    """返回关键词快切在当前设备上的可用状态和说明。"""

    current_platform = platform_name or sys.platform
    if current_platform != "darwin":
        return False, "关键词快切仅支持 macOS 13 或更高版本。"
    current_machine = (machine or platform.machine()).casefold()
    if current_machine != "arm64":
        return False, "当前内置版本需要 Apple Silicon Mac。"
    version_text = mac_version if mac_version is not None else platform.mac_ver()[0]
    try:
        values = [int(value) for value in version_text.split(".")[:2]]
        values.extend([0] * (2 - len(values)))
        parts = tuple(values)
    except ValueError:
        parts = ()
    if parts and parts < KEYWORD_QUICKCUT_MIN_MACOS:
        return False, "关键词快切需要 macOS 13 或更高版本。"
    if library_path is None:
        return False, "未找到关键词快切内嵌组件，请重新安装完整版本。"
    return True, "原生离线 OCR 工作区已就绪。"


def _load_keyword_quickcut_library(path: Path | None = None) -> ctypes.CDLL | None:
    """加载 SwiftUI 内嵌桥接，并声明稳定的 C ABI。"""

    global _KEYWORD_QUICKCUT_LIBRARY, _KEYWORD_QUICKCUT_LIBRARY_PATH
    resolved = path or _resolve_keyword_quickcut_library()
    if resolved is None:
        return None
    resolved = resolved.resolve()
    if _KEYWORD_QUICKCUT_LIBRARY is not None and _KEYWORD_QUICKCUT_LIBRARY_PATH == resolved:
        return _KEYWORD_QUICKCUT_LIBRARY
    try:
        library = ctypes.CDLL(str(resolved))
        library.XUKeywordAlignerCreate.argtypes = [
            ctypes.c_char_p,
            ctypes.c_double,
            ctypes.c_double,
            ctypes.c_double,
            ctypes.c_double,
        ]
        library.XUKeywordAlignerCreate.restype = ctypes.c_void_p
        library.XUKeywordAlignerSetFrame.argtypes = [
            ctypes.c_void_p,
            ctypes.c_double,
            ctypes.c_double,
            ctypes.c_double,
            ctypes.c_double,
        ]
        library.XUKeywordAlignerSetFrame.restype = None
        library.XUKeywordAlignerSetVisible.argtypes = [ctypes.c_void_p, ctypes.c_int32]
        library.XUKeywordAlignerSetVisible.restype = None
        library.XUKeywordAlignerSetTheme.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        library.XUKeywordAlignerSetTheme.restype = None
        library.XUKeywordAlignerIsBusy.argtypes = [ctypes.c_void_p]
        library.XUKeywordAlignerIsBusy.restype = ctypes.c_int32
        library.XUKeywordAlignerCancel.argtypes = [ctypes.c_void_p]
        library.XUKeywordAlignerCancel.restype = None
        library.XUKeywordAlignerDestroy.argtypes = [ctypes.c_void_p]
        library.XUKeywordAlignerDestroy.restype = None
    except (OSError, AttributeError):
        return None
    _KEYWORD_QUICKCUT_LIBRARY = library
    _KEYWORD_QUICKCUT_LIBRARY_PATH = resolved
    return library


class KeywordQuickCutBridge:
    """管理 SwiftUI 关键词工作区在 Tk 主窗口中的原生视图句柄。"""

    def __init__(self, library: ctypes.CDLL) -> None:
        self.library = library
        self.handle: int | None = None

    @property
    def is_attached(self) -> bool:
        return self.handle is not None

    def attach(
        self,
        window_title: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> bool:
        if self.handle is None:
            title_buffer = ctypes.create_string_buffer(window_title.encode("utf-8"))
            handle = self.library.XUKeywordAlignerCreate(
                title_buffer,
                x,
                y,
                width,
                height,
            )
            if not handle:
                return False
            self.handle = int(handle)
        else:
            self.set_frame(x, y, width, height)
        self.set_visible(True)
        return True

    def set_frame(self, x: float, y: float, width: float, height: float) -> None:
        if self.handle is not None:
            self.library.XUKeywordAlignerSetFrame(
                ctypes.c_void_p(self.handle),
                x,
                y,
                width,
                height,
            )

    def set_visible(self, visible: bool) -> None:
        if self.handle is not None:
            self.library.XUKeywordAlignerSetVisible(
                ctypes.c_void_p(self.handle),
                ctypes.c_int32(1 if visible else 0),
            )

    def set_theme(self, skin_id: str) -> None:
        """把工具箱皮肤同步给同窗内嵌的 SwiftUI 工作区。"""

        if self.handle is None:
            return
        theme_buffer = ctypes.create_string_buffer(skin_id.encode("utf-8"))
        self.library.XUKeywordAlignerSetTheme(
            ctypes.c_void_p(self.handle),
            theme_buffer,
        )

    def is_busy(self) -> bool:
        if self.handle is None:
            return False
        return bool(
            self.library.XUKeywordAlignerIsBusy(ctypes.c_void_p(self.handle))
        )

    def cancel(self) -> None:
        if self.handle is not None:
            self.library.XUKeywordAlignerCancel(ctypes.c_void_p(self.handle))

    def destroy(self) -> None:
        if self.handle is None:
            return
        handle = self.handle
        self.handle = None
        self.library.XUKeywordAlignerDestroy(ctypes.c_void_p(handle))


def _rounded_points(width: int, height: int, radius: int) -> list[int]:
    """返回 Canvas 平滑圆角矩形使用的控制点。"""

    safe_width = max(2, width)
    safe_height = max(2, height)
    safe_radius = min(radius, safe_width // 2, safe_height // 2)
    return [
        safe_radius,
        1,
        safe_width - safe_radius,
        1,
        safe_width - 1,
        1,
        safe_width - 1,
        safe_radius,
        safe_width - 1,
        safe_height - safe_radius,
        safe_width - 1,
        safe_height - 1,
        safe_width - safe_radius,
        safe_height - 1,
        safe_radius,
        safe_height - 1,
        1,
        safe_height - 1,
        1,
        safe_height - safe_radius,
        1,
        safe_radius,
        1,
        1,
    ]


def _enable_windows_dpi_awareness() -> None:
    """让 Windows 高分屏按真实缩放比例绘制，避免界面模糊。"""

    if sys.platform != "win32":
        return
    try:
        import ctypes

        # Windows 10 优先使用每显示器 DPI 感知；旧版本自动降级。
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class RoundedButton(tk.Canvas):
    """带悬停、按下、聚焦和禁用状态的圆角按钮。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        command: Callable[[], object],
        palette: dict[str, str],
        font: tuple[str, int] | tuple[str, int, str],
        role: str = "secondary",
        width: int | None = None,
        height: int = 38,
        radius: int | None = None,
        background: str | None = None,
    ) -> None:
        self._text = text
        self._command = command
        self._palette = palette
        self._font = font
        self._role = role
        self._selected = False
        self._state = tk.NORMAL
        self._hovered = False
        self._pressed = False
        self._focused = False
        self._radius = int(
            radius if radius is not None else palette.get("control_radius", 11)
        )
        measured = tkfont.Font(master=master, font=font).measure(text)
        requested_width = width or max(88, measured + 32)
        parent_background = background or str(master.cget("background"))
        super().__init__(
            master,
            width=requested_width,
            height=height,
            background=parent_background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=1,
            cursor=POINTER_CURSOR,
        )
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Return>", self._on_keyboard)
        self.bind("<space>", self._on_keyboard)

    def _colors(self) -> tuple[str, str, str]:
        palette = self._palette
        if self._state == tk.DISABLED:
            return palette["surface"], palette["tertiary"], palette["border"]
        if self._role == "primary":
            fill = palette["accent_active"] if self._pressed else palette["accent"]
            return fill, palette.get("accent_text", "#FFFFFF"), fill
        if self._role == "danger":
            fill = palette["danger_soft"] if self._hovered or self._pressed else palette["panel_alt"]
            return fill, palette["danger"], palette["danger"] if self._focused else palette["border"]
        if self._role == "segment":
            if self._selected:
                return palette["panel"], palette["text"], palette["border"]
            fill = palette["border"] if self._hovered or self._pressed else palette["panel_alt"]
            return fill, palette["secondary"], palette["panel_alt"]
        fill = palette["border"] if self._hovered or self._pressed else palette["panel_alt"]
        outline = palette["accent"] if self._focused else palette["border"]
        return fill, palette["text"], outline

    def _draw(self, _event: tk.Event | None = None) -> None:
        width = max(2, self.winfo_width() - 1)
        height = max(2, self.winfo_height() - 1)
        fill, foreground, outline = self._colors()
        self.delete("all")
        self.create_polygon(
            _rounded_points(width, height, self._radius),
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=outline,
            width=1,
        )
        self.create_text(
            width // 2,
            height // 2,
            text=self._text,
            fill=foreground,
            font=self._font,
            anchor=tk.CENTER,
        )

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event: tk.Event) -> None:
        if self._state == tk.DISABLED:
            return
        self.focus_set()
        self._pressed = True
        self._draw()

    def _on_release(self, event: tk.Event) -> None:
        if self._state == tk.DISABLED:
            return
        was_pressed = self._pressed
        self._pressed = False
        self._draw()
        if was_pressed and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.invoke()

    def _on_focus_in(self, _event: tk.Event) -> None:
        self._focused = True
        self._draw()

    def _on_focus_out(self, _event: tk.Event) -> None:
        self._focused = False
        self._pressed = False
        self._draw()

    def _on_keyboard(self, _event: tk.Event) -> str:
        self.invoke()
        return "break"

    def invoke(self) -> object | None:
        if self._state == tk.DISABLED:
            return None
        return self._command()

    def set_selected(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self._draw()

    def configure(self, cnf: object | None = None, **kwargs: object) -> object:
        if "state" in kwargs:
            self._state = str(kwargs.pop("state"))
        if "text" in kwargs:
            self._text = str(kwargs.pop("text"))
        if "command" in kwargs:
            self._command = kwargs.pop("command")  # type: ignore[assignment]
        result = super().configure(cnf, **kwargs)
        self._draw()
        return result

    config = configure

    def cget(self, key: str) -> object:
        if key == "text":
            return self._text
        if key == "command":
            return self._command
        if key == "state":
            return self._state
        return super().cget(key)


class SidebarNavButton(tk.Canvas):
    """带跨平台线性图标的侧栏导航按钮。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        icon: str,
        command: Callable[[], object],
        palette: dict[str, str],
        font: tuple[str, int] | tuple[str, int, str],
        height: int = 50,
    ) -> None:
        self._text = text
        self._icon = icon
        self._command = command
        self._palette = palette
        self._font = font
        self._selected = False
        self._hovered = False
        self._pressed = False
        self._focused = False
        super().__init__(
            master,
            height=height,
            background=palette["chrome"],
            highlightthickness=0,
            borderwidth=0,
            takefocus=1,
            cursor=POINTER_CURSOR,
        )
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", self._on_focus)
        self.bind("<FocusOut>", self._on_focus)
        self.bind("<Return>", self._on_keyboard)
        self.bind("<space>", self._on_keyboard)

    def _draw(self, _event: tk.Event | None = None) -> None:
        width = max(2, self.winfo_width() - 1)
        height = max(2, self.winfo_height() - 1)
        self.delete("all")
        if self._selected:
            fill = self._palette["accent"]
            foreground = self._palette.get("accent_text", "#FFFFFF")
            outline = self._palette["accent"]
        else:
            fill = (
                self._palette["panel_alt"]
                if self._hovered or self._pressed
                else self._palette["chrome"]
            )
            foreground = self._palette["text"] if self._hovered else self._palette["secondary"]
            outline = self._palette["accent"] if self._focused else fill
        self.create_polygon(
            _rounded_points(width, height, 13),
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=outline,
            width=1,
        )
        if self._selected:
            self.create_line(
                16,
                height - 3,
                width - 16,
                height - 3,
                fill=self._palette.get("glow", self._palette["accent"]),
                width=2,
            )
        icon_x = 24
        icon_y = height // 2
        self._draw_icon(icon_x, icon_y, foreground)
        self.create_text(
            48,
            icon_y,
            text=self._text,
            fill=foreground,
            font=self._font,
            anchor=tk.W,
        )

    def _draw_icon(self, x: int, y: int, color: str) -> None:
        """只用 Canvas 基础图元绘制图标，避免系统字体差异。"""

        if self._icon == "rename":
            self.create_oval(x - 8, y - 8, x + 8, y + 8, outline=color, width=2)
            self.create_line(x, y, x, y - 5, x + 5, y, fill=color, width=2)
            self.create_line(x - 7, y + 8, x - 3, y + 8, fill=color, width=2)
            return
        if self._icon == "cleanup":
            self.create_rectangle(x - 6, y - 5, x + 6, y + 8, outline=color, width=2)
            self.create_line(x - 9, y - 8, x + 9, y - 8, fill=color, width=2)
            self.create_line(x - 3, y - 11, x + 3, y - 11, fill=color, width=2)
            self.create_line(x - 2, y - 2, x - 2, y + 5, fill=color, width=1)
            self.create_line(x + 2, y - 2, x + 2, y + 5, fill=color, width=1)
            return
        if self._icon == "quickcut":
            self.create_oval(x - 8, y + 2, x - 2, y + 8, outline=color, width=2)
            self.create_oval(x + 2, y + 2, x + 8, y + 8, outline=color, width=2)
            self.create_line(x - 3, y + 3, x + 8, y - 8, fill=color, width=2)
            self.create_line(x + 3, y + 3, x - 8, y - 8, fill=color, width=2)
            return
        self.create_line(x - 8, y - 5, x + 6, y - 5, fill=color, width=2)
        self.create_line(x + 3, y - 8, x + 7, y - 5, x + 3, y - 2, fill=color, width=2)
        self.create_line(x + 8, y + 5, x - 6, y + 5, fill=color, width=2)
        self.create_line(x - 3, y + 2, x - 7, y + 5, x - 3, y + 8, fill=color, width=2)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event: tk.Event) -> None:
        self.focus_set()
        self._pressed = True
        self._draw()

    def _on_release(self, event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self._draw()
        if was_pressed and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.invoke()

    def _on_focus(self, event: tk.Event) -> None:
        self._focused = event.type == tk.EventType.FocusIn
        self._draw()

    def _on_keyboard(self, _event: tk.Event) -> str:
        self.invoke()
        return "break"

    def invoke(self) -> object:
        return self._command()

    def set_selected(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self._draw()

    def cget(self, key: str) -> object:
        if key == "text":
            return self._text
        if key == "command":
            return self._command
        return super().cget(key)


class SkinPreviewCard(tk.Canvas):
    """在外观设置中展示可键盘选择的皮肤缩略预览。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        skin_id: str,
        selected_var: tk.StringVar,
        font: tuple[str, int] | tuple[str, int, str],
        width: int = 242,
        height: int = 142,
    ) -> None:
        self.skin_id = skin_id
        self._selected_var = selected_var
        self._font = font
        self._palette = SKIN_PALETTES[skin_id]
        self._hovered = False
        self._focused = False
        background = str(master.cget("background"))
        super().__init__(
            master,
            width=width,
            height=height,
            background=background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=1,
            cursor=POINTER_CURSOR,
        )
        self._selected_var.trace_add("write", lambda *_: self._draw())
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._select)
        self.bind("<Return>", self._select)
        self.bind("<space>", self._select)
        self.bind("<FocusIn>", self._on_focus)
        self.bind("<FocusOut>", self._on_focus)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._draw()

    def _on_focus(self, event: tk.Event) -> None:
        self._focused = event.type == tk.EventType.FocusIn
        self._draw()

    def _select(self, _event: tk.Event | None = None) -> str:
        self.focus_set()
        self._selected_var.set(self.skin_id)
        return "break"

    def _draw(self, _event: tk.Event | None = None) -> None:
        palette = self._palette
        selected = self._selected_var.get() == self.skin_id
        width = max(2, self.winfo_width() - 1)
        height = max(2, self.winfo_height() - 1)
        outline = (
            palette["accent"]
            if selected or self._hovered or self._focused
            else palette["border"]
        )
        self.delete("all")
        self.create_polygon(
            _rounded_points(width, height, int(palette.get("panel_radius", 15))),
            smooth=True,
            splinesteps=24,
            fill=palette["surface"],
            outline=outline,
            width=2 if selected else 1,
        )
        self.create_rectangle(10, 10, 54, 104, fill=palette["chrome"], outline="")
        self.create_oval(22, 22, 42, 42, fill=palette["accent_soft"], outline="")
        self.create_rectangle(18, 54, 47, 63, fill=palette["accent"], outline="")
        self.create_rectangle(18, 70, 43, 75, fill=palette["tertiary"], outline="")
        self.create_rectangle(18, 84, 46, 89, fill=palette["tertiary"], outline="")
        self.create_text(
            70,
            25,
            text="Aa  工作空间",
            fill=palette["title"],
            font=self._font,
            anchor=tk.W,
        )
        self.create_rectangle(70, 44, width - 14, 70, fill=palette["panel"], outline=palette["border"])
        self.create_rectangle(70, 78, width - 82, 104, fill=palette["panel_alt"], outline=palette["border"])
        self.create_rectangle(width - 74, 78, width - 14, 104, fill=palette["panel"], outline=palette["border"])
        self.create_line(
            72,
            101,
            width - 84,
            101,
            fill=palette["glow"],
            width=3,
        )
        label, _description = SKIN_LABELS[self.skin_id]
        self.create_text(
            12,
            height - 19,
            text=label,
            fill=palette["text"],
            font=self._font,
            anchor=tk.W,
        )
        if selected:
            self.create_oval(width - 31, height - 31, width - 13, height - 13, fill=palette["accent"], outline="")
            self.create_text(
                width - 22,
                height - 22,
                text="✓",
                fill=palette.get("accent_text", "#FFFFFF"),
                font=self._font,
            )


class RoundedEntry(tk.Canvas):
    """以 Canvas 外框包裹原生输入能力的圆角路径输入框。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        textvariable: tk.StringVar,
        palette: dict[str, str],
        font: tuple[str, int] | tuple[str, int, str],
        height: int = 38,
    ) -> None:
        self._palette = palette
        self._focused = False
        self._radius = int(palette.get("control_radius", 11))
        background = str(master.cget("background"))
        super().__init__(
            master,
            height=height,
            background=background,
            highlightthickness=0,
            borderwidth=0,
        )
        self.entry = tk.Entry(
            self,
            textvariable=textvariable,
            font=font,
            foreground=palette["text"],
            background=palette["panel"],
            insertbackground=palette["text"],
            selectbackground=palette["selection"],
            selectforeground=palette["text"],
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
        )
        self._entry_window = self.create_window(
            12,
            height // 2,
            anchor=tk.W,
            window=self.entry,
        )
        self.bind("<Configure>", self._draw)
        self.entry.bind("<FocusIn>", self._on_focus)
        self.entry.bind("<FocusOut>", self._on_focus)

    def _on_focus(self, event: tk.Event) -> None:
        self._focused = event.type == tk.EventType.FocusIn
        self._draw()

    def _draw(self, _event: tk.Event | None = None) -> None:
        width = max(2, self.winfo_width() - 1)
        height = max(2, self.winfo_height() - 1)
        self.delete("entry-outline")
        self.create_polygon(
            _rounded_points(width, height, self._radius),
            smooth=True,
            splinesteps=24,
            fill=self._palette["panel"],
            outline=self._palette["accent"] if self._focused else self._palette["border"],
            width=1,
            tags="entry-outline",
        )
        self.tag_lower("entry-outline")
        self.coords(self._entry_window, 12, height // 2)
        self.itemconfigure(
            self._entry_window,
            width=max(1, width - 24),
            height=max(1, height - 8),
        )

    def focus_set(self) -> None:
        self.entry.focus_set()


class RoundedSelect(tk.Canvas):
    """使用圆角画布和系统菜单实现的只读下拉选择器。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        textvariable: tk.StringVar,
        values: tuple[str, ...],
        palette: dict[str, str],
        font: tuple[str, int] | tuple[str, int, str],
        width: int = 150,
        height: int = 38,
    ) -> None:
        self._variable = textvariable
        self._values = values
        self._palette = palette
        self._font = font
        self._hovered = False
        self._focused = False
        self._radius = int(palette.get("control_radius", 11))
        background = str(master.cget("background"))
        super().__init__(
            master,
            width=width,
            height=height,
            background=background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=1,
            cursor=POINTER_CURSOR,
        )
        self._variable.trace_add("write", lambda *_: self._draw())
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._show_menu)
        self.bind("<Return>", self._show_menu)
        self.bind("<space>", self._show_menu)
        self.bind("<FocusIn>", self._on_focus)
        self.bind("<FocusOut>", self._on_focus)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._draw()

    def _on_focus(self, event: tk.Event) -> None:
        self._focused = event.type == tk.EventType.FocusIn
        self._draw()

    def _draw(self, _event: tk.Event | None = None) -> None:
        width = max(2, self.winfo_width() - 1)
        height = max(2, self.winfo_height() - 1)
        fill = self._palette["panel_alt"] if self._hovered else self._palette["panel"]
        outline = self._palette["accent"] if self._focused else self._palette["border"]
        self.delete("all")
        self.create_polygon(
            _rounded_points(width, height, self._radius),
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=outline,
            width=1,
        )
        self.create_text(
            14,
            height // 2,
            text=self._variable.get(),
            fill=self._palette["text"],
            font=self._font,
            anchor=tk.W,
        )
        self.create_text(
            width - 15,
            height // 2 - 1,
            text="⌄",
            fill=self._palette["secondary"],
            font=self._font,
            anchor=tk.CENTER,
        )

    def _show_menu(self, _event: tk.Event | None = None) -> str:
        self.focus_set()
        menu = tk.Menu(
            self,
            tearoff=False,
            background=self._palette["panel_alt"],
            foreground=self._palette["text"],
            activebackground=self._palette["accent"],
            activeforeground=self._palette.get("accent_text", "#FFFFFF"),
            selectcolor=self._palette["accent"],
            relief=tk.FLAT,
            borderwidth=1,
        )
        for value in self._values:
            menu.add_radiobutton(
                label=value,
                value=value,
                variable=self._variable,
            )
        try:
            menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        finally:
            menu.grab_release()
        return "break"


class RoundedCheckbutton(tk.Canvas):
    """与系统蓝强调色一致的轻量圆角复选框。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        variable: tk.BooleanVar,
        palette: dict[str, str],
        font: tuple[str, int] | tuple[str, int, str],
    ) -> None:
        self._text = text
        self._variable = variable
        self._palette = palette
        self._font = font
        self._hovered = False
        self._focused = False
        measured = tkfont.Font(master=master, font=font).measure(text)
        background = str(master.cget("background"))
        super().__init__(
            master,
            width=measured + 32,
            height=30,
            background=background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=1,
            cursor=POINTER_CURSOR,
        )
        self._variable.trace_add("write", lambda *_: self._draw())
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._toggle)
        self.bind("<Return>", self._toggle)
        self.bind("<space>", self._toggle)
        self.bind("<FocusIn>", self._on_focus)
        self.bind("<FocusOut>", self._on_focus)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._draw()

    def _on_focus(self, event: tk.Event) -> None:
        self._focused = event.type == tk.EventType.FocusIn
        self._draw()

    def _toggle(self, _event: tk.Event | None = None) -> str:
        self.focus_set()
        self._variable.set(not self._variable.get())
        return "break"

    def _draw(self, _event: tk.Event | None = None) -> None:
        checked = self._variable.get()
        palette = self._palette
        self.delete("all")
        self.create_polygon(
            _rounded_points(17, 17, 5),
            smooth=True,
            splinesteps=16,
            fill=palette["accent"] if checked else palette["panel"],
            outline=(
                palette["accent"]
                if checked or self._hovered or self._focused
                else palette["border"]
            ),
            width=1,
        )
        if checked:
            self.create_line(
                4,
                9,
                7,
                12,
                13,
                5,
                fill=palette.get("accent_text", "#FFFFFF"),
                width=2,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
        self.create_text(
            25,
            9,
            text=self._text,
            fill=palette["text"],
            font=self._font,
            anchor=tk.W,
        )


class RoundedRadiobutton(tk.Canvas):
    """使用电光蓝选中态的跨平台单选按钮。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        variable: tk.StringVar,
        value: str,
        palette: dict[str, str],
        font: tuple[str, int] | tuple[str, int, str],
    ) -> None:
        self._text = text
        self._variable = variable
        self._value = value
        self._palette = palette
        self._font = font
        self._hovered = False
        self._focused = False
        measured = tkfont.Font(master=master, font=font).measure(text)
        background = str(master.cget("background"))
        super().__init__(
            master,
            width=measured + 34,
            height=30,
            background=background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=1,
            cursor=POINTER_CURSOR,
        )
        self._variable.trace_add("write", lambda *_: self._draw())
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._select)
        self.bind("<Return>", self._select)
        self.bind("<space>", self._select)
        self.bind("<FocusIn>", self._on_focus)
        self.bind("<FocusOut>", self._on_focus)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._draw()

    def _on_focus(self, event: tk.Event) -> None:
        self._focused = event.type == tk.EventType.FocusIn
        self._draw()

    def _select(self, _event: tk.Event | None = None) -> str:
        self.focus_set()
        self._variable.set(self._value)
        return "break"

    def _draw(self, _event: tk.Event | None = None) -> None:
        selected = self._variable.get() == self._value
        palette = self._palette
        outline = (
            palette["accent"]
            if selected or self._hovered or self._focused
            else palette["border"]
        )
        self.delete("all")
        self.create_oval(
            2,
            3,
            16,
            17,
            fill=palette["accent"] if selected else palette["panel"],
            outline=outline,
            width=1,
        )
        if selected:
            self.create_oval(
                7,
                8,
                11,
                12,
                fill=palette.get("accent_text", "#FFFFFF"),
                outline="",
            )
        self.create_text(
            25,
            10,
            text=self._text,
            fill=palette["text"],
            font=self._font,
            anchor=tk.W,
        )


class RoundedProgressbar(tk.Canvas):
    """只显示真实确定型进度的圆角总进度条。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        palette: dict[str, str],
        length: int = 200,
        height: int = 8,
    ) -> None:
        self._palette = palette
        self._maximum = 100.0
        self._value = 0.0
        super().__init__(
            master,
            width=length,
            height=height,
            background=str(master.cget("background")),
            highlightthickness=0,
            borderwidth=0,
        )
        self.bind("<Configure>", self._draw)

    def _draw(self, _event: tk.Event | None = None) -> None:
        width = max(2, self.winfo_width() - 1)
        height = max(2, self.winfo_height() - 1)
        ratio = min(1.0, max(0.0, self._value / self._maximum)) if self._maximum else 0.0
        fill_width = round(width * ratio)
        self.delete("all")
        self.create_polygon(
            _rounded_points(width, height, height // 2),
            smooth=True,
            splinesteps=20,
            fill=self._palette["panel_alt"],
            outline=self._palette["border"],
            width=1,
        )
        if fill_width > 1:
            self.create_polygon(
                _rounded_points(fill_width, height, min(height // 2, fill_width // 2)),
                smooth=True,
                splinesteps=20,
                fill=self._palette["accent"],
                outline=self._palette["accent"],
                width=1,
            )

    def configure(self, cnf: object | None = None, **kwargs: object) -> object:
        if "maximum" in kwargs:
            self._maximum = max(1.0, float(kwargs.pop("maximum")))
        if "value" in kwargs:
            self._value = float(kwargs.pop("value"))
        result = super().configure(cnf, **kwargs)
        self._draw()
        return result

    config = configure

    def cget(self, key: str) -> object:
        if key == "mode":
            return "determinate"
        if key == "maximum":
            return self._maximum
        if key == "value":
            return self._value
        return super().cget(key)


class RoundedPanel(tk.Canvas):
    """使用 Canvas 绘制的轻量圆角磨砂面板。"""

    def __init__(
        self,
        master: tk.Misc,
        *,
        fill: str,
        outline: str,
        background: str,
        radius: int = 16,
        height: int = 86,
        padding: tuple[int, int] = (12, 8),
    ) -> None:
        super().__init__(
            master,
            height=height,
            background=background,
            highlightthickness=0,
            borderwidth=0,
        )
        self._fill = fill
        self._outline = outline
        palette = getattr(self.winfo_toplevel(), "palette", {})
        self._radius = int(palette.get("panel_radius", radius))
        self._padding = padding
        self._highlight = palette.get("panel_highlight", outline)
        self._shadow = palette.get("shadow", background)
        self.body = tk.Frame(self, background=fill, borderwidth=0)
        self.body.place(x=padding[0], y=padding[1])
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event: tk.Event) -> None:
        width = max(2, event.width - 1)
        height = max(2, event.height - 1)
        panel_width = max(2, width - 2)
        panel_height = max(2, height - 3)
        self.delete("all")
        self.create_polygon(
            _rounded_points(panel_width, panel_height, self._radius),
            smooth=True,
            splinesteps=24,
            fill=self._shadow,
            outline=self._shadow,
            width=1,
            tags="panel-shadow",
        )
        self.move("panel-shadow", 1, 2)
        self.create_polygon(
            _rounded_points(panel_width, panel_height, self._radius),
            smooth=True,
            splinesteps=24,
            fill=self._fill,
            outline=self._outline,
            width=1,
            tags="panel",
        )
        self.create_line(
            self._radius,
            2,
            max(self._radius, panel_width - self._radius),
            2,
            fill=self._highlight,
            width=1,
            tags="panel-highlight",
        )
        pad_x, pad_y = self._padding
        # 直接布局子容器，避免 Notebook 切页时 Canvas 窗口延迟映射。
        self.body.place_configure(
            x=pad_x,
            y=pad_y,
            width=max(1, event.width - pad_x * 2),
            height=max(1, event.height - pad_y * 2),
        )


class BasePage(ttk.Frame):
    """三个功能页共享的后台任务与状态栏。"""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=(28, 22), style="Page.TFrame")
        self._job_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._busy = False
        self.palette = self.winfo_toplevel().palette
        self.surface_background = self.winfo_toplevel().surface_background
        self.stats_container: tk.Frame | None = None
        self.table_frame: tk.Misc | None = None
        self._tree_grid_lines: list[tk.Frame] = []

        self.content = ttk.Frame(self, style="Page.TFrame")

        footer = RoundedPanel(
            self,
            fill=self.palette["panel"],
            outline=self.palette["border"],
            background=self.surface_background,
            radius=15,
            height=48,
            padding=(16, 7),
        )
        self.footer = footer
        footer_body = footer.body
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(
            footer_body,
            textvariable=self.status_var,
            background=self.palette["panel"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_caption,
        ).pack(side=tk.LEFT)
        self.progress_text_var = tk.StringVar(value="0 / 0 · 0%")
        tk.Label(
            footer_body,
            textvariable=self.progress_text_var,
            background=self.palette["panel"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_caption,
        ).pack(side=tk.RIGHT)
        self.progress = RoundedProgressbar(
            footer_body,
            palette=self.palette,
            length=200,
        )
        self.progress.pack(side=tk.RIGHT, padx=(0, 12), pady=5)
        self._progress_current = 0
        self._progress_total = 0
        self.content.pack(fill=tk.BOTH, expand=True)

    def run_job(
        self,
        status: str,
        function: Callable[[core.ProgressCallback], object],
        on_success: Callable[[object], None],
        *,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """在线程中执行耗时任务，界面更新仍留在主线程。"""

        if self._busy:
            return
        self._busy = True
        self.show_footer()
        self.status_var.set(status)
        self._apply_progress(0, 0, status)

        def worker() -> None:
            terminal_progress: tuple[int, int, str] | None = None

            def report_progress(current: int, total: int, message: str) -> None:
                nonlocal terminal_progress
                if total > 0 and current >= total:
                    terminal_progress = (current, total, message)
                    return
                self._job_queue.put(("progress", (current, total, message)))

            try:
                result = function(report_progress)
                self._job_queue.put(("success", (result, terminal_progress)))
            except Exception as exc:
                self._job_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()
        self.after(80, lambda: self._poll_job(on_success, on_progress))

    def _poll_job(
        self,
        on_success: Callable[[object], None],
        on_progress: Callable[[int, int, str], None] | None,
    ) -> None:
        latest_progress: tuple[int, int, str] | None = None
        final_event: tuple[str, object] | None = None
        while True:
            try:
                state, payload = self._job_queue.get_nowait()
            except queue.Empty:
                break
            if state == "progress":
                latest_progress = payload
            else:
                final_event = (state, payload)

        if latest_progress is not None:
            self._apply_progress(*latest_progress)
            if on_progress is not None:
                on_progress(*latest_progress)
        if final_event is None:
            self.after(80, lambda: self._poll_job(on_success, on_progress))
            return

        state, payload = final_event
        self._busy = False
        if state == "error":
            self.status_var.set("操作失败")
            messagebox.showerror("操作失败", str(payload), parent=self)
            return
        result, terminal_progress = payload
        if terminal_progress is not None:
            self._apply_progress(*terminal_progress)
            if on_progress is not None:
                on_progress(*terminal_progress)
        else:
            self._complete_progress()
        self.status_var.set("完成")
        on_success(result)

    def _apply_progress(self, current: int, total: int, message: str) -> None:
        """在主线程中显示当前数量、总数量和完成百分比。"""

        safe_total = max(0, total)
        safe_current = min(max(0, current), safe_total) if safe_total else 0
        self._progress_current = safe_current
        self._progress_total = safe_total
        self.progress.configure(maximum=max(1, safe_total), value=safe_current)
        percent = round(safe_current / safe_total * 100) if safe_total else 0
        self.progress_text_var.set(f"{safe_current} / {safe_total} · {percent}%")
        if message:
            self.status_var.set(message)

    def _complete_progress(self) -> None:
        """任务成功后把确定型进度条收束到 100%。"""

        if self._progress_total:
            self.progress.configure(
                maximum=self._progress_total,
                value=self._progress_total,
            )
            self.progress_text_var.set(
                f"{self._progress_total} / {self._progress_total} · 100%"
            )
            return
        self.progress.configure(maximum=1, value=1)
        self.progress_text_var.set("0 / 0 · 100%")

    def show_footer(self) -> None:
        """任务开始时显示状态和总进度，启动页面时保持隐藏。"""

        if self.footer.winfo_manager():
            return
        self.content.pack_forget()
        self.footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(14, 0))
        self.content.pack(fill=tk.BOTH, expand=True)

    @staticmethod
    def choose_folder(variable: tk.StringVar) -> None:
        selected = filedialog.askdirectory(title="选择照片文件夹")
        if selected:
            variable.set(selected)

    @staticmethod
    def require_folder(variable: tk.StringVar) -> str:
        value = variable.get().strip()
        if not value or not Path(value).is_dir():
            raise ValueError("请先选择有效的照片文件夹。")
        return value

    @staticmethod
    def fill_tree(tree: ttk.Treeview, rows: list[tuple[str, ...]]) -> None:
        tree.delete(*tree.get_children())
        for row in rows[:MAX_PREVIEW_ROWS]:
            tree.insert("", tk.END, values=row)

    @staticmethod
    def begin_activity(tree: ttk.Treeview, row: tuple[str, ...]) -> None:
        """开始新任务时清空旧预览，并立即显示准备状态。"""

        tree.delete(*tree.get_children())
        tree.insert("", tk.END, values=row)

    @staticmethod
    def append_activity(tree: ttk.Treeview, row: tuple[str, ...]) -> None:
        """追加实时处理记录，并限制行数以保持切页流畅。"""

        children = tree.get_children()
        if children and tuple(tree.item(children[-1], "values")) == row:
            return
        item = tree.insert("", tk.END, values=row)
        overflow = len(children) + 1 - MAX_ACTIVITY_ROWS
        if overflow > 0:
            tree.delete(*children[:overflow])
        tree.see(item)

    def install_vertical_tree_grid(self, tree: ttk.Treeview) -> None:
        """在结果表格各列之间绘制灰色实线，不增加横向网格。"""

        columns = tuple(tree.cget("columns"))
        self._tree_grid_lines = [
            tk.Frame(
                tree,
                width=1,
                background=self.palette["table_grid"],
                borderwidth=0,
            )
            for _ in columns[:-1]
        ]

        def redraw_grid(_event: tk.Event | None = None) -> None:
            if not tree.winfo_exists():
                return
            separator_x = 0
            height = max(1, tree.winfo_height())
            for index, line in enumerate(self._tree_grid_lines):
                separator_x += int(tree.column(columns[index], "width"))
                line.place(
                    x=max(0, separator_x - 1),
                    y=0,
                    width=1,
                    height=height,
                )
                line.lift()

        tree.bind(
            "<Configure>",
            lambda _event: tree.after_idle(redraw_grid),
            add="+",
        )
        tree.bind(
            "<ButtonRelease-1>",
            lambda _event: tree.after_idle(redraw_grid),
            add="+",
        )
        tree.after_idle(redraw_grid)

    def create_stats(
        self,
        items: list[tuple[str, str]],
    ) -> dict[str, tk.StringVar]:
        """创建默认隐藏、扫描完成后显示的统计卡片。"""

        container = tk.Frame(
            self.content,
            background=self.surface_background,
            borderwidth=0,
        )
        self.stats_container = container
        variables: dict[str, tk.StringVar] = {}
        for index, (key, label) in enumerate(items):
            is_emphasis = key in {"rename", "pending"}
            is_danger = key == "conflicts"
            fill = (
                self.palette["danger_soft"]
                if is_danger
                else self.palette["accent_soft"]
                if is_emphasis
                else self.palette["panel"]
            )
            outline = (
                self.palette["danger"]
                if is_danger
                else self.palette["accent"]
                if is_emphasis
                else self.palette["border"]
            )
            card = RoundedPanel(
                container,
                fill=fill,
                outline=outline,
                background=self.surface_background,
                radius=15,
                height=82,
                padding=(16, 11),
            )
            card.grid(
                row=0,
                column=index,
                sticky=tk.EW,
                padx=(0, 8) if index < len(items) - 1 else 0,
            )
            container.grid_columnconfigure(index, weight=1, uniform="stats")
            value_var = tk.StringVar(value="—")
            variables[key] = value_var
            tk.Label(
                card.body,
                textvariable=value_var,
                font=self.winfo_toplevel().font_stat_value,
                foreground=(
                    self.palette["danger"]
                    if is_danger
                    else self.palette["text"]
                ),
                background=fill,
                anchor=tk.W,
            ).pack(fill=tk.X)
            tk.Label(
                card.body,
                text=label,
                font=self.winfo_toplevel().font_caption,
                foreground=self.palette["secondary"],
                background=fill,
                anchor=tk.W,
            ).pack(fill=tk.X)
        return variables

    def show_stats(self) -> None:
        """首次扫描成功后，在结果表格上方显示统计卡片。"""

        if (
            self.stats_container is None
            or self.table_frame is None
            or self.stats_container.winfo_manager()
        ):
            return
        self.stats_container.pack(
            fill=tk.X,
            pady=(0, 12),
            before=self.table_frame,
        )

    def create_workflow_panel(self, *, height: int) -> tk.Frame:
        """创建统一的圆角操作面板并返回内容容器。"""

        panel = RoundedPanel(
            self.content,
            fill=self.palette["panel"],
            outline=self.palette["border"],
            background=self.surface_background,
            radius=18,
            height=height,
            padding=(20, 14),
        )
        panel.pack(fill=tk.X, pady=(0, 12))
        return panel.body

    def create_divider(self, parent: tk.Misc) -> None:
        """在操作面板内创建克制的分隔线。"""

        tk.Frame(
            parent,
            height=1,
            background=self.palette["border"],
        ).pack(fill=tk.X, pady=(11, 10))

    def create_button(
        self,
        parent: tk.Misc,
        *,
        text: str,
        command: Callable[[], object],
        role: str = "secondary",
        width: int | None = None,
    ) -> RoundedButton:
        """创建与页面视觉令牌一致的圆角按钮。"""

        return RoundedButton(
            parent,
            text=text,
            command=command,
            palette=self.palette,
            font=self.winfo_toplevel().font_body_medium,
            role=role,
            width=width,
        )

    @staticmethod
    def update_stats(
        variables: dict[str, tk.StringVar],
        values: dict[str, int],
    ) -> None:
        """批量更新统计卡片。"""

        for key, variable in variables.items():
            variable.set(str(values.get(key, 0)))


class RenamePage(BasePage):
    """根据拍摄时间重命名页面。"""

    def __init__(
        self,
        master: tk.Misc,
        folder_var: tk.StringVar | None = None,
    ) -> None:
        super().__init__(master)
        self.plan: core.RenamePlan | None = None
        self.folder_var = (
            folder_var if folder_var is not None else tk.StringVar(master=self)
        )

        self._title(
            "根据拍摄时间重命名",
            "按 EXIF 拍摄时间排序，将 RAW、JPG 和对应 XMP 侧车安全地统一命名。",
        )
        workflow = self.create_workflow_panel(height=126)
        self._folder_row(workflow)
        self.create_divider(workflow)

        action_row = tk.Frame(workflow, background=self.palette["panel"])
        action_row.pack(fill=tk.X)
        self.create_button(
            action_row,
            text="扫描并预览",
            command=self.preview,
            width=120,
        ).pack(side=tk.LEFT)
        self.create_button(
            action_row,
            text="执行重命名",
            command=self.execute,
            role="primary",
            width=130,
        ).pack(side=tk.LEFT, padx=8)
        self.create_button(
            action_row,
            text="撤回最近一次",
            command=self.undo,
            width=140,
        ).pack(side=tk.LEFT)
        tk.Label(
            action_row,
            text="仅扫描当前文件夹",
            background=self.palette["panel"],
            foreground=self.palette["tertiary"],
            font=self.winfo_toplevel().font_caption,
        ).pack(side=tk.RIGHT, padx=(12, 0))

        self.stats_vars = self.create_stats(
            [
                ("total", "扫描照片"),
                ("raw", "RAW"),
                ("jpg", "JPG"),
                ("rename", "待改名照片"),
                ("xmp", "同步改名 XMP"),
                ("conflicts", "冲突"),
            ]
        )

        columns = ("source", "target", "kind")
        self.tree = ttk.Treeview(self.content, columns=columns, show="headings")
        self.tree.heading("source", text="原文件")
        self.tree.heading("target", text="新文件")
        self.tree.heading("kind", text="类型")
        self.tree.column("source", width=300)
        self.tree.column("target", width=300)
        self.tree.column("kind", width=90, anchor=tk.CENTER)
        self._pack_tree(self.tree)

    def _title(self, title: str, subtitle: str) -> None:
        ttk.Label(self.content, text=title, style="PageTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(
            self.content,
            text=subtitle,
            style="Muted.TLabel",
            wraplength=850,
        ).pack(anchor=tk.W, pady=(5, 16))

    def _folder_row(self, parent: tk.Misc) -> None:
        row = tk.Frame(parent, background=self.palette["panel"])
        row.pack(fill=tk.X)
        tk.Label(
            row,
            text="照片文件夹",
            width=10,
            anchor=tk.W,
            background=self.palette["panel"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_body_medium,
        ).pack(side=tk.LEFT)
        RoundedEntry(
            row,
            textvariable=self.folder_var,
            palette=self.palette,
            font=self.winfo_toplevel().font_body,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.create_button(
            row,
            text="选择文件夹…",
            command=lambda: self.choose_folder(self.folder_var),
            width=132,
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _pack_tree(self, tree: ttk.Treeview) -> None:
        frame = RoundedPanel(
            self.content,
            fill=self.palette["panel"],
            outline=self.palette["border"],
            background=self.surface_background,
            radius=17,
            height=300,
            padding=(8, 8),
        )
        frame.pack(fill=tk.BOTH, expand=True)
        self.table_frame = frame
        scrollbar = ttk.Scrollbar(frame.body, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(
            in_=frame.body,
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=(1, 0),
            pady=1,
        )
        # Treeview 的实际父级是页面内容区，需要提升到圆角 Canvas 上方。
        tree.lift(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.install_vertical_tree_grid(tree)

    def preview(self) -> None:
        try:
            folder = self.require_folder(self.folder_var)
        except Exception as exc:
            messagebox.showwarning("提示", str(exc), parent=self)
            return
        self.run_job(
            "正在读取拍摄时间并生成预览…",
            lambda progress: core.build_rename_plan(
                folder,
                recursive=False,
                progress=progress,
            ),
            self._show_plan,
        )

    def _show_plan(self, payload: object) -> None:
        plan = payload
        assert isinstance(plan, core.RenamePlan)
        self.plan = plan
        rows = [
            (
                _display_filename(operation.source),
                _display_filename(operation.target),
                operation.kind,
            )
            for operation in plan.operations
        ]
        self.fill_tree(self.tree, rows)
        self.update_stats(
            self.stats_vars,
            {
                "total": plan.stats.total_images,
                "raw": plan.stats.raw_count,
                "jpg": plan.stats.jpg_count,
                "rename": plan.image_count,
                "xmp": plan.stats.xmp_count,
                "conflicts": len(plan.conflicts),
            },
        )
        self.show_stats()
        self.status_var.set(
            f"扫描 {plan.stats.total_images} 张照片；待改名 {plan.image_count} 张"
        )
        if plan.conflicts:
            messagebox.showerror(
                "发现重名冲突",
                "\n".join(plan.conflicts[:12]) + "\n\n请先处理冲突，程序不会覆盖任何文件。",
                parent=self,
            )
        elif plan.warnings:
            messagebox.showwarning(
                "扫描提示",
                "\n".join(plan.warnings[:12]),
                parent=self,
            )

    def execute(self) -> None:
        if self.plan is None:
            messagebox.showwarning("提示", "请先扫描并预览。", parent=self)
            return
        if self.plan.conflicts:
            messagebox.showerror("不能执行", "预览中存在重名冲突。", parent=self)
            return
        if not self.plan.operations:
            messagebox.showinfo("提示", "没有需要重命名的文件。", parent=self)
            return
        if not messagebox.askyesno(
            "确认重命名",
            f"将重命名 {self.plan.image_count} 张照片，并同步处理 XMP 侧车。\n\n"
            "程序不会覆盖已有文件，是否继续？",
            parent=self,
        ):
            return
        plan = self.plan
        self.begin_activity(self.tree, ("正在准备重命名", "", "等待执行"))
        self.run_job(
            "正在安全重命名…",
            lambda progress: core.execute_rename_plan(plan, progress=progress),
            lambda payload: self._rename_finished(payload, plan),
            on_progress=self._show_rename_activity,
        )

    def _show_rename_activity(
        self,
        current: int,
        total: int,
        message: str,
    ) -> None:
        state = "完成" if total > 0 and current >= total else "处理中"
        self.append_activity(self.tree, (message, "", state))

    def _rename_finished(self, payload: object, plan: core.RenamePlan) -> None:
        backup_path = Path(payload)
        count = plan.image_count
        self.plan = None
        self.fill_tree(
            self.tree,
            [
                (
                    _display_filename(operation.source),
                    _display_filename(operation.target),
                    f"{operation.kind} · 已重命名",
                )
                for operation in plan.operations
            ],
        )
        self.status_var.set(f"已重命名 {count} 张照片")
        messagebox.showinfo(
            "重命名完成",
            f"已处理 {count} 张照片。\n撤回记录：{backup_path}",
            parent=self,
        )

    def undo(self) -> None:
        if not messagebox.askyesno(
            "确认撤回",
            "将恢复最近一次重命名的照片和 XMP 侧车，是否继续？",
            parent=self,
        ):
            return
        self.begin_activity(self.tree, ("正在读取撤回记录", "", "等待恢复"))
        self.run_job(
            "正在撤回重命名…",
            lambda progress: core.undo_latest_rename(progress=progress),
            self._rename_undo_finished,
            on_progress=self._show_rename_activity,
        )

    def _rename_undo_finished(self, payload: object) -> None:
        value = int(payload)
        self.append_activity(self.tree, (f"已恢复 {value} 个文件", "", "撤回完成"))
        self.status_var.set(f"已恢复 {value} 个文件")
        messagebox.showinfo(
            "撤回完成",
            f"已恢复 {value} 个文件。",
            parent=self,
        )


class CleanupPage(BasePage):
    """RAW/JPG 配对清理页面。"""

    def __init__(
        self,
        master: tk.Misc,
        folder_var: tk.StringVar | None = None,
    ) -> None:
        super().__init__(master)
        self.items: list[core.CleanupItem] = []
        self.folder_var = (
            folder_var if folder_var is not None else tk.StringVar(master=self)
        )
        self.kind_var = tk.StringVar(value="JPG")
        self.trash_name = "回收站" if sys.platform == "win32" else "废纸篓"

        if sys.platform == "win32":
            cleanup_description = (
                "检查当前文件夹内的同名照片；待清理文件直接移入 Windows 回收站，"
                "不在原文件夹创建额外备份。"
            )
        else:
            cleanup_description = (
                "检查当前文件夹内的同名照片；移入废纸篓前创建隐藏安全备份，"
                "恢复不依赖直接访问废纸篓。"
            )

        ttk.Label(self.content, text="RAW / JPG 配对清理", style="PageTitle.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            self.content,
            text=cleanup_description,
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(5, 16))

        workflow = self.create_workflow_panel(height=164)
        folder_row = tk.Frame(workflow, background=self.palette["panel"])
        folder_row.pack(fill=tk.X)
        tk.Label(
            folder_row,
            text="照片文件夹",
            width=10,
            anchor=tk.W,
            background=self.palette["panel"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_body_medium,
        ).pack(side=tk.LEFT)
        RoundedEntry(
            folder_row,
            textvariable=self.folder_var,
            palette=self.palette,
            font=self.winfo_toplevel().font_body,
        ).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
        )
        self.create_button(
            folder_row,
            text="选择文件夹…",
            command=lambda: self.choose_folder(self.folder_var),
            width=132,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.create_divider(workflow)
        option_row = tk.Frame(workflow, background=self.palette["panel"])
        option_row.pack(fill=tk.X)
        tk.Label(
            option_row,
            text="清理格式",
            width=10,
            anchor=tk.W,
            background=self.palette["panel"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_body_medium,
        ).pack(side=tk.LEFT)
        self._kind_buttons = [
            RoundedRadiobutton(
                option_row,
                text="JPG（没有对应 RAW）",
                variable=self.kind_var,
                value="JPG",
                palette=self.palette,
                font=self.winfo_toplevel().font_body,
            ),
            RoundedRadiobutton(
                option_row,
                text="RAW（没有对应 JPG）",
                variable=self.kind_var,
                value="RAW",
                palette=self.palette,
                font=self.winfo_toplevel().font_body,
            ),
        ]
        self._kind_buttons[0].pack(side=tk.LEFT, padx=(8, 16))
        self._kind_buttons[1].pack(side=tk.LEFT)

        action_row = tk.Frame(workflow, background=self.palette["panel"])
        action_row.pack(fill=tk.X, pady=(10, 0))
        self.create_button(
            action_row,
            text="扫描并预览",
            command=self.preview,
            width=120,
        ).pack(side=tk.LEFT)
        self.create_button(
            action_row,
            text=f"移入{self.trash_name}",
            command=self.execute,
            role="danger",
            width=130,
        ).pack(side=tk.LEFT, padx=8)
        self.create_button(
            action_row,
            text="恢复最近一次清理",
            command=self.restore,
            width=164,
        ).pack(side=tk.LEFT)
        tk.Label(
            action_row,
            text="仅扫描当前文件夹",
            background=self.palette["panel"],
            foreground=self.palette["tertiary"],
            font=self.winfo_toplevel().font_caption,
        ).pack(side=tk.RIGHT, padx=(12, 0))

        self.stats_vars = self.create_stats(
            [
                ("total", "扫描照片"),
                ("raw", "RAW"),
                ("jpg", "JPG"),
                ("paired", "已有配对"),
                ("pending", "待清理"),
            ]
        )

        self.tree = ttk.Treeview(
            self.content,
            columns=("path", "missing"),
            show="headings",
        )
        self.tree.heading("path", text="待清理文件")
        self.tree.heading("missing", text="缺少配对")
        self.tree.column("path", width=600)
        self.tree.column("missing", width=100, anchor=tk.CENTER)
        RenamePage._pack_tree(self, self.tree)

    def preview(self) -> None:
        try:
            folder = self.require_folder(self.folder_var)
        except Exception as exc:
            messagebox.showwarning("提示", str(exc), parent=self)
            return
        kind = self.kind_var.get()
        self.run_job(
            f"正在查找没有配对的 {kind}…",
            lambda progress: core.scan_cleanup(
                folder,
                kind,
                recursive=False,
                progress=progress,
            ),
            self._show_items,
        )

    def _show_items(self, payload: object) -> None:
        result = payload
        assert isinstance(result, core.CleanupScanResult)
        self.items = result.items
        self.fill_tree(
            self.tree,
            [
                (_display_filename(item.path), item.missing_pair_kind)
                for item in self.items
            ],
        )
        self.update_stats(
            self.stats_vars,
            {
                "total": result.total_images,
                "raw": result.raw_count,
                "jpg": result.jpg_count,
                "paired": result.paired_target_count,
                "pending": len(result.items),
            },
        )
        self.show_stats()
        self.status_var.set(
            f"扫描 {result.total_images} 张照片；找到 {len(self.items)} 个待清理文件"
        )
        if not self.items:
            messagebox.showinfo("扫描完成", "所有照片都有对应的配对文件。", parent=self)

    def execute(self) -> None:
        if not self.items:
            messagebox.showwarning("提示", "请先扫描，没有待清理项目。", parent=self)
            return
        if not messagebox.askyesno(
            f"确认移入{self.trash_name}",
            f"将把 {len(self.items)} 个文件移入{self.trash_name}。\n\n"
            "不会永久删除，是否继续？",
            icon="warning",
            parent=self,
        ):
            return
        items = self.items.copy()
        self.begin_activity(self.tree, ("正在准备清理", "等待执行"))
        self.run_job(
            f"正在移入{self.trash_name}…",
            lambda progress: core.move_cleanup_items_to_trash(
                items,
                progress=progress,
            ),
            lambda payload: self._cleanup_finished(payload, items),
            on_progress=self._show_cleanup_activity,
        )

    def _show_cleanup_activity(
        self,
        current: int,
        total: int,
        message: str,
    ) -> None:
        state = "完成" if total > 0 and current >= total else f"{current}/{total}"
        self.append_activity(self.tree, (message, state))

    def _cleanup_finished(
        self,
        payload: object,
        items: list[core.CleanupItem],
    ) -> None:
        moved, errors = payload
        self.items = []
        failed_paths = {error.split("：", 1)[0] for error in errors}
        self.fill_tree(
            self.tree,
            [
                (
                    _display_filename(item.path),
                    "处理失败"
                    if item.path in failed_paths
                    else f"已移入{self.trash_name}",
                )
                for item in items
            ],
        )
        self.status_var.set(f"已移入{self.trash_name} {moved} 个文件")
        text = f"已移入{self.trash_name} {moved} 个文件。"
        if errors:
            text += f"\n\n有 {len(errors)} 个文件处理失败：\n" + "\n".join(errors[:8])
        messagebox.showinfo("清理完成", text, parent=self)

    def restore(self) -> None:
        if sys.platform == "darwin":
            confirmation = (
                "将优先通过隐藏安全备份恢复最近一次清理的文件。\n"
                "备份不可用时，macOS 可能询问是否允许控制 Finder。"
            )
        elif sys.platform == "win32":
            confirmation = (
                "将把最近一次清理的文件直接从 Windows 回收站还原到原位置。\n"
                "如果回收站已被清空，对应文件将无法恢复。"
            )
        else:
            confirmation = "将通过隐藏安全备份恢复最近一次清理的文件，是否继续？"
        if not messagebox.askyesno(
            "确认恢复",
            confirmation,
            parent=self,
        ):
            return
        self.begin_activity(self.tree, ("正在读取清理记录", "等待恢复"))
        self.run_job(
            f"正在从{self.trash_name}恢复…",
            lambda progress: core.restore_latest_cleanup(progress=progress),
            self._restore_finished,
            on_progress=self._show_cleanup_activity,
        )

    def _restore_finished(self, payload: object) -> None:
        restored, errors = payload
        self.append_activity(
            self.tree,
            (f"已恢复 {restored} 个文件", "恢复完成" if not errors else "部分失败"),
        )
        self.status_var.set(f"已恢复 {restored} 个文件")
        text = f"已恢复 {restored} 个文件。"
        if restored:
            if sys.platform == "win32":
                text += "\n\n文件已从 Windows 回收站移回原位置。"
            else:
                text += "\n\n废纸篓中可能仍保留同一文件的安全副本，确认照片正常后可照常清空废纸篓。"
        if errors:
            text += f"\n\n有 {len(errors)} 个文件未恢复：\n" + "\n".join(errors[:8])
        messagebox.showinfo("恢复结果", text, parent=self)


class SyncPage(BasePage):
    """Adobe Bridge 星标与颜色标签同步页面。"""

    def __init__(
        self,
        master: tk.Misc,
        folder_var: tk.StringVar | None = None,
    ) -> None:
        super().__init__(master)
        self.operations: list[core.SyncOperation] = []
        self.folder_var = (
            folder_var if folder_var is not None else tk.StringVar(master=self)
        )
        self.direction_var = tk.StringVar(value="JPG → RAW")
        self.rating_var = tk.BooleanVar(value=True)
        self.label_var = tk.BooleanVar(value=True)

        ttk.Label(self.content, text="星标与颜色标签同步", style="PageTitle.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            self.content,
            text="在同名 JPG 与 RAW 之间同步 Adobe Bridge XMP 标记；RAW 永远只写入侧车文件。",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(5, 16))

        workflow = self.create_workflow_panel(height=164)
        folder_row = tk.Frame(workflow, background=self.palette["panel"])
        folder_row.pack(fill=tk.X)
        tk.Label(
            folder_row,
            text="照片文件夹",
            width=10,
            anchor=tk.W,
            background=self.palette["panel"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_body_medium,
        ).pack(side=tk.LEFT)
        RoundedEntry(
            folder_row,
            textvariable=self.folder_var,
            palette=self.palette,
            font=self.winfo_toplevel().font_body,
        ).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
        )
        self.create_button(
            folder_row,
            text="选择文件夹…",
            command=lambda: self.choose_folder(self.folder_var),
            width=132,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.create_divider(workflow)
        option_row = tk.Frame(workflow, background=self.palette["panel"])
        option_row.pack(fill=tk.X)
        tk.Label(
            option_row,
            text="同步方向",
            width=10,
            anchor=tk.W,
            background=self.palette["panel"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_body_medium,
        ).pack(side=tk.LEFT)
        RoundedSelect(
            option_row,
            textvariable=self.direction_var,
            values=("JPG → RAW", "RAW → JPG"),
            palette=self.palette,
            font=self.winfo_toplevel().font_body,
            width=150,
        ).pack(side=tk.LEFT, padx=(6, 18))
        RoundedCheckbutton(
            option_row,
            text="同步星标",
            variable=self.rating_var,
            palette=self.palette,
            font=self.winfo_toplevel().font_body,
        ).pack(
            side=tk.LEFT
        )
        RoundedCheckbutton(
            option_row,
            text="同步颜色标签",
            variable=self.label_var,
            palette=self.palette,
            font=self.winfo_toplevel().font_body,
        ).pack(
            side=tk.LEFT,
            padx=(12, 0),
        )

        action_row = tk.Frame(workflow, background=self.palette["panel"])
        action_row.pack(fill=tk.X, pady=(10, 0))
        self.create_button(
            action_row,
            text="扫描并预览",
            command=self.preview,
            width=120,
        ).pack(side=tk.LEFT)
        self.create_button(
            action_row,
            text="执行同步",
            command=self.execute,
            role="primary",
            width=120,
        ).pack(side=tk.LEFT, padx=8)
        self.create_button(
            action_row,
            text="撤回最近一次同步",
            command=self.undo,
            width=164,
        ).pack(side=tk.LEFT)
        tk.Label(
            action_row,
            text="仅扫描当前文件夹",
            background=self.palette["panel"],
            foreground=self.palette["tertiary"],
            font=self.winfo_toplevel().font_caption,
        ).pack(side=tk.RIGHT, padx=(12, 0))

        self.stats_vars = self.create_stats(
            [
                ("total", "扫描照片"),
                ("source", "来源文件"),
                ("matched", "成功匹配"),
                ("marked", "带标记"),
                ("pending", "待同步"),
            ]
        )

        columns = ("source", "target", "rating", "label")
        self.tree = ttk.Treeview(self.content, columns=columns, show="headings")
        self.tree.heading("source", text="来源")
        self.tree.heading("target", text="目标")
        self.tree.heading("rating", text="星标变化")
        self.tree.heading("label", text="标签变化")
        self.tree.column("source", width=250)
        self.tree.column("target", width=250)
        self.tree.column("rating", width=100, anchor=tk.CENTER)
        self.tree.column("label", width=140, anchor=tk.CENTER)
        RenamePage._pack_tree(self, self.tree)

    def preview(self) -> None:
        try:
            folder = self.require_folder(self.folder_var)
            if not self.rating_var.get() and not self.label_var.get():
                raise ValueError("请至少选择“同步星标”或“同步颜色标签”。")
        except Exception as exc:
            messagebox.showwarning("提示", str(exc), parent=self)
            return
        direction = self.direction_var.get()
        sync_rating = self.rating_var.get()
        sync_label = self.label_var.get()
        self.run_job(
            "正在读取 XMP 标记并生成预览…",
            lambda progress: core.scan_sync(
                folder,
                direction,
                sync_rating,
                sync_label,
                recursive=False,
                progress=progress,
            ),
            self._show_operations,
        )

    def _show_operations(self, payload: object) -> None:
        result = payload
        assert isinstance(result, core.SyncScanResult)
        self.operations = result.operations
        rows = []
        for operation in self.operations:
            rating_text = (
                f"{operation.old_rating} → {operation.rating}"
                if operation.rating is not None and operation.old_rating != operation.rating
                else "不修改"
            )
            label_text = (
                f"{core.describe_label(operation.old_label)} → {core.describe_label(operation.label)}"
                if operation.label is not None and operation.old_label != operation.label
                else "不修改"
            )
            rows.append(
                (
                    _display_filename(operation.source),
                    _display_filename(operation.target),
                    rating_text,
                    label_text,
                )
            )
        self.fill_tree(self.tree, rows)
        self.update_stats(
            self.stats_vars,
            {
                "total": result.total_images,
                "source": result.source_count,
                "matched": result.matched_count,
                "marked": result.marked_count,
                "pending": len(result.operations),
            },
        )
        self.show_stats()
        self.status_var.set(
            f"扫描 {result.total_images} 张照片；找到 {len(self.operations)} 组需要同步"
        )
        if not self.operations:
            messagebox.showinfo("扫描完成", "没有需要同步的匹配照片。", parent=self)

    def execute(self) -> None:
        if not self.operations:
            messagebox.showwarning("提示", "请先扫描，没有待同步项目。", parent=self)
            return
        target_kind = "RAW 侧车" if self.direction_var.get() == "JPG → RAW" else "JPG"
        if not messagebox.askyesno(
            "确认同步",
            f"将修改 {len(self.operations)} 个{target_kind}文件。\n"
            "修改前会保留完整备份，是否继续？",
            parent=self,
        ):
            return
        operations = self.operations.copy()
        self.begin_activity(self.tree, ("正在准备同步", "", "", "等待执行"))
        self.run_job(
            "正在备份并同步 XMP 标记…",
            lambda progress: core.execute_sync_plan(
                operations,
                progress=progress,
            ),
            lambda payload: self._sync_finished(payload, operations),
            on_progress=self._show_sync_activity,
        )

    def _show_sync_activity(
        self,
        current: int,
        total: int,
        message: str,
    ) -> None:
        state = "完成" if total > 0 and current >= total else f"{current}/{total}"
        self.append_activity(self.tree, (message, "", "", state))

    def _sync_finished(
        self,
        payload: object,
        operations: list[core.SyncOperation],
    ) -> None:
        count, manifest = payload
        self.operations = []
        rows = []
        for operation in operations:
            rating_text = (
                f"{operation.old_rating} → {operation.rating}"
                if operation.rating is not None and operation.old_rating != operation.rating
                else "不修改"
            )
            label_text = (
                f"{core.describe_label(operation.old_label)} → "
                f"{core.describe_label(operation.label)} · 已同步"
                if operation.label is not None and operation.old_label != operation.label
                else "已同步"
            )
            rows.append(
                (
                    _display_filename(operation.source),
                    _display_filename(operation.target),
                    rating_text,
                    label_text,
                )
            )
        self.fill_tree(self.tree, rows)
        self.status_var.set(f"已同步 {count} 组照片")
        messagebox.showinfo(
            "同步完成",
            f"已同步 {count} 组照片。\n完整备份：{manifest.parent}",
            parent=self,
        )

    def undo(self) -> None:
        if not messagebox.askyesno(
            "确认撤回",
            "将使用完整备份恢复最近一次 XMP 同步，是否继续？",
            parent=self,
        ):
            return
        self.begin_activity(self.tree, ("正在读取同步备份", "", "", "等待恢复"))
        self.run_job(
            "正在恢复 XMP 备份…",
            lambda progress: core.undo_latest_sync(progress=progress),
            self._sync_undo_finished,
            on_progress=self._show_sync_activity,
        )

    def _sync_undo_finished(self, payload: object) -> None:
        value = int(payload)
        self.append_activity(
            self.tree,
            (f"已恢复 {value} 个目标文件", "", "", "撤回完成"),
        )
        self.status_var.set(f"已恢复 {value} 个目标文件")
        messagebox.showinfo(
            "撤回完成",
            f"已恢复 {value} 个目标文件。",
            parent=self,
        )


class KeywordQuickCutPage(ttk.Frame):
    """在工具集当前页面内承载 SwiftUI 关键词快切工作区。"""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=0, style="Page.TFrame")
        self.palette = self.winfo_toplevel().palette
        self.library_path = _resolve_keyword_quickcut_library()
        self.is_available, support_message = _keyword_quickcut_support(
            self.library_path
        )
        library = (
            _load_keyword_quickcut_library(self.library_path)
            if self.is_available
            else None
        )
        self.bridge = KeywordQuickCutBridge(library) if library is not None else None
        if self.is_available and self.bridge is None:
            self.is_available = False
            support_message = "关键词快切内嵌组件加载失败，请重新安装完整版本。"

        self._active = False
        self._resize_job: str | None = None
        self.host = tk.Frame(self, background=self.palette["window"], borderwidth=0)
        self.host.pack(fill=tk.BOTH, expand=True)
        self.content = self.host
        self.support_var = tk.StringVar(value=support_message)

        if self.is_available:
            self.loading_label = tk.Label(
                self.host,
                text="正在载入关键词快切工作区…",
                background=self.palette["window"],
                foreground=self.palette["secondary"],
                font=self.winfo_toplevel().font_body_medium,
            )
            self.loading_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            self._build_unavailable_state()

        self.host.bind("<Configure>", self._schedule_native_sync, add="+")

    def _build_unavailable_state(self) -> None:
        panel = tk.Frame(self.host, background=self.palette["panel"], padx=28, pady=24)
        panel.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        tk.Label(
            panel,
            text="关键词快切暂不可用",
            background=self.palette["panel"],
            foreground=self.palette["text"],
            font=self.winfo_toplevel().font_page_title,
        ).pack()
        tk.Label(
            panel,
            textvariable=self.support_var,
            background=self.palette["panel"],
            foreground=self.palette["warning"],
            font=self.winfo_toplevel().font_body,
            wraplength=520,
            justify=tk.CENTER,
        ).pack(pady=(10, 0))

    def activate(self) -> None:
        """页面被选中后显示原生工作区，并同步承载区域。"""

        self._active = True
        self._schedule_native_sync()

    def deactivate(self) -> None:
        """离开页面时隐藏原生视图，避免遮挡其他 Tk 页面。"""

        self._active = False
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except tk.TclError:
                pass
            self._resize_job = None
        if self.bridge is not None:
            self.bridge.set_visible(False)

    def _schedule_native_sync(self, _event: tk.Event | None = None) -> None:
        if not self._active or self.bridge is None:
            return
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except tk.TclError:
                pass
        self._resize_job = self.after(16, self._sync_native_view)

    def _sync_native_view(self) -> None:
        self._resize_job = None
        if not self._active or self.bridge is None or not self.winfo_exists():
            return
        self.update_idletasks()
        width = self.host.winfo_width()
        height = self.host.winfo_height()
        if width < 2 or height < 2:
            self._resize_job = self.after(50, self._sync_native_view)
            return
        root = self.winfo_toplevel()
        x = self.host.winfo_rootx() - root.winfo_rootx()
        y = self.host.winfo_rooty() - root.winfo_rooty()
        try:
            attached = self.bridge.attach(root.title(), x, y, width, height)
            if attached:
                self.bridge.set_theme(root.skin_id)
        except (OSError, ValueError, AttributeError):
            attached = False
        if attached:
            self.loading_label.place_forget()
            return
        self.support_var.set("无法把关键词工作区挂载到当前窗口，请重新启动应用。")
        self.is_available = False
        self.bridge = None
        self.loading_label.place_forget()
        self._build_unavailable_state()

    def is_busy(self) -> bool:
        return self.bridge.is_busy() if self.bridge is not None else False

    def cancel_current_operation(self) -> None:
        if self.bridge is not None:
            self.bridge.cancel()

    def dispose(self) -> None:
        """同步释放原生视图，供换肤重建和应用退出使用。"""

        self.deactivate()
        if self.bridge is not None:
            self.bridge.destroy()
            self.bridge = None


class PhotoAssistantApp(tk.Tk):
    """应用主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.skin_id = self._load_ui_config()
        self.dark_mode = self.skin_id != "editorial_minimal"
        self.palette = SKIN_PALETTES[self.skin_id]
        self.native_glass_active = (
            self.skin_id in GLASS_SKIN_IDS
            and _load_native_vibrancy_library() is not None
        )
        self.surface_background = (
            "systemTransparent"
            if self.native_glass_active
            else self.palette["surface"]
        )
        self._config_save_job: str | None = None
        self._appearance_window: tk.Toplevel | None = None
        self._sidebar_compact: bool | None = None
        self.pending_skin_var: tk.StringVar | None = None
        # 三个工具共用同一照片文件夹路径，切换页面时无需重复选择。
        self.shared_folder_var = tk.StringVar(master=self)

        self._available_fonts = tuple(tkfont.families(self))
        self.font_family = self._select_ui_font(self._available_fonts, sys.platform)
        self._configure_font_tokens()

        self.title(WINDOW_TITLE)
        initial_width, initial_height = self._fit_initial_window_size(
            self.winfo_screenwidth(),
            self.winfo_screenheight(),
        )
        self._initial_window_width = initial_width
        self.geometry(f"{initial_width}x{initial_height}")
        self.minsize(1300, 760)
        self.configure(
            background=(
                "systemTransparent"
                if self.native_glass_active
                else self.palette["window"]
            )
        )
        self._set_icon()
        self._configure_styles()
        self._build_ui()
        self.bind("<Configure>", self._on_root_configure, add="+")
        self.attributes("-alpha", 1.0)
        if self.native_glass_active:
            self.after_idle(lambda: _set_native_vibrancy(self, True))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    @staticmethod
    def _select_ui_font(
        available_families: tuple[str, ...],
        platform: str,
    ) -> str:
        """优先选择设计字体，并按平台回退到清晰的中文字体。"""

        available = {family.casefold(): family for family in available_families}
        design_fonts = ("Manrope", "Geist", "Noto Sans SC", "Noto Sans CJK SC")
        if platform == "win32":
            fallbacks = ("Microsoft YaHei UI", "Segoe UI Variable", "Segoe UI")
            default = "Microsoft YaHei UI"
        elif platform == "darwin":
            fallbacks = ("PingFang SC", "SF Pro Text", "Helvetica Neue")
            default = "PingFang SC"
        else:
            fallbacks = ("Noto Sans", "DejaVu Sans")
            default = "Noto Sans"
        for candidate in design_fonts + fallbacks:
            if candidate.casefold() in available:
                return available[candidate.casefold()]
        return default

    def _configure_font_tokens(self) -> None:
        """按皮肤选择标题字体，正文继续使用稳定的跨平台字体。"""

        available = {family.casefold(): family for family in self._available_fonts}
        display_font = self.font_family
        if self.skin_id == "editorial_minimal":
            for candidate in ("Songti SC", "STSong", "New York", "Georgia"):
                if candidate.casefold() in available:
                    display_font = available[candidate.casefold()]
                    break
        elif self.skin_id == "bento_modular":
            for candidate in ("Avenir Next", "Avenir", "PingFang SC"):
                if candidate.casefold() in available:
                    display_font = available[candidate.casefold()]
                    break
        elif self.skin_id == "soft_3d":
            for candidate in ("SF Pro Rounded", "Arial Rounded MT Bold", "PingFang SC"):
                if candidate.casefold() in available:
                    display_font = available[candidate.casefold()]
                    break

        text_font = self.font_family
        self.font_title = (display_font, 15, "bold")
        self.font_page_title = (display_font, 22, "bold")
        self.font_body = (text_font, 12)
        self.font_body_medium = (text_font, 12, "bold")
        self.font_caption = (text_font, 11)
        self.font_sidebar_section = (text_font, 10, "bold")
        self.font_stat_value = (display_font, 22, "bold")

    @staticmethod
    def _fit_initial_window_size(
        screen_width: int,
        screen_height: int,
    ) -> tuple[int, int]:
        """在小屏幕上缩小初始窗口，避免被任务栏或屏幕边缘遮挡。"""

        width = max(1300, min(1440, screen_width - 48))
        height = max(760, min(900, screen_height - 88))
        return width, height

    def _set_icon(self) -> None:
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "app_icon.png"
        if icon_path.exists():
            try:
                self._icon_image = tk.PhotoImage(file=str(icon_path))
                self.iconphoto(True, self._icon_image)
            except tk.TclError:
                pass

    @staticmethod
    def _load_ui_config() -> str:
        """读取皮肤配置；旧版透明度字段会被主动忽略。"""

        for config_path in (UI_CONFIG_FILE, *LEGACY_UI_CONFIG_FILES):
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                skin_id = str(data.get("skin", DEFAULT_SKIN_ID))
                if skin_id not in SKIN_PALETTES:
                    skin_id = DEFAULT_SKIN_ID
                return skin_id
            except Exception:
                continue
        return DEFAULT_SKIN_ID

    def _save_ui_config(self) -> None:
        """原子保存外观配置。"""

        if self._config_save_job is not None:
            try:
                self.after_cancel(self._config_save_job)
            except tk.TclError:
                pass
            self._config_save_job = None
        try:
            UI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            temporary = UI_CONFIG_FILE.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(
                    {"skin": self.skin_id},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary.replace(UI_CONFIG_FILE)
        except OSError:
            # 外观配置写入失败不应影响照片处理功能。
            pass

    def _schedule_config_save(self) -> None:
        if self._config_save_job is not None:
            self.after_cancel(self._config_save_job)
        self._config_save_job = self.after(250, self._save_ui_config)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        palette = self.palette
        surface = self.surface_background

        style.configure(".", font=self.font_body)
        style.configure("TFrame", background=surface)
        style.configure("Page.TFrame", background=surface)
        style.configure("Panel.TFrame", background=palette["panel"])
        style.configure("TLabel", background=surface, foreground=palette["text"])
        style.configure(
            "Panel.TLabel",
            background=palette["panel"],
            foreground=palette["text"],
        )
        style.configure(
            "Muted.TLabel",
            background=surface,
            foreground=palette["secondary"],
        )
        style.configure(
            "PageTitle.TLabel",
            font=self.font_page_title,
            background=surface,
            foreground=palette["title"],
        )
        style.configure(
            "TButton",
            padding=(14, 8),
            font=self.font_body_medium,
            background=palette["panel_alt"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["panel_alt"],
            darkcolor=palette["border"],
            relief=tk.FLAT,
        )
        style.map(
            "TButton",
            background=[
                ("pressed", palette["border"]),
                ("active", palette["border"]),
                ("disabled", palette["surface"]),
            ],
            foreground=[("disabled", palette["tertiary"])],
        )
        style.configure("Header.TButton", padding=(12, 7), font=self.font_caption)
        style.configure(
            "TEntry",
            padding=(10, 8),
            background=palette["panel"],
            fieldbackground=palette["panel"],
            foreground=palette["text"],
            insertcolor=palette["text"],
            selectbackground=palette["selection"],
            selectforeground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
            borderwidth=1,
        )
        style.configure(
            "TCombobox",
            padding=(8, 6),
            background=palette["panel"],
            fieldbackground=palette["panel"],
            foreground=palette["text"],
            arrowcolor=palette["secondary"],
            selectbackground=palette["selection"],
            selectforeground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
        )
        style.configure(
            "TCheckbutton",
            background=palette["panel"],
            foreground=palette["text"],
            indicatorcolor=palette["panel_alt"],
            focuscolor=palette["accent"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", palette["panel"])],
            foreground=[("disabled", palette["tertiary"])],
            indicatorcolor=[
                ("selected", palette["accent"]),
                ("active", palette["accent_soft"]),
            ],
        )
        style.configure(
            "TRadiobutton",
            background=palette["panel"],
            foreground=palette["text"],
            indicatorcolor=palette["panel_alt"],
            focuscolor=palette["accent"],
        )
        style.map(
            "TRadiobutton",
            background=[("active", palette["panel"])],
            foreground=[("disabled", palette["tertiary"])],
            indicatorcolor=[
                ("selected", palette["accent"]),
                ("active", palette["accent_soft"]),
            ],
        )
        style.configure(
            "Accent.TButton",
            foreground=palette.get("accent_text", "#FFFFFF"),
            background=palette["accent"],
            bordercolor=palette["accent"],
            lightcolor=palette["accent"],
            darkcolor=palette["accent"],
        )
        style.map(
            "Accent.TButton",
            background=[
                ("pressed", palette["accent_active"]),
                ("active", palette["accent_active"]),
                ("disabled", palette["surface"]),
            ],
            foreground=[
                ("disabled", palette["tertiary"]),
                ("active", palette.get("accent_text", "#FFFFFF")),
            ],
        )
        style.configure(
            "Danger.TButton",
            foreground=palette["danger"],
            background=palette["panel_alt"],
            bordercolor=palette["border"],
            lightcolor=palette["panel_alt"],
            darkcolor=palette["border"],
        )
        style.map(
            "Danger.TButton",
            background=[
                ("pressed", palette["danger_soft"]),
                ("active", palette["danger_soft"]),
            ],
            foreground=[
                ("disabled", palette["tertiary"]),
                ("active", palette["danger_active"]),
            ],
        )
        style.configure(
            "Treeview",
            rowheight=33,
            background=palette["panel"],
            fieldbackground=palette["panel"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
            borderwidth=0,
            relief=tk.FLAT,
        )
        style.map(
            "Treeview",
            background=[("selected", palette["selection"])],
            foreground=[("selected", palette["text"])],
        )
        style.configure(
            "Treeview.Heading",
            font=self.font_body_medium,
            background=palette["panel_alt"],
            foreground=palette["secondary"],
            bordercolor=palette["border"],
            lightcolor=palette["panel_alt"],
            darkcolor=palette["panel_alt"],
            relief=tk.FLAT,
            padding=(10, 8),
        )
        style.configure(
            "Hidden.TNotebook",
            background=surface,
            borderwidth=0,
            bordercolor=surface,
            lightcolor=surface,
            darkcolor=surface,
            relief=tk.FLAT,
            tabmargins=0,
        )
        style.layout("Hidden.TNotebook.Tab", [])
        style.configure(
            "Segment.TButton",
            font=self.font_body_medium,
            padding=(12, 9),
            background=palette["panel_alt"],
            foreground=palette["secondary"],
            bordercolor=palette["panel_alt"],
            lightcolor=palette["panel_alt"],
            darkcolor=palette["panel_alt"],
        )
        style.map(
            "Segment.TButton",
            background=[
                ("pressed", palette["border"]),
                ("active", palette["border"]),
            ],
            foreground=[
                ("pressed", palette["text"]),
                ("active", palette["text"]),
            ],
        )
        style.configure(
            "SelectedSegment.TButton",
            font=self.font_body_medium,
            padding=(12, 9),
            background=palette["panel"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["panel"],
            darkcolor=palette["border"],
        )
        style.map(
            "SelectedSegment.TButton",
            background=[
                ("pressed", palette["panel"]),
                ("active", palette["panel"]),
            ],
            foreground=[("active", palette["text"])],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=palette["panel_alt"],
            troughcolor=palette["panel"],
            bordercolor=palette["border"],
            lightcolor=palette["panel_alt"],
            darkcolor=palette["border"],
            arrowcolor=palette["secondary"],
            borderwidth=0,
            relief=tk.FLAT,
        )
        style.configure(
            "TScrollbar",
            background=palette["panel_alt"],
            troughcolor=palette["panel"],
            bordercolor=palette["border"],
            lightcolor=palette["panel_alt"],
            darkcolor=palette["border"],
            arrowcolor=palette["secondary"],
            borderwidth=0,
            relief=tk.FLAT,
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=palette["accent"],
            troughcolor=palette["panel_alt"],
            borderwidth=0,
            thickness=5,
        )
    def _build_ui(self) -> None:
        palette = self.palette
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        sidebar = tk.Frame(
            self,
            background=palette["chrome"],
            width=SIDEBAR_EXPANDED_WIDTH,
            borderwidth=0,
        )
        sidebar.grid(row=0, column=0, sticky=tk.NS)
        # 侧栏内部使用 pack，关闭几何传播才能严格遵守响应式宽度。
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

        brand = tk.Frame(sidebar, background=palette["chrome"])
        brand.pack(fill=tk.X, padx=14, pady=(20, 14))
        assets_dir = Path(__file__).resolve().parent.parent / "assets"
        icon_path = assets_dir / "app_icon_header.png"
        if icon_path.exists():
            try:
                # 继续使用高质量缩放资源，避免 Tk 整数抽样造成模糊。
                self._header_icon = tk.PhotoImage(file=str(icon_path))
                self._brand_icon_label = tk.Label(
                    brand,
                    image=self._header_icon,
                    background=palette["chrome"],
                )
                self._brand_icon_label.pack(anchor=tk.CENTER)
            except tk.TclError:
                pass

        self._brand_title_label = tk.Label(
            brand,
            text=WINDOW_TITLE,
            background=palette["chrome"],
            foreground=palette["text"],
            font=self.font_title,
        )
        self._brand_title_label.pack(anchor=tk.CENTER, pady=(8, 0))
        self._brand_subtitle_label = tk.Label(
            brand,
            text="照片整理 · 本地处理",
            background=palette["chrome"],
            foreground=palette["secondary"],
            font=self.font_caption,
        )
        self._brand_subtitle_label.pack(anchor=tk.CENTER, pady=(4, 0))

        self._nav_section_label = tk.Label(
            sidebar,
            text="工具",
            background=palette["chrome"],
            foreground=palette["tertiary"],
            font=self.font_sidebar_section,
            anchor=tk.W,
        )
        self._nav_section_label.pack(fill=tk.X, padx=18, pady=(6, 8))

        nav_container = tk.Frame(sidebar, background=palette["chrome"])
        nav_container.pack(fill=tk.X)
        self._nav_container = nav_container
        self._nav_buttons: list[SidebarNavButton] = []
        nav_items = (
            ("时间重命名", "rename"),
            ("配对清理", "cleanup"),
            ("星标与颜色同步", "sync"),
            ("关键词快切", "quickcut"),
        )
        for index, (label, icon) in enumerate(nav_items):
            button = SidebarNavButton(
                nav_container,
                text=label,
                icon=icon,
                command=lambda selected=index: self._select_page(selected),
                palette=palette,
                font=self.font_body_medium,
            )
            button.set_selected(index == 0)
            button.pack(fill=tk.X, padx=14, pady=3)
            self._nav_buttons.append(button)
        # 保留旧的私有别名，避免依赖旧导航名称的测试或扩展失效。
        self._tab_buttons = self._nav_buttons

        sidebar_bottom = tk.Frame(sidebar, background=palette["chrome"])
        sidebar_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(12, 16))
        self._sidebar_bottom = sidebar_bottom

        self.appearance_button = RoundedButton(
            sidebar_bottom,
            text="外观…",
            command=self.open_appearance_settings,
            palette=palette,
            font=self.font_body_medium,
            width=180,
            height=40,
            radius=12,
            background=palette["chrome"],
        )
        self.appearance_button.pack(fill=tk.X)
        self._version_label = tk.Label(
            sidebar_bottom,
            text=f"v{__version__}",
            background=palette["chrome"],
            foreground=palette["tertiary"],
            font=self.font_caption,
        )
        self._version_label.pack(pady=(9, 0))

        tk.Frame(self, width=1, background=palette["border"]).grid(
            row=0,
            column=0,
            sticky="nse",
        )

        main_area = tk.Frame(self, background=self.surface_background, borderwidth=0)
        main_area.grid(row=0, column=1, sticky=tk.NSEW)
        self.main_area = main_area

        notebook = ttk.Notebook(main_area, style="Hidden.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True)
        notebook.add(
            RenamePage(notebook, self.shared_folder_var),
            text="  时间重命名  ",
        )
        notebook.add(
            CleanupPage(notebook, self.shared_folder_var),
            text="  配对清理  ",
        )
        notebook.add(
            SyncPage(notebook, self.shared_folder_var),
            text="  星标与颜色同步  ",
        )
        quickcut_page = KeywordQuickCutPage(notebook)
        notebook.add(quickcut_page, text="  关键词快切  ")
        self.quickcut_page = quickcut_page
        self.notebook = notebook
        notebook.bind("<<NotebookTabChanged>>", self._sync_tab_styles)
        current_width = self.winfo_width()
        self._apply_sidebar_layout(
            current_width if current_width > 1 else self._initial_window_width
        )

    @staticmethod
    def _sidebar_width_for(window_width: int) -> int:
        """按主窗口总宽度返回侧栏宽度。"""

        if window_width >= SIDEBAR_BREAKPOINT:
            return SIDEBAR_EXPANDED_WIDTH
        return SIDEBAR_COMPACT_WIDTH

    def _on_root_configure(self, event: tk.Event) -> None:
        """只在跨越响应式断点时重排侧栏，避免连续缩放时闪烁。"""

        if event.widget is not self:
            return
        self._apply_sidebar_layout(event.width)

    def _apply_sidebar_layout(self, window_width: int) -> None:
        width = self._sidebar_width_for(window_width)
        compact = width == SIDEBAR_COMPACT_WIDTH
        if self._sidebar_compact == compact:
            return
        self._sidebar_compact = compact
        self.sidebar.configure(width=width)
        side_padding = 8 if compact else 14
        nav_label_padding = 12 if compact else 18
        for button in self._nav_buttons:
            button.pack_configure(padx=side_padding)
        self._nav_section_label.pack_configure(padx=nav_label_padding)
        self._sidebar_bottom.pack_configure(padx=side_padding)
        page_padding = (16, 18) if compact else (28, 22)
        for page in self.notebook.winfo_children():
            page.configure(
                padding=0 if isinstance(page, KeywordQuickCutPage) else page_padding
            )

        if compact:
            self._brand_subtitle_label.pack_forget()
        else:
            self._brand_subtitle_label.pack(anchor=tk.CENTER, pady=(4, 0))

    def _select_page(self, index: int) -> None:
        """通过左侧导航切换原有三个功能页。"""

        if self.notebook.index(self.notebook.select()) == index:
            return
        self.notebook.select(index)
        self._sync_tab_styles()
        # 点击事件返回前完成当前页面布局，避免短暂显示空白面板。
        self.notebook.update_idletasks()

    def _sync_tab_styles(self, _event: tk.Event | None = None) -> None:
        """让侧栏导航的选中状态与 Notebook 页面保持一致。"""

        selected = self.notebook.index(self.notebook.select())
        for index, button in enumerate(self._tab_buttons):
            button.set_selected(index == selected)
        for index, page in enumerate(self.notebook.winfo_children()):
            if isinstance(page, KeywordQuickCutPage):
                if index == selected:
                    page.activate()
                else:
                    page.deactivate()

    def _has_busy_jobs(self) -> bool:
        """换肤前确认所有页面后台任务已经结束。"""

        python_busy = any(
            page._busy
            for page in self.notebook.winfo_children()
            if isinstance(page, BasePage)
        )
        native_busy = any(
            page.is_busy()
            for page in self.notebook.winfo_children()
            if isinstance(page, KeywordQuickCutPage)
        )
        return python_busy or native_busy

    def _dispose_keyword_quickcut_pages(self) -> None:
        """在 Tk 页面被销毁前释放其上方的原生 SwiftUI 视图。"""

        for page in self.notebook.winfo_children():
            if isinstance(page, KeywordQuickCutPage):
                page.dispose()

    def _has_preview_results(self) -> bool:
        """检测会因界面重建而清空的表格预览或活动记录。"""

        for page in self.notebook.winfo_children():
            tree = getattr(page, "tree", None)
            if tree is not None and tree.winfo_exists() and tree.get_children():
                return True
        return False

    def _apply_pending_skin(self) -> None:
        if self.pending_skin_var is None:
            return
        target_skin = self.pending_skin_var.get()
        if target_skin == self.skin_id:
            if self._appearance_window is not None:
                self._appearance_window.destroy()
                self._appearance_window = None
            self.pending_skin_var = None
            return
        self._apply_skin(target_skin)

    def _apply_skin(
        self,
        skin_id: str,
        *,
        confirm_results: bool = True,
    ) -> bool:
        """在安全边界内保存并立即重建主界面。"""

        target_skin = skin_id if skin_id in SKIN_PALETTES else DEFAULT_SKIN_ID
        if target_skin == self.skin_id:
            return True
        if self._has_busy_jobs():
            messagebox.showwarning(
                "暂时无法切换皮肤",
                "当前有任务正在执行，请等待任务完成后再切换。",
                parent=self._appearance_window or self,
            )
            return False
        if self._has_preview_results() and confirm_results:
            if not messagebox.askyesno(
                "确认切换皮肤",
                "切换皮肤会重建界面，并清空当前扫描预览和临时列表。是否继续？",
                parent=self._appearance_window or self,
            ):
                return False

        selected_index = self.notebook.index(self.notebook.select())
        shared_folder = self.shared_folder_var.get()
        if self.native_glass_active:
            _set_native_vibrancy(self, False)
        if self._appearance_window is not None and self._appearance_window.winfo_exists():
            self._appearance_window.destroy()
        self._appearance_window = None
        self.pending_skin_var = None

        self._dispose_keyword_quickcut_pages()

        for child in list(self.winfo_children()):
            child.destroy()

        self.skin_id = target_skin
        self.dark_mode = target_skin != "editorial_minimal"
        self.palette = SKIN_PALETTES[target_skin]
        self._configure_font_tokens()
        self.native_glass_active = (
            target_skin in GLASS_SKIN_IDS
            and _load_native_vibrancy_library() is not None
        )
        self.surface_background = (
            "systemTransparent"
            if self.native_glass_active
            else self.palette["surface"]
        )
        self._sidebar_compact = None
        self.configure(
            background=(
                "systemTransparent"
                if self.native_glass_active
                else self.palette["window"]
            )
        )
        self._configure_styles()
        self._build_ui()
        self.shared_folder_var.set(shared_folder)
        safe_index = min(selected_index, len(self.notebook.tabs()) - 1)
        self.notebook.select(safe_index)
        self._sync_tab_styles()
        self.attributes("-alpha", 1.0)
        if self.native_glass_active:
            self.after_idle(lambda: _set_native_vibrancy(self, True))
        self._save_ui_config()
        self.update_idletasks()
        return True

    def open_appearance_settings(self) -> None:
        """打开只包含皮肤选择的外观设置弹窗。"""

        if self._appearance_window is not None and self._appearance_window.winfo_exists():
            self._appearance_window.lift()
            self._appearance_window.focus_force()
            return

        palette = self.palette
        window = tk.Toplevel(self)
        self._appearance_window = window
        window.title("外观设置")
        window.geometry("720x740")
        window.resizable(False, False)
        window.transient(self)
        appearance_background = (
            "systemTransparent"
            if self.native_glass_active
            else palette["window"]
        )
        window.configure(background=appearance_background)
        window.attributes("-alpha", 1.0)

        def close_window() -> None:
            if self.native_glass_active:
                _set_native_vibrancy(window, False)
            window.destroy()
            self._appearance_window = None
            self.pending_skin_var = None

        window.protocol("WM_DELETE_WINDOW", close_window)

        panel = RoundedPanel(
            window,
            fill=palette["panel"],
            outline=palette["border"],
            background=appearance_background,
            radius=20,
            height=704,
            padding=(22, 18),
        )
        panel.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        tk.Label(
            panel.body,
            text="外观皮肤",
            background=palette["panel"],
            foreground=palette["text"],
            font=self.font_body_medium,
            anchor=tk.W,
        ).pack(fill=tk.X)
        tk.Label(
            panel.body,
            text="选择一套工作区配色。窗口始终保持清晰不透明，应用后立即重建主界面。",
            background=palette["panel"],
            foreground=palette["secondary"],
            font=self.font_caption,
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(5, 10))

        self.pending_skin_var = tk.StringVar(master=window, value=self.skin_id)
        preview_grid = tk.Frame(panel.body, background=palette["panel"])
        preview_grid.pack(fill=tk.BOTH, expand=True)
        for index, skin_id in enumerate(SKIN_ORDER):
            row, column = divmod(index, 3)
            wrapper = tk.Frame(preview_grid, background=palette["panel"])
            wrapper.grid(
                row=row,
                column=column,
                sticky=tk.NSEW,
                padx=5,
                pady=5,
            )
            preview_grid.grid_columnconfigure(column, weight=1, uniform="skins")
            preview_grid.grid_rowconfigure(row, weight=1, uniform="skin_rows")
            SkinPreviewCard(
                wrapper,
                skin_id=skin_id,
                selected_var=self.pending_skin_var,
                font=self.font_caption,
                width=198,
                height=132,
            ).pack(fill=tk.X)
            _label, description = SKIN_LABELS[skin_id]
            tk.Label(
                wrapper,
                text=description,
                background=palette["panel"],
                foreground=palette["tertiary"],
                font=self.font_caption,
                anchor=tk.W,
                justify=tk.LEFT,
                wraplength=198,
            ).pack(fill=tk.X, pady=(4, 0))

        tk.Frame(
            panel.body,
            height=1,
            background=palette["border"],
        ).pack(fill=tk.X, pady=(8, 10))

        tk.Label(
            panel.body,
            text="提示：任务执行中不能换肤；已有扫描预览时会先请求确认。",
            background=palette["panel"],
            foreground=palette["warning"],
            font=self.font_caption,
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 8))

        button_row = tk.Frame(panel.body, background=palette["panel"])
        button_row.pack(fill=tk.X)
        RoundedButton(
            button_row,
            text="恢复默认皮肤",
            command=lambda: self.pending_skin_var.set(DEFAULT_SKIN_ID),
            palette=palette,
            font=self.font_body_medium,
            width=128,
        ).pack(side=tk.LEFT)
        RoundedButton(
            button_row,
            text="关闭",
            command=close_window,
            palette=palette,
            font=self.font_body_medium,
            width=88,
        ).pack(side=tk.RIGHT)
        RoundedButton(
            button_row,
            text="应用皮肤",
            command=self._apply_pending_skin,
            palette=palette,
            font=self.font_body_medium,
            role="primary",
            width=110,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        self.update_idletasks()
        if self.native_glass_active:
            window.after_idle(lambda: _set_native_vibrancy(window, True))
        x = self.winfo_rootx() + (self.winfo_width() - window.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - window.winfo_height()) // 2
        window.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _on_close(self) -> None:
        if self._config_save_job is not None:
            self.after_cancel(self._config_save_job)
            self._config_save_job = None
        self._save_ui_config()
        self._dispose_keyword_quickcut_pages()
        if self.native_glass_active:
            _set_native_vibrancy(self, False)
        self.destroy()


def run() -> None:
    """启动应用。"""

    _enable_windows_dpi_awareness()
    app = PhotoAssistantApp()
    app.mainloop()
