"""macOS 主应用与关键词快切同窗桥接的打包契约测试。"""

from __future__ import annotations

import unittest
from pathlib import Path

from photo_assistant import __version__


class MacPackagingTests(unittest.TestCase):
    def test_bundle_version_and_embedded_keyword_bridge_are_declared(self) -> None:
        project_dir = Path(__file__).resolve().parent.parent
        spec = (project_dir / "photo_assistant.spec").read_text(encoding="utf-8")
        script = (project_dir / "build_app.sh").read_text(encoding="utf-8")
        gui = (project_dir / "photo_assistant" / "gui.py").read_text(encoding="utf-8")
        bridge = (project_dir / "native" / "macos_vibrancy.m").read_text(
            encoding="utf-8"
        )
        keyword_bridge = (
            project_dir
            / "native"
            / "keyword_aligner"
            / "Sources"
            / "KeywordAlignerBridge"
            / "KeywordAlignerBridge.swift"
        ).read_text(encoding="utf-8")
        keyword_ui = (
            project_dir
            / "native"
            / "keyword_aligner"
            / "Sources"
            / "KeywordAlignerUI"
            / "ContentView.swift"
        ).read_text(encoding="utf-8")

        self.assertIn(f'"CFBundleShortVersionString": "{__version__}"', spec)
        self.assertIn('app_name = "旭影工具箱"', spec)
        self.assertIn('app_name="旭影工具箱"', script)
        self.assertIn('target_arch="arm64"', spec)
        self.assertIn('"CFBundleVersion": "23"', spec)
        self.assertIn('"LSMinimumSystemVersion": "13.0"', spec)
        self.assertIn("photo-post-assistant.embedded", spec)
        self.assertIn("build_keyword_quickcut", script)
        self.assertIn("libKeywordAlignerBridge.dylib", script)
        self.assertIn("Contents/Frameworks", script)
        self.assertNotIn("关键词快切.app", script)
        self.assertNotIn('subprocess.Popen(', gui)
        self.assertIn("build_native_vibrancy", script)
        self.assertIn("libxuying_vibrancy.dylib", spec)
        self.assertIn("NSVisualEffectView", bridge)
        self.assertIn("NSVisualEffectBlendingModeBehindWindow", bridge)
        self.assertIn('XUKeywordAlignerCreate', keyword_bridge)
        self.assertIn('XUKeywordAlignerSetTheme', keyword_bridge)
        self.assertIn('NSHostingView', keyword_bridge)
        self.assertIn('.allowsHitTesting(false)', keyword_ui)
        self.assertLess(
            script.index('sign_bundle "$keyword_framework"'),
            script.index('sign_bundle "$app_path"'),
        )


if __name__ == "__main__":
    unittest.main()
