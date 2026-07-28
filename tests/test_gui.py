"""视觉改造后的 GUI 结构、事件绑定和透明度测试。"""

from __future__ import annotations

import json
import tempfile
import threading
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
                if isinstance(widget, (ttk.Button, gui.RoundedButton))
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

    def test_photo_folder_is_shared_between_all_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            rename_page, cleanup_page, sync_page = app.notebook.winfo_children()

            with mock.patch.object(
                gui.filedialog,
                "askdirectory",
                return_value=temp_dir,
            ):
                rename_page.choose_folder(rename_page.folder_var)

            self.assertIs(rename_page.folder_var, app.shared_folder_var)
            self.assertIs(cleanup_page.folder_var, app.shared_folder_var)
            self.assertIs(sync_page.folder_var, app.shared_folder_var)
            for index, page in enumerate((rename_page, cleanup_page, sync_page)):
                app._select_page(index)
                self.assertEqual(page.folder_var.get(), temp_dir)

    def test_header_uses_high_quality_icon_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            self.assertEqual(app._header_icon.width(), 70)
            self.assertEqual(app._header_icon.height(), 70)

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

    def test_progress_footer_is_hidden_until_a_task_starts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            for page in app.notebook.winfo_children():
                self.assertEqual(page.footer.winfo_manager(), "")
                page.show_footer()
                app.update_idletasks()
                self.assertEqual(page.footer.winfo_manager(), "pack")

    def test_scan_statistics_are_hidden_until_scan_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            for page in app.notebook.winfo_children():
                self.assertIsNotNone(page.stats_container)
                self.assertEqual(page.stats_container.winfo_manager(), "")
                page.show_stats()
                app.update_idletasks()
                self.assertEqual(page.stats_container.winfo_manager(), "pack")
                self.assertLess(
                    page.content.pack_slaves().index(page.stats_container),
                    page.content.pack_slaves().index(page.table_frame),
                )

    def test_segmented_navigation_keeps_original_page_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            for index in range(3):
                app._tab_buttons[index].invoke()
                app.update_idletasks()
                self.assertEqual(app.notebook.index(app.notebook.select()), index)
                self.assertTrue(app._tab_buttons[index]._selected)
                page = app.nametowidget(app.notebook.select())
                visible_panels = [
                    widget
                    for widget in all_descendants(page)
                    if isinstance(widget, gui.RoundedPanel) and widget.winfo_ismapped()
                ]
                self.assertTrue(visible_panels)
                self.assertTrue(
                    all(panel.body.winfo_manager() == "place" for panel in visible_panels)
                )
                self.assertTrue(
                    all(panel.body.winfo_ismapped() for panel in visible_panels)
                )

    def test_background_job_delivers_progress_to_main_thread(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            page = app.nametowidget(app.notebook.tabs()[0])
            completed: list[object] = []
            activity_updates: list[tuple[int, int, str]] = []

            def task(progress: gui.core.ProgressCallback) -> int:
                progress(1, 2, "正在处理 1/2")
                progress(2, 2, "正在处理 2/2")
                return 7

            page.run_job(
                "准备中",
                task,
                completed.append,
                on_progress=lambda *update: activity_updates.append(update),
            )
            self.assertEqual(page.footer.winfo_manager(), "pack")
            deadline = time.monotonic() + 2
            while page._busy and time.monotonic() < deadline:
                app.update()
                time.sleep(0.01)

            self.assertFalse(page._busy)
            self.assertEqual(completed, [7])
            self.assertEqual(page.progress_text_var.get(), "2 / 2 · 100%")
            self.assertEqual([update[0] for update in activity_updates], [1, 2])

    def test_execute_and_undo_details_remain_visible_in_all_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            rename_page, cleanup_page, sync_page = app.notebook.winfo_children()

            rename_operation = gui.core.RenameOperation(
                "/照片/DSC0001.JPG",
                "/照片/DSC26-07-28-00001.jpg",
                "JPG",
            )
            rename_plan = gui.core.RenamePlan(
                operations=[rename_operation],
                image_count=1,
                conflicts=[],
                warnings=[],
                stats=gui.core.RenameScanStats(1, 0, 1, 0, 0, 0),
            )
            cleanup_items = [gui.core.CleanupItem("/照片/DSC0002.JPG", "RAW")]
            sync_operations = [
                gui.core.SyncOperation(
                    "/照片/DSC0003.JPG",
                    "/照片/DSC0003.ARW",
                    True,
                    5,
                    "Red",
                    0,
                    None,
                )
            ]

            with mock.patch.object(gui.messagebox, "showinfo"):
                rename_page._rename_finished(Path(temp_dir) / "rename.json", rename_plan)
                rename_values = rename_page.tree.item(
                    rename_page.tree.get_children()[0],
                    "values",
                )
                self.assertEqual(rename_values[0], "DSC0001.JPG")
                self.assertEqual(rename_values[1], "DSC26-07-28-00001.jpg")
                self.assertIn("已重命名", rename_values[2])
                rename_page._rename_undo_finished(1)
                self.assertEqual(
                    rename_page.tree.item(rename_page.tree.get_children()[-1], "values")[2],
                    "撤回完成",
                )

                cleanup_page._cleanup_finished((1, []), cleanup_items)
                cleanup_values = cleanup_page.tree.item(
                    cleanup_page.tree.get_children()[0],
                    "values",
                )
                self.assertEqual(cleanup_values[0], "DSC0002.JPG")
                self.assertEqual(cleanup_values[1], "已移入废纸篓")
                cleanup_page._restore_finished((1, []))
                self.assertEqual(
                    cleanup_page.tree.item(cleanup_page.tree.get_children()[-1], "values")[1],
                    "恢复完成",
                )

                sync_page._sync_finished(
                    (1, Path(temp_dir) / "manifest.json"),
                    sync_operations,
                )
                sync_values = sync_page.tree.item(
                    sync_page.tree.get_children()[0],
                    "values",
                )
                self.assertEqual(sync_values[0], "DSC0003.JPG")
                self.assertEqual(sync_values[1], "DSC0003.ARW")
                self.assertIn("已同步", sync_values[3])
                sync_page._sync_undo_finished(1)
                self.assertEqual(
                    sync_page.tree.item(sync_page.tree.get_children()[-1], "values")[3],
                    "撤回完成",
                )
                app._select_page(2)
                app.update_idletasks()
                first_item = sync_page.tree.get_children()[0]
                self.assertTrue(sync_page.tree.winfo_ismapped())
                self.assertTrue(sync_page.tree.bbox(first_item))
                self.assertEqual(sync_page.tree.identify_region(20, 10), "heading")

    def test_scan_results_show_only_filenames_in_all_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            rename_page, cleanup_page, sync_page = app.notebook.winfo_children()

            rename_page._show_plan(
                gui.core.RenamePlan(
                    operations=[
                        gui.core.RenameOperation(
                            "/照片/子目录/DSC0001.JPG",
                            "/照片/子目录/DSC26-07-28-00001.jpg",
                            "JPG",
                        )
                    ],
                    image_count=1,
                    conflicts=[],
                    warnings=[],
                    stats=gui.core.RenameScanStats(1, 0, 1, 0, 0, 0),
                )
            )
            cleanup_page._show_items(
                gui.core.CleanupScanResult(
                    items=[
                        gui.core.CleanupItem(
                            "/照片/子目录/DSC0002.JPG",
                            "RAW",
                        )
                    ],
                    total_images=1,
                    raw_count=0,
                    jpg_count=1,
                    target_count=1,
                    paired_target_count=0,
                )
            )
            sync_page._show_operations(
                gui.core.SyncScanResult(
                    operations=[
                        gui.core.SyncOperation(
                            "/照片/子目录/DSC0003.JPG",
                            "/照片/子目录/DSC0003.ARW",
                            True,
                            5,
                            "Red",
                            0,
                            None,
                        )
                    ],
                    total_images=2,
                    source_count=1,
                    target_count=1,
                    matched_count=1,
                    marked_count=1,
                    up_to_date_count=0,
                )
            )

            expected_rows = [
                ("DSC0001.JPG", "DSC26-07-28-00001.jpg"),
                ("DSC0002.JPG", "RAW"),
                ("DSC0003.JPG", "DSC0003.ARW"),
            ]
            for page, expected in zip(
                (rename_page, cleanup_page, sync_page),
                expected_rows,
            ):
                item = page.tree.get_children()[0]
                values = page.tree.item(item, "values")
                self.assertEqual(tuple(values[:2]), expected)
                self.assertNotIn("/照片/", " ".join(values))

    def test_result_tables_have_only_vertical_grid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            for index, page in enumerate(app.notebook.winfo_children()):
                app._select_page(index)
                app.update_idletasks()
                columns = tuple(page.tree.cget("columns"))
                self.assertEqual(len(page._tree_grid_lines), len(columns) - 1)
                self.assertTrue(
                    all(
                        line.cget("background") == app.palette["table_grid"]
                        for line in page._tree_grid_lines
                    )
                )
                self.assertTrue(
                    all(line.winfo_manager() == "place" for line in page._tree_grid_lines)
                )
                self.assertTrue(
                    all(line.winfo_width() == 1 for line in page._tree_grid_lines)
                )

    def test_terminal_progress_waits_until_background_result_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            page = app.nametowidget(app.notebook.tabs()[0])
            terminal_reported = threading.Event()
            allow_return = threading.Event()

            def task(progress: gui.core.ProgressCallback) -> int:
                progress(1, 2, "正在处理 1/2")
                progress(2, 2, "正在处理 2/2")
                terminal_reported.set()
                allow_return.wait(timeout=2)
                return 9

            completed: list[object] = []
            page.run_job("准备中", task, completed.append)
            deadline = time.monotonic() + 2
            while not terminal_reported.is_set() and time.monotonic() < deadline:
                app.update()
                time.sleep(0.01)
            app.update()

            self.assertNotEqual(float(page.progress.cget("value")), 2)
            self.assertNotEqual(page.progress_text_var.get(), "2 / 2 · 100%")

            allow_return.set()
            deadline = time.monotonic() + 2
            while page._busy and time.monotonic() < deadline:
                app.update()
                time.sleep(0.01)
            self.assertEqual(completed, [9])
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
                self.assertFalse(page.progress.winfo_ismapped())
                page.show_footer()
                app.update_idletasks()
                self.assertTrue(page.progress.winfo_ismapped())
                self.assertLessEqual(
                    page.progress.winfo_rooty() + page.progress.winfo_height(),
                    page.winfo_rooty() + page.winfo_height(),
                )


if __name__ == "__main__":
    unittest.main()
