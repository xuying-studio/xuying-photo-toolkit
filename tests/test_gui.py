"""视觉改造后的 GUI 结构、事件绑定和皮肤测试。"""

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


def processing_pages(app: gui.PhotoAssistantApp) -> tuple[tk.Misc, ...]:
    """返回原有三个照片处理页，不把原生工具入口混入表格断言。"""

    return tuple(app.notebook.winfo_children()[:3])


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


class GuiTests(unittest.TestCase):
    def make_app(self, config_path: Path) -> gui.PhotoAssistantApp:
        path_patch = mock.patch.object(gui, "UI_CONFIG_FILE", config_path)
        legacy_path_patch = mock.patch.object(
            gui,
            "LEGACY_UI_CONFIG_FILES",
            (config_path.with_name("legacy_ui_config.json"),),
        )
        path_patch.start()
        legacy_path_patch.start()
        self.addCleanup(path_patch.stop)
        self.addCleanup(legacy_path_patch.stop)
        app = gui.PhotoAssistantApp()

        def cleanup_app() -> None:
            try:
                if app.winfo_exists():
                    app.destroy()
            except tk.TclError:
                pass

        self.addCleanup(cleanup_app)
        app.update()
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
                "移入回收站" if gui.sys.platform == "win32" else "移入废纸篓",
                "恢复最近一次清理",
                "执行同步",
                "撤回最近一次同步",
                "外观…",
            }
            self.assertTrue(expected.issubset(set(texts)))
            self.assertTrue(all(button.cget("command") for button in buttons))

    def test_original_pages_remain_and_keyword_quickcut_is_added_last(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            pages = app.notebook.winfo_children()
            self.assertEqual(len(pages), 4)
            rename_page, cleanup_page, sync_page, quickcut_page = pages
            self.assertIsInstance(rename_page, gui.RenamePage)
            self.assertIsInstance(cleanup_page, gui.CleanupPage)
            self.assertIsInstance(sync_page, gui.SyncPage)
            self.assertIsInstance(quickcut_page, gui.KeywordQuickCutPage)
            self.assertEqual(cleanup_page.kind_var.get(), "JPG")
            self.assertEqual(sync_page.direction_var.get(), "JPG → RAW")
            self.assertTrue(sync_page.rating_var.get())
            self.assertTrue(sync_page.label_var.get())
            self.assertEqual(app.title(), "旭影工具箱")

    def test_all_pages_state_current_folder_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            labels = [
                widget.cget("text")
                for widget in all_descendants(app)
                if isinstance(widget, tk.Label)
            ]
            self.assertEqual(labels.count("仅扫描当前文件夹"), 3)

    def test_keyword_quickcut_support_boundaries_are_explicit(self) -> None:
        library_path = Path("/tmp/libKeywordAlignerBridge.dylib")
        self.assertEqual(
            gui._keyword_quickcut_support(
                library_path,
                platform_name="win32",
                machine="arm64",
                mac_version="14.0",
            )[0],
            False,
        )
        self.assertEqual(
            gui._keyword_quickcut_support(
                library_path,
                platform_name="darwin",
                machine="x86_64",
                mac_version="14.0",
            )[0],
            False,
        )
        self.assertEqual(
            gui._keyword_quickcut_support(
                library_path,
                platform_name="darwin",
                machine="arm64",
                mac_version="12.6",
            )[0],
            False,
        )
        self.assertTrue(
            gui._keyword_quickcut_support(
                library_path,
                platform_name="darwin",
                machine="arm64",
                mac_version="13.0",
            )[0]
        )

    def test_keyword_quickcut_attaches_inside_current_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            library_path = root / gui.KEYWORD_QUICKCUT_LIBRARY_NAME
            library_path.write_bytes(b"test")
            library = mock.Mock()
            library.XUKeywordAlignerCreate.return_value = 1234
            library.XUKeywordAlignerIsBusy.return_value = 0
            with (
                mock.patch.object(
                    gui,
                    "_resolve_keyword_quickcut_library",
                    return_value=library_path,
                ),
                mock.patch.object(
                    gui,
                    "_load_keyword_quickcut_library",
                    return_value=library,
                ),
                mock.patch.object(gui.sys, "platform", "darwin"),
                mock.patch.object(gui.platform, "machine", return_value="arm64"),
                mock.patch.object(
                    gui.platform,
                    "mac_ver",
                    return_value=("14.0", ("", "", ""), ""),
                ),
            ):
                app = self.make_app(root / "ui_config.json")
                quickcut_page = app.notebook.winfo_children()[3]
                self.assertTrue(quickcut_page.is_available)
                app._select_page(3)
                quickcut_page._sync_native_view()
                library.XUKeywordAlignerCreate.assert_called_once()
                library.XUKeywordAlignerSetTheme.assert_called()
                self.assertTrue(quickcut_page.bridge.is_attached)

                app._select_page(0)
                library.XUKeywordAlignerSetVisible.assert_called_with(
                    mock.ANY,
                    mock.ANY,
                )

    def test_keyword_quickcut_busy_state_blocks_skin_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            quickcut_page = app.notebook.winfo_children()[3]
            quickcut_page.bridge = mock.Mock()
            quickcut_page.bridge.is_busy.return_value = True
            with mock.patch.object(gui.messagebox, "showwarning") as warning:
                self.assertFalse(
                    app._apply_skin("nebula_navy", confirm_results=False)
                )
            warning.assert_called_once()

    def test_cleanup_uses_dark_custom_radio_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            cleanup_page = app.notebook.winfo_children()[1]
            self.assertTrue(
                all(
                    isinstance(button, gui.RoundedRadiobutton)
                    for button in cleanup_page._kind_buttons
                )
            )
            app._select_page(1)
            app.update()
            cleanup_page._kind_buttons[1].focus_set()
            cleanup_page._kind_buttons[1].event_generate("<Return>")
            app.update()
            self.assertEqual(cleanup_page.kind_var.get(), "RAW")
            self.assertTrue(cleanup_page._kind_buttons[1]._focused)

    def test_photo_folder_is_shared_between_all_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            rename_page, cleanup_page, sync_page = processing_pages(app)

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

    def test_sidebar_uses_high_quality_icon_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            self.assertEqual(app._header_icon.width(), 70)
            self.assertEqual(app._header_icon.height(), 70)

    def test_all_pages_show_determinate_total_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            for page in processing_pages(app):
                self.assertEqual(str(page.progress.cget("mode")), "determinate")
                page._apply_progress(3, 10, "正在处理 3/10")
                self.assertEqual(float(page.progress.cget("maximum")), 10)
                self.assertEqual(float(page.progress.cget("value")), 3)
                self.assertEqual(page.progress_text_var.get(), "3 / 10 · 30%")
                self.assertEqual(page.status_var.get(), "正在处理 3/10")

    def test_progress_footer_is_hidden_until_a_task_starts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            for page in processing_pages(app):
                self.assertEqual(page.footer.winfo_manager(), "")
                page.show_footer()
                app.update_idletasks()
                self.assertEqual(page.footer.winfo_manager(), "pack")

    def test_scan_statistics_are_hidden_until_scan_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            for page in processing_pages(app):
                self.assertIsNotNone(page.stats_container)
                self.assertEqual(page.stats_container.winfo_manager(), "")
                page.show_stats()
                app.update_idletasks()
                self.assertEqual(page.stats_container.winfo_manager(), "pack")
                self.assertLess(
                    page.content.pack_slaves().index(page.stats_container),
                    page.content.pack_slaves().index(page.table_frame),
                )

    def test_sidebar_navigation_keeps_original_page_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            self.assertEqual(app.sidebar.winfo_manager(), "grid")
            self.assertEqual(
                [button.cget("text") for button in app._nav_buttons],
                ["时间重命名", "配对清理", "星标与颜色同步", "关键词快切"],
            )
            for index in range(4):
                app._nav_buttons[index].invoke()
                app.update()
                self.assertEqual(app.notebook.index(app.notebook.select()), index)
                self.assertTrue(app._nav_buttons[index]._selected)
                self.assertTrue(
                    all(
                        button._selected == (button_index == index)
                        for button_index, button in enumerate(app._nav_buttons)
                    )
                )
                page = app.nametowidget(app.notebook.select())
                if isinstance(page, gui.KeywordQuickCutPage):
                    self.assertTrue(page.host.winfo_ismapped())
                    continue
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

    def test_sidebar_width_uses_confirmed_breakpoint(self) -> None:
        self.assertEqual(
            gui.PhotoAssistantApp._sidebar_width_for(1120),
            gui.SIDEBAR_EXPANDED_WIDTH,
        )
        self.assertEqual(
            gui.PhotoAssistantApp._sidebar_width_for(1119),
            gui.SIDEBAR_COMPACT_WIDTH,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            app.geometry("1300x760")
            app.update()
            self.assertAlmostEqual(
                app.sidebar.winfo_width(),
                gui.SIDEBAR_EXPANDED_WIDTH,
                delta=2,
            )
            app.geometry("1119x700")
            app.update()
            self.assertAlmostEqual(
                app.sidebar.winfo_width(),
                gui.SIDEBAR_EXPANDED_WIDTH,
                delta=2,
            )
            app.geometry("1400x800")
            app.update()
            self.assertAlmostEqual(
                app.sidebar.winfo_width(),
                gui.SIDEBAR_EXPANDED_WIDTH,
                delta=2,
            )
            self.assertTrue(app._brand_subtitle_label.winfo_ismapped())
            app.geometry("1119x700")
            app.update()
            self.assertAlmostEqual(
                app.sidebar.winfo_width(),
                gui.SIDEBAR_EXPANDED_WIDTH,
                delta=2,
            )
            self.assertTrue(app._brand_subtitle_label.winfo_ismapped())

    def test_sidebar_navigation_supports_keyboard_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            button = app._nav_buttons[1]
            button.focus_set()
            button.event_generate("<Return>")
            app.update()
            self.assertEqual(app.notebook.index(app.notebook.select()), 1)
            self.assertTrue(button._selected)

    def test_minimum_window_keeps_workspace_controls_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            app.geometry("1300x760")
            app.update()
            self.assertAlmostEqual(
                app.sidebar.winfo_width(),
                gui.SIDEBAR_EXPANDED_WIDTH,
                delta=2,
            )
            self.assertGreater(app.notebook.winfo_width(), 500)
            self.assertTrue(app.appearance_button.winfo_ismapped())
            self.assertIs(app.appearance_button.master, app._sidebar_bottom)
            self.assertFalse(hasattr(app, "local_status_panel"))
            labels = [
                widget.cget("text")
                for widget in all_descendants(app)
                if isinstance(widget, tk.Label)
            ]
            self.assertNotIn("本地处理", labels)
            for button in app._nav_buttons:
                self.assertTrue(button.winfo_ismapped())
                self.assertGreater(button.winfo_width(), 120)
                self.assertGreater(button.winfo_height(), 30)

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
            rename_page, cleanup_page, sync_page = processing_pages(app)

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
                self.assertEqual(
                    cleanup_values[1],
                    "已移入回收站"
                    if gui.sys.platform == "win32"
                    else "已移入废纸篓",
                )
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
                app.update()
                first_item = sync_page.tree.get_children()[0]
                self.assertTrue(sync_page.tree.winfo_ismapped())
                self.assertTrue(sync_page.tree.bbox(first_item))
                self.assertEqual(sync_page.tree.identify_region(20, 10), "heading")

    def test_scan_results_show_only_filenames_in_all_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            rename_page, cleanup_page, sync_page = processing_pages(app)

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
            for index, page in enumerate(processing_pages(app)):
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

    def test_ui_config_ignores_legacy_opacity_and_saves_only_skin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "ui_config.json"
            config_path.write_text(
                '{"opacity": 78, "skin": "liquid_glass"}',
                encoding="utf-8",
            )
            app = self.make_app(config_path)
            self.assertEqual(app.skin_id, "liquid_glass")
            self.assertAlmostEqual(float(app.attributes("-alpha")), 1.0, places=2)
            self.assertFalse(hasattr(app, "opacity_percent"))
            app._save_ui_config()
            saved = json.loads(config_path.read_text())
            self.assertEqual(saved, {"skin": "liquid_glass"})

    def test_skin_reads_legacy_config_after_app_rename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "new" / "ui_config.json"
            legacy_path = Path(temp_dir) / "legacy" / "ui_config.json"
            legacy_path.parent.mkdir()
            legacy_path.write_text(
                '{"opacity": 81, "skin": "bento_modular"}',
                encoding="utf-8",
            )
            with (
                mock.patch.object(gui, "UI_CONFIG_FILE", config_path),
                mock.patch.object(gui, "LEGACY_UI_CONFIG_FILES", (legacy_path,)),
            ):
                self.assertEqual(
                    gui.PhotoAssistantApp._load_ui_config(), "bento_modular"
                )

    def test_unknown_skin_falls_back_to_professional_dark(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "ui_config.json"
            config_path.write_text(
                '{"opacity": 86, "skin": "unknown"}',
                encoding="utf-8",
            )
            with mock.patch.object(gui, "UI_CONFIG_FILE", config_path):
                self.assertEqual(
                    gui.PhotoAssistantApp._load_ui_config(), gui.DEFAULT_SKIN_ID
                )

    def test_nebula_skin_falls_back_safely_without_native_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "ui_config.json"
            config_path.write_text(
                '{"opacity": 92, "skin": "nebula_navy"}',
                encoding="utf-8",
            )
            with mock.patch.object(
                gui,
                "_load_native_vibrancy_library",
                return_value=None,
            ):
                app = self.make_app(config_path)
            self.assertEqual(app.skin_id, "nebula_navy")
            self.assertFalse(app.native_glass_active)
            self.assertEqual(
                app.surface_background,
                gui.NEBULA_NAVY_PALETTE["surface"],
            )

    def test_fixed_dark_palette_matches_product_specification(self) -> None:
        expected = {
            "window": "#0B0E14",
            "panel": "#141923",
            "accent": "#2F6BFF",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "danger": "#EF4444",
            "text": "#F5F7FA",
            "secondary": "#8B93A5",
            "border": "#282D36",
        }
        for key, value in expected.items():
            self.assertEqual(gui.DARK_PALETTE[key], value)
        self.assertGreaterEqual(
            contrast_ratio(gui.DARK_PALETTE["text"], gui.DARK_PALETTE["panel"]),
            7.0,
        )
        self.assertGreaterEqual(
            contrast_ratio(
                gui.DARK_PALETTE["secondary"],
                gui.DARK_PALETTE["panel"],
            ),
            3.5,
        )

    def test_nebula_skin_matches_reference_palette_and_schema(self) -> None:
        palette = gui.NEBULA_NAVY_PALETTE
        expected = {
            "window": "#070B1A",
            "panel": "#101A35",
            "accent": "#5A6FFF",
            "glow": "#6D5DFB",
            "text": "#F5F7FF",
            "title": "#7EA0FF",
            "secondary": "#95A2C3",
        }
        for key, value in expected.items():
            self.assertEqual(palette[key], value)
        self.assertEqual(set(palette), set(gui.DARK_PALETTE))
        self.assertIs(
            gui.SKIN_PALETTES[gui.DEFAULT_SKIN_ID],
            gui.DARK_PALETTE,
        )

    def test_selected_designs_are_registered_as_five_new_skins(self) -> None:
        self.assertEqual(
            gui.SKIN_ORDER,
            (
                "professional_dark",
                "nebula_navy",
                "liquid_glass",
                "bento_modular",
                "editorial_minimal",
                "aurora_spatial",
                "soft_3d",
            ),
        )
        self.assertEqual(len(gui.SKIN_PALETTES), 7)
        self.assertEqual(
            {gui.SKIN_LABELS[skin_id][0] for skin_id in gui.SKIN_ORDER[2:]},
            {"流光玻璃", "模块拼盘", "编辑部极简", "极光空间", "柔软三维"},
        )
        expected_schema = set(gui.DARK_PALETTE)
        self.assertTrue(
            all(set(palette) == expected_schema for palette in gui.SKIN_PALETTES.values())
        )

    def test_all_skin_text_remains_readable_at_full_opacity(self) -> None:
        for palette in gui.SKIN_PALETTES.values():
            self.assertGreaterEqual(
                contrast_ratio(palette["text"], palette["panel"]),
                4.5,
            )

    def test_skin_rebuild_preserves_stable_window_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "ui_config.json"
            app = self.make_app(config_path)
            old_notebook = app.notebook
            binding_before = app.bind("<Configure>")
            app.shared_folder_var.set("/tmp/照片")
            app._select_page(2)

            self.assertTrue(
                app._apply_skin("editorial_minimal", confirm_results=False)
            )
            self.assertIsNot(app.notebook, old_notebook)
            self.assertEqual(app.skin_id, "editorial_minimal")
            self.assertIs(app.palette, gui.EDITORIAL_MINIMAL_PALETTE)
            self.assertFalse(app.dark_mode)
            self.assertEqual(app.notebook.index(app.notebook.select()), 2)
            self.assertEqual(app.shared_folder_var.get(), "/tmp/照片")
            self.assertAlmostEqual(float(app.attributes("-alpha")), 1.0, places=2)
            self.assertEqual(len(app.notebook.winfo_children()), 4)
            self.assertEqual(app.bind("<Configure>"), binding_before)

            self.assertTrue(
                app._apply_skin(gui.DEFAULT_SKIN_ID, confirm_results=False)
            )
            self.assertEqual(app.skin_id, gui.DEFAULT_SKIN_ID)
            self.assertEqual(app.bind("<Configure>"), binding_before)
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved, {"skin": gui.DEFAULT_SKIN_ID})

    def test_busy_task_blocks_skin_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            page = processing_pages(app)[0]
            old_notebook = app.notebook
            page._busy = True
            with mock.patch.object(gui.messagebox, "showwarning") as warning:
                self.assertFalse(
                    app._apply_skin("nebula_navy", confirm_results=False)
                )
            warning.assert_called_once()
            self.assertIs(app.notebook, old_notebook)
            self.assertEqual(app.skin_id, gui.DEFAULT_SKIN_ID)

    def test_preview_requires_confirmation_before_skin_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            page = processing_pages(app)[0]
            page.tree.insert("", tk.END, values=("A.JPG", "B.JPG", "JPG"))
            old_notebook = app.notebook
            with mock.patch.object(
                gui.messagebox,
                "askyesno",
                return_value=False,
            ) as confirm:
                self.assertFalse(app._apply_skin("nebula_navy"))
            confirm.assert_called_once()
            self.assertIs(app.notebook, old_notebook)
            self.assertEqual(len(page.tree.get_children()), 1)
            self.assertEqual(app.skin_id, gui.DEFAULT_SKIN_ID)

            with mock.patch.object(gui.messagebox, "askyesno", return_value=True):
                self.assertTrue(app._apply_skin("nebula_navy"))
            self.assertIsNot(app.notebook, old_notebook)
            self.assertEqual(app.skin_id, "nebula_navy")

    def test_appearance_window_shows_seven_skin_previews_without_opacity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            app.open_appearance_settings()
            app.update()
            previews = [
                widget
                for widget in all_descendants(app._appearance_window)
                if isinstance(widget, gui.SkinPreviewCard)
            ]
            self.assertEqual(
                [preview.skin_id for preview in previews],
                list(gui.SKIN_ORDER),
            )
            self.assertEqual(app.pending_skin_var.get(), gui.DEFAULT_SKIN_ID)
            widgets = all_descendants(app._appearance_window)
            self.assertFalse(any(isinstance(widget, ttk.Scale) for widget in widgets))
            labels = [
                widget.cget("text")
                for widget in widgets
                if isinstance(widget, tk.Label) and "text" in widget.keys()
            ]
            self.assertFalse(any("透明度" in str(text) for text in labels))

    def test_fixed_dark_theme_and_minimum_window_size_initialize(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            self.assertTrue(app.dark_mode)
            self.assertEqual(app.palette, gui.DARK_PALETTE)
            app.geometry("980x680")
            app.update_idletasks()
            for tab_id in app.notebook.tabs()[:3]:
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

    def test_initial_window_size_fits_common_small_and_large_screens(self) -> None:
        self.assertEqual(
            gui.PhotoAssistantApp._fit_initial_window_size(1024, 768),
            (1300, 760),
        )
        self.assertEqual(
            gui.PhotoAssistantApp._fit_initial_window_size(1920, 1080),
            (1440, 900),
        )

    def test_ui_font_prefers_requested_design_families(self) -> None:
        self.assertEqual(
            gui.PhotoAssistantApp._select_ui_font(
                ("Arial", "Noto Sans SC", "Manrope"),
                "darwin",
            ),
            "Manrope",
        )
        self.assertEqual(
            gui.PhotoAssistantApp._select_ui_font(
                ("Arial", "PingFang SC", "Noto Sans SC"),
                "darwin",
            ),
            "Noto Sans SC",
        )
        self.assertEqual(
            gui.PhotoAssistantApp._select_ui_font(
                ("Arial", "Microsoft YaHei UI", "Segoe UI Variable"),
                "win32",
            ),
            "Microsoft YaHei UI",
        )

    def test_windows_cleanup_page_uses_recycle_bin_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            gui.sys,
            "platform",
            "win32",
        ):
            app = self.make_app(Path(temp_dir) / "ui_config.json")
            cleanup_page = app.notebook.winfo_children()[1]
            texts = [
                widget.cget("text")
                for widget in all_descendants(cleanup_page)
                if isinstance(widget, (ttk.Label, ttk.Button, gui.RoundedButton))
            ]
            self.assertIn("移入回收站", texts)
            self.assertTrue(any("不在原文件夹创建额外备份" in text for text in texts))


if __name__ == "__main__":
    unittest.main()
