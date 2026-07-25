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
from typing import Callable

from . import __version__
from . import core


WINDOW_TITLE = "旭影的摄影工具集"
LEGACY_WINDOW_TITLE = "摄影文件后期处理助手"
MAX_PREVIEW_ROWS = 1000
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
    "window": "#E9ECF1",
    "chrome": "#F4F5F7",
    "surface": "#F7F8FA",
    "panel": "#FCFCFD",
    "panel_alt": "#F1F3F6",
    "border": "#D9DDE5",
    "text": "#1D1D1F",
    "secondary": "#6E6E73",
    "tertiary": "#8E8E93",
    "accent": "#3978D3",
    "accent_active": "#2866BE",
    "danger": "#B85C66",
    "danger_active": "#A44C56",
    "selection": "#DCE9FA",
}

DARK_PALETTE = {
    "window": "#1B1B1D",
    "chrome": "#242426",
    "surface": "#202124",
    "panel": "#2A2A2D",
    "panel_alt": "#303034",
    "border": "#414145",
    "text": "#F5F5F7",
    "secondary": "#B2B2B7",
    "tertiary": "#8E8E93",
    "accent": "#6AA9F4",
    "accent_active": "#82B8F7",
    "danger": "#D27A83",
    "danger_active": "#DF8C94",
    "selection": "#304865",
}


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
        self._body_window = self.create_window(
            padding[0],
            padding[1],
            anchor=tk.NW,
            window=self.body,
        )
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event: tk.Event) -> None:
        width = max(2, event.width - 1)
        height = max(2, event.height - 1)
        radius = min(self._radius, width // 2, height // 2)
        points = [
            radius, 1,
            width - radius, 1,
            width - 1, 1,
            width - 1, radius,
            width - 1, height - radius,
            width - 1, height - 1,
            width - radius, height - 1,
            radius, height - 1,
            1, height - 1,
            1, height - radius,
            1, radius,
            1, 1,
        ]
        self.delete("panel")
        self.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            fill=self._fill,
            outline=self._outline,
            width=1,
            tags="panel",
        )
        self.tag_lower("panel")
        pad_x, pad_y = self._padding
        self.coords(self._body_window, pad_x, pad_y)
        self.itemconfigure(
            self._body_window,
            width=max(1, event.width - pad_x * 2),
            height=max(1, event.height - pad_y * 2),
        )


