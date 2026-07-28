"""视觉改造后的 GUI 结构、事件绑定和透明度测试。"""

from __future__ import annotations

import json
import tempfile
import tkinter as tk
import time
import unittest
from pathlib import Path
from tkinter import ttk
from unittest import mock

from photo_assistant import gui


def all_descendants(widget: tk.Misc) -> list[tk.Misc]:
    """递归返回控件树，便于确认原按钮和事件绑定仍存在。"""

    result: list[tk.Misc] = []
    for child in widget.winfo_children():
        result.append(child)
        result.extend(all_descendants(child))
    return result


def contrast_ratio(foreground: str, background: str) -> float:
    """计算两种十六进制颜色的 WCAG 对比度。"""

    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]

        def linear(value: float) -> float:
            return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

        red, green, blue = (linear(value) for value in channels)
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    lighter = max(luminance(foreground), luminance(background))
    darker = min(luminance(foreground), luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def composite_color(foreground: str, background: str, alpha: float) -> str:
    """将前景色按透明度合成到背景色上。"""

    foreground_channels = [
        int(foreground[index:index + 2], 16) for index in (1, 3, 5)
    ]
    background_channels = [
        int(background[index:index + 2], 16) for index in (1, 3, 5)
    ]
    channels = [
        round(foreground_value * alpha + background_value * (1 - alpha))
        for foreground_value, background_value in zip(
            foreground_channels,
            background_channels,
        )
    ]
    return "#" + "".join(f"{value:02X}" for value in channels)


class GuiTests(unittest.TestCase):
    def make_app(self, config_path: Path, dark_mode: bool = False) -> gui.PhotoAssistantApp:
        path_patch = mock.patch.object(gui, "UI_CONFIG_FILE", config_path)
        legacy_path_patch = mock.patch.object(
            gui,
            "LEGACY_UI_CONFIG_FILE",
            config_path.with_name("legacy_ui_config.json"),
        )
        dark_patch = mock.patch.object(
            gui.PhotoAssistantApp,
            "_detect_dark_mode",
            return_value=dark_mode,
        )
        path_patch.start()
        legacy_path_patch.start()
        dark_patch.start()
        self.addCleanup(path_patch.stop)
        self.addCleanup(legacy_path_patch.stop)
        self.addCleanup(dark_patch.stop)
        app = gui.PhotoAssistantApp()

        def cleanup_app() -> None:
            try:
                if app.winfo_exists():
                    app.destroy()
            except tk.TclError:
                pass

        self.addCleanup(cleanup_app)
        app.update_idletasks()
        return app

    def test_all_original_buttons_keep_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            buttons = [
                widget
                for widget in all_descendants(app)
                if isinstance(widget, ttk.Button)
            ]
            texts = [button.cget("text") for button in buttons]
            expected = {
                "选择文件夹…",
                "扫描并预览",
                "执行重命名",
                "撤回最近一次",
                "移入废纸篓",
                "恢复最近一次清理",
                "执行同步",
                "撤回最近一次同步",
                "外观…",
            }
            self.assertTrue(expected.issubset(set(texts)))
            self.assertTrue(all(button.cget("command") for button in buttons))

    def test_original_page_count_and_default_choices_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            pages = app.notebook.winfo_children()
            self.assertEqual(len(pages), 3)
            rename_page, cleanup_page, sync_page = pages
            self.assertIsInstance(rename_page, gui.RenamePage)
            self.assertIsInstance(cleanup_page, gui.CleanupPage)
            self.assertIsInstance(sync_page, gui.SyncPage)
            self.assertEqual(cleanup_page.kind_var.get(), "JPG")
            self.assertEqual(sync_page.direction_var.get(), "JPG → RAW")
            self.assertTrue(sync_page.rating_var.get())
            self.assertTrue(sync_page.label_var.get())
            self.assertEqual(app.title(), "旭影的摄影工具集")

    def test_all_pages_show_determinate_total_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            for page in app.notebook.winfo_children():
                self.assertEqual(str(page.progress.cget("mode")), "determinate")
                page._apply_progress(3, 10, "正在处理 3/10")
                self.assertEqual(float(page.progress.cget("maximum")), 10)
                self.assertEqual(float(page.progress.cget("value")), 3)
                self.assertEqual(page.progress_text_var.get(), "3 / 10 · 30%")
                self.assertEqual(page.status_var.get(), "正在处理 3/10")

    def test_background_job_delivers_progress_to_main_thread(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            page = app.nametowidget(app.notebook.tabs()[0])
            completed: list[object] = []

            def task(progress: gui.core.ProgressCallback) -> int:
                progress(1, 2, "正在处理 1/2")
                progress(2, 2, "正在处理 2/2")
                return 7

            page.run_job("准备中", task, completed.append)
            deadline = time.monotonic() + 2
            while page._busy and time.monotonic() < deadline:
                app.update()
                time.sleep(0.01)

            self.assertFalse(page._busy)
            self.assertEqual(completed, [7])
            self.assertEqual(page.progress_text_var.get(), "2 / 2 · 100%")

    def test_opacity_updates_live_and_restores_next_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "ui_config.json"
            app = self.make_app(config_path)
            app._on_opacity_change("78")
            app._save_ui_config()
            self.assertEqual(app.opacity_percent, 78)
            self.assertAlmostEqual(float(app.attributes("-alpha")), 0.78, places=2)
            self.assertEqual(json.loads(config_path.read_text())["opacity"], 78)
            app.destroy()

            second_app = self.make_app(config_path)
            self.assertEqual(second_app.opacity_percent, 78)
            self.assertAlmostEqual(float(second_app.attributes("-alpha")), 0.78, places=2)

    def test_opacity_reads_legacy_config_after_app_rename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "new" / "ui_config.json"
            legacy_path = Path(temp_dir) / "legacy" / "ui_config.json"
            legacy_path.parent.mkdir()
            legacy_path.write_text('{"opacity": 81}', encoding="utf-8")
            with (
                mock.patch.object(gui, "UI_CONFIG_FILE", config_path),
                mock.patch.object(gui, "LEGACY_UI_CONFIG_FILE", legacy_path),
            ):
                self.assertEqual(gui.PhotoAssistantApp._load_opacity(), 81)

    def test_opacity_is_clamped_to_readable_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            app._apply_opacity(10)
            self.assertEqual(app.opacity_percent, gui.MIN_OPACITY)
            app._apply_opacity(150)
            self.assertEqual(app.opacity_percent, gui.MAX_OPACITY)

    def test_light_and_dark_palettes_have_readable_contrast(self) -> None:
        for palette in (gui.LIGHT_PALETTE, gui.DARK_PALETTE):
            self.assertGreaterEqual(
                contrast_ratio(palette["text"], palette["panel"]),
                7.0,
            )
            self.assertGreaterEqual(
                contrast_ratio(palette["secondary"], palette["panel"]),
                3.5,
            )

    def test_primary_text_remains_readable_at_minimum_opacity(self) -> None:
        alpha = gui.MIN_OPACITY / 100
        for palette in (gui.LIGHT_PALETTE, gui.DARK_PALETTE):
            for desktop in ("#000000", "#FFFFFF", "#808080"):
                composited_text = composite_color(palette["text"], desktop, alpha)
                composited_panel = composite_color(palette["panel"], desktop, alpha)
                self.assertGreaterEqual(
                    contrast_ratio(composited_text, composited_panel),
                    4.5,
                )

    def test_dark_mode_and_minimum_window_size_initialize(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json", dark_mode=True)
            self.assertTrue(app.dark_mode)
            self.assertEqual(app.palette, gui.DARK_PALETTE)
            app.geometry("980x680")
            app.update_idletasks()
            for tab_id in app.notebook.tabs():
                app.notebook.select(tab_id)
                app.update_idletasks()
                page = app.nametowidget(tab_id)
                trees = [
                    widget
                    for widget in all_descendants(page)
                    if isinstance(widget, ttk.Treeview)
                ]
                self.assertEqual(len(trees), 1)
                self.assertGreater(trees[0].winfo_width(), 100)


if __name__ == "__main__":
    unittest.main()
