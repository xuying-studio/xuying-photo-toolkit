"""关键词快切原生桥接在真实 Tk 主窗口中的生命周期回归测试。"""

from __future__ import annotations

import platform
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from photo_assistant import gui


@unittest.skipUnless(
    sys.platform == "darwin" and platform.machine().casefold() == "arm64",
    "仅在 Apple Silicon macOS 执行",
)
class KeywordBridgeIntegrationTests(unittest.TestCase):
    def test_native_view_reuses_handle_across_page_switches_and_releases_cleanly(
        self,
    ) -> None:
        library_path = gui._resolve_keyword_quickcut_library()
        if library_path is None:
            self.skipTest("尚未构建关键词快切动态库")

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "ui_config.json"
            with (
                mock.patch.object(gui, "UI_CONFIG_FILE", config_path),
                mock.patch.object(
                    gui,
                    "LEGACY_UI_CONFIG_FILES",
                    (config_path.with_name("legacy_ui_config.json"),),
                ),
            ):
                app = gui.PhotoAssistantApp()
                try:
                    app.update_idletasks()
                    quickcut_page = app.notebook.winfo_children()[3]
                    self.assertTrue(quickcut_page.is_available)

                    app._select_page(3)
                    app.update_idletasks()
                    quickcut_page._sync_native_view()
                    self.assertIsNotNone(quickcut_page.bridge)
                    self.assertTrue(quickcut_page.bridge.is_attached)
                    original_handle = quickcut_page.bridge.handle

                    for skin_id in gui.SKIN_ORDER:
                        quickcut_page.bridge.set_theme(skin_id)
                        self.assertEqual(quickcut_page.bridge.handle, original_handle)

                    app._select_page(0)
                    app.update()
                    self.assertEqual(quickcut_page.bridge.handle, original_handle)

                    app._select_page(3)
                    app.update_idletasks()
                    quickcut_page._sync_native_view()
                    self.assertEqual(quickcut_page.bridge.handle, original_handle)

                    quickcut_page.dispose()
                    self.assertIsNone(quickcut_page.bridge)
                finally:
                    app.destroy()


if __name__ == "__main__":
    unittest.main()
