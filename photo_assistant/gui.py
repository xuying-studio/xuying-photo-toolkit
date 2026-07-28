"""旭影的摄影工具集 Tkinter 图形界面。"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Callable

from . import __version__
from . import core


WINDOW_TITLE = "旭影的摄影工具集"
LEGACY_WINDOW_TITLE = "摄影文件后期处理助手"
MAX_PREVIEW_ROWS = 1000
MAX_ACTIVITY_ROWS = 300
DEFAULT_OPACITY = 92
MIN_OPACITY = 70
MAX_OPACITY = 100
UI_CONFIG_FILE = (
    Path.home()
    / "Library"
    / "Application Support"
    / WINDOW_TITLE
    / "ui_config.json"
)
LEGACY_UI_CONFIG_FILE = (
    Path.home()
    / "Library"
    / "Application Support"
    / LEGACY_WINDOW_TITLE
    / "ui_config.json"
)

LIGHT_PALETTE = {
    "window": "#E8EBF0",
    "chrome": "#F8F9FB",
    "surface": "#F3F4F7",
    "panel": "#FBFCFD",
    "panel_alt": "#ECEFF3",
    "border": "#D7DBE2",
    "table_grid": "#C7CCD4",
    "text": "#202124",
    "secondary": "#686D76",
    "tertiary": "#90959E",
    "accent": "#0A7AF4",
    "accent_active": "#0069DC",
    "accent_soft": "#E3F0FF",
    "danger": "#C34852",
    "danger_active": "#A93A44",
    "danger_soft": "#F9EAEC",
    "selection": "#E4F0FF",
}

DARK_PALETTE = {
    "window": "#16171A",
    "chrome": "#24252A",
    "surface": "#202125",
    "panel": "#2D2E33",
    "panel_alt": "#36373D",
    "border": "#44464D",
    "table_grid": "#555861",
    "text": "#F4F4F6",
    "secondary": "#B4B7BF",
    "tertiary": "#858992",
    "accent": "#409CFF",
    "accent_active": "#64ADFF",
    "accent_soft": "#233F5E",
    "danger": "#E07A84",
    "danger_active": "#EE929A",
    "danger_soft": "#3C292E",
    "selection": "#233F5E",
}


def _display_filename(value: str | Path) -> str:
    """仅返回表格展示需要的文件名，内部路径保持不变。"""

    return Path(value).name or str(value)


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
        radius: int = 11,
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
        self._radius = radius
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
            cursor="pointinghand",
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
            return fill, "#FFFFFF", fill
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
        self._radius = 11
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
        self._radius = 11
        background = str(master.cget("background"))
        super().__init__(
            master,
            width=width,
            height=height,
            background=background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=1,
            cursor="pointinghand",
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
        menu = tk.Menu(self, tearoff=False)
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
            cursor="pointinghand",
        )
        self._variable.trace_add("write", lambda *_: self._draw())
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._toggle)
        self.bind("<Return>", self._toggle)
        self.bind("<space>", self._toggle)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._draw()

    def _toggle(self, _event: tk.Event | None = None) -> str:
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
            outline=palette["accent"] if checked or self._hovered else palette["border"],
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
                fill="#FFFFFF",
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
        self._radius = radius
        self._padding = padding
        self.body = tk.Frame(self, background=fill, borderwidth=0)
        self.body.place(x=padding[0], y=padding[1])
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event: tk.Event) -> None:
        width = max(2, event.width - 1)
        height = max(2, event.height - 1)
        self.delete("panel")
        self.create_polygon(
            _rounded_points(width, height, self._radius),
            smooth=True,
            splinesteps=24,
            fill=self._fill,
            outline=self._outline,
            width=1,
            tags="panel",
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
        self.stats_container: tk.Frame | None = None
        self.table_frame: tk.Misc | None = None
        self._tree_grid_lines: list[tk.Frame] = []

        self.content = ttk.Frame(self, style="Page.TFrame")

        footer = tk.Frame(self, background=self.palette["surface"])
        self.footer = footer
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(
            footer,
            textvariable=self.status_var,
            background=self.palette["surface"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_caption,
        ).pack(side=tk.LEFT)
        self.progress_text_var = tk.StringVar(value="0 / 0 · 0%")
        tk.Label(
            footer,
            textvariable=self.progress_text_var,
            background=self.palette["surface"],
            foreground=self.palette["secondary"],
            font=self.winfo_toplevel().font_caption,
        ).pack(side=tk.RIGHT)
        self.progress = RoundedProgressbar(
            footer,
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
            background=self.palette["surface"],
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
                background=self.palette["surface"],
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
            background=self.palette["surface"],
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
            text="扫描包含所有子文件夹",
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
        self.tree.column("source", width=400)
        self.tree.column("target", width=400)
        self.tree.column("kind", width=100, anchor=tk.CENTER)
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
            background=self.palette["surface"],
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
                recursive=True,
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

        ttk.Label(self.content, text="RAW / JPG 配对清理", style="PageTitle.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            self.content,
            text="递归检查同一文件夹内的同名照片；移入废纸篓前创建隐藏安全备份，恢复不依赖 Finder。",
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
        ttk.Radiobutton(
            option_row,
            text="JPG（没有对应 RAW）",
            variable=self.kind_var,
            value="JPG",
        ).pack(side=tk.LEFT, padx=(8, 16))
        ttk.Radiobutton(
            option_row,
            text="RAW（没有对应 JPG）",
            variable=self.kind_var,
            value="RAW",
        ).pack(side=tk.LEFT)

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
            text="移入废纸篓",
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
            text="扫描包含所有子文件夹",
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
        self.tree.column("path", width=780)
        self.tree.column("missing", width=110, anchor=tk.CENTER)
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
                recursive=True,
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
            "确认移入废纸篓",
            f"将把 {len(self.items)} 个文件移入废纸篓。\n\n"
            "不会永久删除，是否继续？",
            icon="warning",
            parent=self,
        ):
            return
        items = self.items.copy()
        self.begin_activity(self.tree, ("正在准备清理", "等待执行"))
        self.run_job(
            "正在移入废纸篓…",
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
                    "处理失败" if item.path in failed_paths else "已移入废纸篓",
                )
                for item in items
            ],
        )
        self.status_var.set(f"已移入废纸篓 {moved} 个文件")
        text = f"已移入废纸篓 {moved} 个文件。"
        if errors:
            text += f"\n\n有 {len(errors)} 个文件处理失败：\n" + "\n".join(errors[:8])
        messagebox.showinfo("清理完成", text, parent=self)

    def restore(self) -> None:
        if not messagebox.askyesno(
            "确认恢复",
            "将通过 Finder 尝试恢复最近一次清理的文件。\n"
            "macOS 可能会询问是否允许控制 Finder。",
            parent=self,
        ):
            return
        self.begin_activity(self.tree, ("正在读取清理记录", "等待恢复"))
        self.run_job(
            "正在从废纸篓恢复…",
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
            text="扫描包含所有子文件夹",
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
        self.tree.column("source", width=320)
        self.tree.column("target", width=320)
        self.tree.column("rating", width=110, anchor=tk.CENTER)
        self.tree.column("label", width=170, anchor=tk.CENTER)
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
                recursive=True,
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


class PhotoAssistantApp(tk.Tk):
    """应用主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.dark_mode = self._detect_dark_mode()
        self.palette = DARK_PALETTE if self.dark_mode else LIGHT_PALETTE
        self.opacity_percent = self._load_opacity()
        self._config_save_job: str | None = None
        self._appearance_window: tk.Toplevel | None = None
        self.opacity_var: tk.DoubleVar | None = None
        self.opacity_text_var: tk.StringVar | None = None
        # 三个工具共用同一照片文件夹路径，切换页面时无需重复选择。
        self.shared_folder_var = tk.StringVar(master=self)

        # SF Pro 使用可识别的字体族名称，中文字符由系统自动回退到苹方。
        self.font_title = ("SF Pro Display", 18, "bold")
        self.font_page_title = ("SF Pro Display", 21, "bold")
        self.font_body = ("SF Pro Text", 12)
        self.font_body_medium = ("SF Pro Text", 12, "bold")
        self.font_caption = ("SF Pro Text", 11)
        self.font_stat_value = ("SF Pro Display", 20, "bold")

        self.title(WINDOW_TITLE)
        self.geometry("1180x820")
        self.minsize(980, 680)
        self.configure(background=self.palette["window"])
        self._set_icon()
        self._configure_styles()
        self._build_ui()
        self._apply_opacity(self.opacity_percent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_icon(self) -> None:
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "app_icon.png"
        if icon_path.exists():
            try:
                self._icon_image = tk.PhotoImage(file=str(icon_path))
                self.iconphoto(True, self._icon_image)
            except tk.TclError:
                pass

    @staticmethod
    def _detect_dark_mode() -> bool:
        """启动时读取系统外观；读取失败时使用浅色模式。"""

        if sys.platform != "darwin":
            return False
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.stdout.strip().casefold() == "dark"
        except Exception:
            return False

    @staticmethod
    def _load_opacity() -> int:
        """读取并限制本地保存的透明度，兼容改名前的配置。"""

        value = DEFAULT_OPACITY
        for config_path in (UI_CONFIG_FILE, LEGACY_UI_CONFIG_FILE):
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                value = int(round(float(data.get("opacity", DEFAULT_OPACITY))))
                break
            except Exception:
                continue
        return max(MIN_OPACITY, min(MAX_OPACITY, value))

    def _save_ui_config(self) -> None:
        """原子保存外观配置。"""

        try:
            UI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            temporary = UI_CONFIG_FILE.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(
                    {"opacity": self.opacity_percent},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary.replace(UI_CONFIG_FILE)
        except OSError:
            # 外观配置写入失败不应影响照片处理功能。
            pass
        self._config_save_job = None

    def _schedule_config_save(self) -> None:
        if self._config_save_job is not None:
            self.after_cancel(self._config_save_job)
        self._config_save_job = self.after(250, self._save_ui_config)

    def _apply_opacity(self, percent: int | float) -> None:
        """实时应用窗口透明度，并同步外观弹窗。"""

        value = max(MIN_OPACITY, min(MAX_OPACITY, int(round(float(percent)))))
        self.opacity_percent = value
        try:
            self.attributes("-alpha", value / 100)
        except tk.TclError:
            pass
        if self.opacity_text_var is not None:
            self.opacity_text_var.set(f"{value}%")
        if self._appearance_window is not None and self._appearance_window.winfo_exists():
            try:
                self._appearance_window.attributes("-alpha", value / 100)
            except tk.TclError:
                pass

    def _on_opacity_change(self, value: str) -> None:
        self._apply_opacity(float(value))
        self._schedule_config_save()

    def _reset_opacity(self) -> None:
        if self.opacity_var is not None:
            self.opacity_var.set(DEFAULT_OPACITY)
        self._apply_opacity(DEFAULT_OPACITY)
        self._schedule_config_save()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        palette = self.palette

        style.configure(".", font=self.font_body)
        style.configure("TFrame", background=palette["surface"])
        style.configure("Page.TFrame", background=palette["surface"])
        style.configure("Panel.TFrame", background=palette["panel"])
        style.configure("TLabel", background=palette["surface"], foreground=palette["text"])
        style.configure(
            "Panel.TLabel",
            background=palette["panel"],
            foreground=palette["text"],
        )
        style.configure(
            "Muted.TLabel",
            background=palette["surface"],
            foreground=palette["secondary"],
        )
        style.configure(
            "PageTitle.TLabel",
            font=self.font_page_title,
            background=palette["surface"],
            foreground=palette["text"],
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
            fieldbackground=palette["panel"],
            foreground=palette["text"],
            insertcolor=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
            borderwidth=1,
        )
        style.configure(
            "TCombobox",
            padding=(8, 6),
            fieldbackground=palette["panel"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
        )
        style.configure(
            "TCheckbutton",
            background=palette["panel"],
            foreground=palette["text"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", palette["panel"])],
            foreground=[("disabled", palette["tertiary"])],
        )
        style.configure(
            "TRadiobutton",
            background=palette["panel"],
            foreground=palette["text"],
        )
        style.map(
            "TRadiobutton",
            background=[("active", palette["panel"])],
            foreground=[("disabled", palette["tertiary"])],
        )
        style.configure(
            "Accent.TButton",
            foreground="#FFFFFF",
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
                ("active", "#FFFFFF"),
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
            relief=tk.FLAT,
            padding=(10, 8),
        )
        style.configure(
            "Hidden.TNotebook",
            background=palette["surface"],
            borderwidth=0,
            bordercolor=palette["surface"],
            lightcolor=palette["surface"],
            darkcolor=palette["surface"],
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
            troughcolor=palette["surface"],
            bordercolor=palette["border"],
            lightcolor=palette["panel_alt"],
            darkcolor=palette["border"],
            arrowcolor=palette["secondary"],
        )
        style.configure(
            "TScrollbar",
            background=palette["panel_alt"],
            troughcolor=palette["surface"],
            bordercolor=palette["border"],
            lightcolor=palette["panel_alt"],
            darkcolor=palette["border"],
            arrowcolor=palette["secondary"],
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
        header = tk.Frame(self, bg=palette["chrome"], height=104, borderwidth=0)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        header.grid_columnconfigure(0, weight=1, minsize=310)
        header.grid_columnconfigure(1, weight=0)
        header.grid_columnconfigure(2, weight=1, minsize=130)
        header.grid_rowconfigure(0, weight=1)

        brand = tk.Frame(header, bg=palette["chrome"])
        brand.grid(row=0, column=0, sticky=tk.NSEW, padx=(26, 14))
        assets_dir = Path(__file__).resolve().parent.parent / "assets"
        icon_path = assets_dir / "app_icon_header.png"
        if icon_path.exists():
            try:
                # 使用由原图高质量缩放的页眉资源，避免 Tk 整数抽样造成模糊。
                self._header_icon = tk.PhotoImage(file=str(icon_path))
                tk.Label(brand, image=self._header_icon, bg=palette["chrome"]).pack(
                    side=tk.LEFT,
                    padx=(0, 13),
                )
            except tk.TclError:
                pass

        title_box = tk.Frame(brand, bg=palette["chrome"])
        title_box.pack(side=tk.LEFT)
        tk.Label(
            title_box,
            text=WINDOW_TITLE,
            bg=palette["chrome"],
            fg=palette["text"],
            font=self.font_title,
        ).pack(anchor=tk.W)
        tk.Label(
            title_box,
            text="重命名 · RAW/JPG 配对清理 · Adobe Bridge 标记同步",
            bg=palette["chrome"],
            fg=palette["secondary"],
            font=self.font_caption,
        ).pack(anchor=tk.W, pady=(3, 0))

        nav_panel = RoundedPanel(
            header,
            fill=palette["panel_alt"],
            outline=palette["border"],
            background=palette["chrome"],
            radius=16,
            height=49,
            padding=(5, 5),
        )
        nav_panel.configure(width=390)
        nav_panel.grid(row=0, column=1)
        self._tab_buttons: list[RoundedButton] = []
        tab_labels = ("时间重命名", "配对清理", "星标与颜色同步")
        for index, label in enumerate(tab_labels):
            button = RoundedButton(
                nav_panel.body,
                text=label,
                command=lambda selected=index: self._select_page(selected),
                palette=palette,
                font=self.font_body_medium,
                role="segment",
                width=126,
                height=38,
                radius=11,
            )
            button.set_selected(index == 0)
            button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self._tab_buttons.append(button)

        header_actions = tk.Frame(header, bg=palette["chrome"])
        header_actions.grid(row=0, column=2, sticky=tk.E, padx=(14, 22))
        RoundedButton(
            header_actions,
            text="外观…",
            command=self.open_appearance_settings,
            palette=palette,
            font=self.font_caption,
            width=88,
            height=36,
            radius=11,
        ).pack(side=tk.RIGHT)
        tk.Label(
            header_actions,
            text=f"v{__version__}",
            bg=palette["chrome"],
            fg=palette["tertiary"],
            font=self.font_caption,
        ).pack(side=tk.RIGHT, padx=(0, 14))

        tk.Frame(self, height=1, bg=palette["border"]).pack(fill=tk.X)

        notebook = ttk.Notebook(self, style="Hidden.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True, padx=18, pady=(10, 18))
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
        self.notebook = notebook
        notebook.bind("<<NotebookTabChanged>>", self._sync_tab_styles)

    def _select_page(self, index: int) -> None:
        """通过顶部的分段导航切换原有三个功能页。"""

        if self.notebook.index(self.notebook.select()) == index:
            return
        self.notebook.select(index)
        self._sync_tab_styles()
        # 点击事件返回前完成当前页面布局，避免短暂显示空白面板。
        self.notebook.update_idletasks()

    def _sync_tab_styles(self, _event: tk.Event | None = None) -> None:
        """让分段导航的选中状态与 Notebook 页面保持一致。"""

        selected = self.notebook.index(self.notebook.select())
        for index, button in enumerate(self._tab_buttons):
            button.set_selected(index == selected)

    def open_appearance_settings(self) -> None:
        """打开不干扰主要操作的透明度设置弹窗。"""

        if self._appearance_window is not None and self._appearance_window.winfo_exists():
            self._appearance_window.lift()
            self._appearance_window.focus_force()
            return

        palette = self.palette
        window = tk.Toplevel(self)
        self._appearance_window = window
        window.title("外观设置")
        window.geometry("430x245")
        window.resizable(False, False)
        window.transient(self)
        window.configure(background=palette["window"])
        window.attributes("-alpha", self.opacity_percent / 100)
        window.protocol("WM_DELETE_WINDOW", window.destroy)

        panel = RoundedPanel(
            window,
            fill=palette["panel"],
            outline=palette["border"],
            background=palette["window"],
            radius=20,
            height=205,
            padding=(22, 18),
        )
        panel.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        top_row = tk.Frame(panel.body, background=palette["panel"])
        top_row.pack(fill=tk.X)
        tk.Label(
            top_row,
            text="界面透明度",
            background=palette["panel"],
            foreground=palette["text"],
            font=self.font_body_medium,
        ).pack(side=tk.LEFT)
        self.opacity_text_var = tk.StringVar(value=f"{self.opacity_percent}%")
        tk.Label(
            top_row,
            textvariable=self.opacity_text_var,
            background=palette["panel"],
            foreground=palette["accent"],
            font=self.font_body_medium,
        ).pack(side=tk.RIGHT)

        tk.Label(
            panel.body,
            text="范围 70%～100%，拖动时实时预览；设置会在下次启动时自动恢复。",
            background=palette["panel"],
            foreground=palette["secondary"],
            font=self.font_caption,
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(8, 15))

        self.opacity_var = tk.DoubleVar(value=self.opacity_percent)
        ttk.Scale(
            panel.body,
            from_=MIN_OPACITY,
            to=MAX_OPACITY,
            variable=self.opacity_var,
            command=self._on_opacity_change,
            orient=tk.HORIZONTAL,
        ).pack(fill=tk.X)

        scale_labels = tk.Frame(panel.body, background=palette["panel"])
        scale_labels.pack(fill=tk.X, pady=(3, 15))
        tk.Label(
            scale_labels,
            text=f"{MIN_OPACITY}%  更透明",
            background=palette["panel"],
            foreground=palette["tertiary"],
            font=self.font_caption,
        ).pack(side=tk.LEFT)
        tk.Label(
            scale_labels,
            text=f"更不透明  {MAX_OPACITY}%",
            background=palette["panel"],
            foreground=palette["tertiary"],
            font=self.font_caption,
        ).pack(side=tk.RIGHT)

        button_row = tk.Frame(panel.body, background=palette["panel"])
        button_row.pack(fill=tk.X)
        RoundedButton(
            button_row,
            text="恢复默认",
            command=self._reset_opacity,
            palette=palette,
            font=self.font_body_medium,
            width=104,
        ).pack(side=tk.LEFT)
        RoundedButton(
            button_row,
            text="完成",
            command=window.destroy,
            palette=palette,
            font=self.font_body_medium,
            role="primary",
            width=88,
        ).pack(side=tk.RIGHT)

        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - window.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - window.winfo_height()) // 2
        window.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _on_close(self) -> None:
        if self._config_save_job is not None:
            self.after_cancel(self._config_save_job)
            self._config_save_job = None
        self._save_ui_config()
        self.destroy()


def run() -> None:
    """启动应用。"""

    app = PhotoAssistantApp()
    app.mainloop()