class BasePage(ttk.Frame):
    """三个功能页共享的后台任务与状态栏。"""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=(24, 20), style="Page.TFrame")
        self._job_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._busy = False
        self.palette = self.winfo_toplevel().palette

        self.content = ttk.Frame(self, style="Page.TFrame")
        self.content.pack(fill=tk.BOTH, expand=True)

        footer = ttk.Frame(self, style="Page.TFrame")
        footer.pack(fill=tk.X, pady=(14, 0))
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=150)
        self.progress.pack(side=tk.RIGHT)

    def run_job(
        self,
        status: str,
        function: Callable[[], object],
        on_success: Callable[[object], None],
    ) -> None:
        """在线程中执行耗时任务，界面更新仍留在主线程。"""

        if self._busy:
            return
        self._busy = True
        self.status_var.set(status)
        self.progress.start(12)

        def worker() -> None:
            try:
                self._job_queue.put(("success", function()))
            except Exception as exc:
                self._job_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()
        self.after(80, lambda: self._poll_job(on_success))

    def _poll_job(self, on_success: Callable[[object], None]) -> None:
        try:
            state, payload = self._job_queue.get_nowait()
        except queue.Empty:
            self.after(80, lambda: self._poll_job(on_success))
            return

        self._busy = False
        self.progress.stop()
        if state == "error":
            self.status_var.set("操作失败")
            messagebox.showerror("操作失败", str(payload), parent=self)
            return
        self.status_var.set("完成")
        on_success(payload)

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

    def create_stats(
        self,
        items: list[tuple[str, str]],
    ) -> dict[str, tk.StringVar]:
        """创建一排始终可见的扫描统计卡片。"""

        container = RoundedPanel(
            self.content,
            fill=self.palette["panel"],
            outline=self.palette["border"],
            background=self.palette["surface"],
            radius=18,
            height=88,
            padding=(14, 8),
        )
        container.pack(fill=tk.X, pady=(0, 14))
        variables: dict[str, tk.StringVar] = {}
        for index, (key, label) in enumerate(items):
            card = tk.Frame(container.body, background=self.palette["panel"])
            card.pack(side=tk.LEFT, fill=tk.X, expand=True)
            value_var = tk.StringVar(value="—")
            variables[key] = value_var
            tk.Label(
                card,
                textvariable=value_var,
                font=self.winfo_toplevel().font_stat_value,
                foreground=self.palette["accent"],
                background=self.palette["panel"],
                anchor=tk.CENTER,
            ).pack(fill=tk.X)
            tk.Label(
                card,
                text=label,
                font=self.winfo_toplevel().font_caption,
                foreground=self.palette["secondary"],
                background=self.palette["panel"],
                anchor=tk.CENTER,
            ).pack(fill=tk.X)
            if index < len(items) - 1:
                tk.Frame(
                    container.body,
                    width=1,
                    background=self.palette["border"],
                ).pack(
                    side=tk.LEFT,
                    fill=tk.Y,
                    pady=8,
                )
        return variables

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

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.plan: core.RenamePlan | None = None
        self.folder_var = tk.StringVar()

        self._title(
            "根据拍摄时间重命名",
            "按 EXIF 拍摄时间排序，将 RAW、JPG 和对应 XMP 侧车安全地统一命名。",
        )
        self._folder_row()

        action_row = ttk.Frame(self.content)
        action_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(action_row, text="扫描并预览", command=self.preview).pack(side=tk.LEFT)
        ttk.Button(
            action_row,
            text="执行重命名",
            style="Accent.TButton",
            command=self.execute,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(action_row, text="撤回最近一次", command=self.undo).pack(side=tk.LEFT)

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
        ).pack(anchor=tk.W, pady=(5, 18))

    def _folder_row(self) -> None:
        row = ttk.Frame(self.content, style="Page.TFrame")
        row.pack(fill=tk.X, pady=(0, 14))
        ttk.Entry(row, textvariable=self.folder_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            row,
            text="选择文件夹…",
            command=lambda: self.choose_folder(self.folder_var),
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(row, text="包含所有子文件夹", style="Muted.TLabel").pack(
            side=tk.LEFT,
            padx=(12, 0),
        )

    def _pack_tree(self, tree: ttk.Treeview) -> None:
        frame = tk.Frame(
            self.content,
            background=self.palette["panel"],
            highlightbackground=self.palette["border"],
            highlightcolor=self.palette["border"],
            highlightthickness=1,
            borderwidth=0,
        )
        frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(in_=frame, side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(1, 0), pady=1)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def preview(self) -> None:
        try:
            folder = self.require_folder(self.folder_var)
        except Exception as exc:
            messagebox.showwarning("提示", str(exc), parent=self)
            return
        self.run_job(
            "正在读取拍摄时间并生成预览…",
            lambda: core.build_rename_plan(folder, recursive=True),
            self._show_plan,
        )

    def _show_plan(self, payload: object) -> None:
        plan = payload
        assert isinstance(plan, core.RenamePlan)
        self.plan = plan
        rows = [
            (operation.source, operation.target, operation.kind)
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
        self.run_job(
            "正在安全重命名…",
            lambda: core.execute_rename_plan(plan),
            self._rename_finished,
        )

    def _rename_finished(self, payload: object) -> None:
        backup_path = Path(payload)
        count = self.plan.image_count if self.plan else 0
        self.plan = None
        self.tree.delete(*self.tree.get_children())
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
        self.run_job(
            "正在撤回重命名…",
            core.undo_latest_rename,
            lambda value: messagebox.showinfo(
                "撤回完成",
                f"已恢复 {value} 个文件。",
                parent=self,
            ),
        )


class CleanupPage(BasePage):
    """RAW/JPG 配对清理页面。"""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.items: list[core.CleanupItem] = []
        self.folder_var = tk.StringVar()
        self.kind_var = tk.StringVar(value="JPG")

        ttk.Label(self.content, text="RAW / JPG 配对清理", style="PageTitle.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            self.content,
            text="递归检查同一文件夹内的同名照片；移入废纸篓前创建隐藏安全备份，恢复不依赖 Finder。",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(4, 16))

        folder_row = ttk.Frame(self.content)
        folder_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
        )
        ttk.Button(
            folder_row,
            text="选择文件夹…",
            command=lambda: self.choose_folder(self.folder_var),
        ).pack(side=tk.LEFT, padx=(8, 0))

        option_row = ttk.Frame(self.content)
        option_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(option_row, text="要清理的格式：").pack(side=tk.LEFT)
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

        action_row = ttk.Frame(self.content)
        action_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(action_row, text="扫描并预览", command=self.preview).pack(side=tk.LEFT)
        ttk.Button(
            action_row,
            text="移入废纸篓",
            style="Danger.TButton",
            command=self.execute,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(action_row, text="恢复最近一次清理", command=self.restore).pack(side=tk.LEFT)

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
            lambda: core.scan_cleanup(folder, kind, recursive=True),
            self._show_items,
        )

    def _show_items(self, payload: object) -> None:
        result = payload
        assert isinstance(result, core.CleanupScanResult)
        self.items = result.items
        self.fill_tree(
            self.tree,
            [(item.path, item.missing_pair_kind) for item in self.items],
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
        self.run_job(
            "正在移入废纸篓…",
            lambda: core.move_cleanup_items_to_trash(items),
            self._cleanup_finished,
        )

    def _cleanup_finished(self, payload: object) -> None:
        moved, errors = payload
        self.items = []
        self.tree.delete(*self.tree.get_children())
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
        self.run_job(
            "正在从废纸篓恢复…",
            core.restore_latest_cleanup,
            self._restore_finished,
        )

    def _restore_finished(self, payload: object) -> None:
        restored, errors = payload
        self.status_var.set(f"已恢复 {restored} 个文件")
        text = f"已恢复 {restored} 个文件。"
        if restored:
            text += "\n\n废纸篓中可能仍保留同一文件的安全副本，确认照片正常后可照常清空废纸篓。"
        if errors:
            text += f"\n\n有 {len(errors)} 个文件未恢复：\n" + "\n".join(errors[:8])
        messagebox.showinfo("恢复结果", text, parent=self)


class SyncPage(BasePage):
    """Adobe Bridge 星标与颜色标签同步页面。"""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.operations: list[core.SyncOperation] = []
        self.folder_var = tk.StringVar()
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
        ).pack(anchor=tk.W, pady=(4, 16))

        folder_row = ttk.Frame(self.content)
        folder_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
        )
        ttk.Button(
            folder_row,
            text="选择文件夹…",
            command=lambda: self.choose_folder(self.folder_var),
        ).pack(side=tk.LEFT, padx=(8, 0))

        option_row = ttk.Frame(self.content)
        option_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(option_row, text="方向：").pack(side=tk.LEFT)
        ttk.Combobox(
            option_row,
            textvariable=self.direction_var,
            values=("JPG → RAW", "RAW → JPG"),
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT, padx=(6, 18))
        ttk.Checkbutton(option_row, text="同步星标", variable=self.rating_var).pack(
            side=tk.LEFT
        )
        ttk.Checkbutton(option_row, text="同步颜色标签", variable=self.label_var).pack(
            side=tk.LEFT,
            padx=(12, 0),
        )

        action_row = ttk.Frame(self.content)
        action_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(action_row, text="扫描并预览", command=self.preview).pack(side=tk.LEFT)
        ttk.Button(
            action_row,
            text="执行同步",
            style="Accent.TButton",
            command=self.execute,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(action_row, text="撤回最近一次同步", command=self.undo).pack(side=tk.LEFT)

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
            lambda: core.scan_sync(
                folder,
                direction,
                sync_rating,
                sync_label,
                recursive=True,
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
                (operation.source, operation.target, rating_text, label_text)
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
        self.run_job(
            "正在备份并同步 XMP 标记…",
            lambda: core.execute_sync_plan(operations),
            self._sync_finished,
        )

    def _sync_finished(self, payload: object) -> None:
        count, manifest = payload
        self.operations = []
        self.tree.delete(*self.tree.get_children())
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
        self.run_job(
            "正在恢复 XMP 备份…",
            core.undo_latest_sync,
            lambda value: messagebox.showinfo(
                "撤回完成",
                f"已恢复 {value} 个目标文件。",
                parent=self,
            ),
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

        # 字体只影响视觉层，中文字符由系统自动回退到苹方。
        self.font_title = ("-apple-system", 21, "bold")
        self.font_page_title = ("-apple-system", 21, "bold")
        self.font_body = ("-apple-system", 13)
        self.font_body_medium = ("-apple-system", 13, "bold")
        self.font_caption = ("-apple-system", 11)
        self.font_stat_value = ("-apple-system", 20, "bold")

        self.title(WINDOW_TITLE)
        self.geometry("1160x800")
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
        using_aqua = (
            sys.platform == "darwin"
            and not self.dark_mode
            and "aqua" in style.theme_names()
        )
        if using_aqua:
            style.theme_use("aqua")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
        palette = self.palette
        style.configure(".", font=self.font_body)
        style.configure("TFrame", background=palette["surface"])
        style.configure("Page.TFrame", background=palette["surface"])
        style.configure("TLabel", background=palette["surface"], foreground=palette["text"])
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
        style.configure("TButton", padding=(14, 8), font=self.font_body)
        style.configure("Header.TButton", padding=(12, 6), font=self.font_caption)
        if not using_aqua:
            # Clam 主题允许稳定控制深色控件，避免使用系统默认的浅米色按钮。
            style.configure(
                "TButton",
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
            background=palette["surface"],
            foreground=palette["text"],
        )
        style.configure(
            "TRadiobutton",
            background=palette["surface"],
            foreground=palette["text"],
        )
        style.configure(
            "Accent.TButton",
            foreground=palette["accent"] if using_aqua else "#FFFFFF",
            background=palette["accent"],
            bordercolor=palette["accent"],
        )
        style.map(
            "Accent.TButton",
            background=[("active", palette["accent_active"])],
            foreground=[
                ("disabled", palette["tertiary"]),
                ("active", palette["accent_active"] if using_aqua else "#FFFFFF"),
            ],
        )
        style.configure(
            "Danger.TButton",
            foreground=palette["danger"],
            background=palette["panel_alt"],
            bordercolor=palette["border"],
        )
        style.map(
            "Danger.TButton",
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
            "TNotebook",
            background=palette["window"],
            borderwidth=0,
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
            tabmargins=(8, 6, 8, 0),
        )
        style.configure(
            "TNotebook.Tab",
            font=self.font_body_medium,
            padding=(22, 11),
        )
        style.map(
            "TNotebook.Tab",
            foreground=[
                ("selected", palette["text"]),
                ("!selected", palette["secondary"]),
            ],
        )
        if not using_aqua:
            style.configure(
                "TNotebook.Tab",
                background=palette["panel_alt"],
                bordercolor=palette["border"],
                lightcolor=palette["panel_alt"],
                darkcolor=palette["border"],
            )
            style.map(
                "TNotebook.Tab",
                background=[
                    ("selected", palette["panel"]),
                    ("active", palette["border"]),
                ],
                foreground=[
                    ("selected", palette["text"]),
                    ("!selected", palette["secondary"]),
                ],
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
        )

    def _build_ui(self) -> None:
        palette = self.palette
        header = tk.Frame(self, bg=palette["chrome"], height=88, borderwidth=0)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        icon_path = Path(__file__).resolve().parent.parent / "assets" / "app_icon.png"
        if icon_path.exists():
            try:
                self._header_icon = tk.PhotoImage(file=str(icon_path)).subsample(20, 20)
                tk.Label(header, image=self._header_icon, bg=palette["chrome"]).pack(
                    side=tk.LEFT,
                    padx=(24, 13),
                )
            except tk.TclError:
                pass

        title_box = tk.Frame(header, bg=palette["chrome"])
        title_box.pack(side=tk.LEFT, pady=14)
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

        header_actions = tk.Frame(header, bg=palette["chrome"])
        header_actions.pack(side=tk.RIGHT, padx=(8, 20))
        ttk.Button(
            header_actions,
            text="外观…",
            style="Header.TButton",
            command=self.open_appearance_settings,
        ).pack(side=tk.RIGHT)
        tk.Label(
            header_actions,
            text=f"v{__version__}",
            bg=palette["chrome"],
            fg=palette["tertiary"],
            font=self.font_caption,
        ).pack(side=tk.RIGHT, padx=(0, 14))

        tk.Frame(self, height=1, bg=palette["border"]).pack(fill=tk.X)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=18, pady=(12, 18))
        notebook.add(RenamePage(notebook), text="  时间重命名  ")
        notebook.add(CleanupPage(notebook), text="  配对清理  ")
        notebook.add(SyncPage(notebook), text="  星标与颜色同步  ")
        self.notebook = notebook

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
        ttk.Button(
            button_row,
            text="恢复默认",
            command=self._reset_opacity,
        ).pack(side=tk.LEFT)
        ttk.Button(
            button_row,
            text="完成",
            style="Accent.TButton",
            command=window.destroy,
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
