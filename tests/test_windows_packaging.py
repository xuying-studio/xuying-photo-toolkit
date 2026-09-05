"""Windows 分发包构建辅助逻辑测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from photo_assistant import __version__
from scripts.create_portable_zip import create_portable_zip


class WindowsPackagingTests(unittest.TestCase):
    def test_windows_metadata_matches_app_version(self) -> None:
        project_dir = Path(__file__).resolve().parent.parent
        installer = (project_dir / "installer.iss").read_text(encoding="utf-8")
        manifest = (project_dir / "windows_app.manifest").read_text(encoding="utf-8")
        version_info = (project_dir / "windows_version_info.txt").read_text(
            encoding="utf-8"
        )

        self.assertIn(f'#define AppVersion "{__version__}"', installer)
        self.assertIn(f'version="{__version__}.0"', manifest)
        self.assertIn(
            f"StringStruct('ProductVersion', '{__version__}.0')",
            version_info,
        )

    def test_portable_zip_preserves_chinese_filenames_as_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "旭影工具箱"
            source.mkdir()
            (source / "旭影工具箱.exe").write_bytes(b"test")
            output = root / "portable.zip"

            create_portable_zip(source, output)

            with ZipFile(output) as archive:
                item = archive.infolist()[0]
                self.assertEqual(
                    item.filename,
                    "旭影工具箱/旭影工具箱.exe",
                )
                self.assertTrue(item.flag_bits & 0x800)


if __name__ == "__main__":
    unittest.main()
