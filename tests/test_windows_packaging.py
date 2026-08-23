"""Windows 分发包构建辅助逻辑测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.create_portable_zip import create_portable_zip


class WindowsPackagingTests(unittest.TestCase):
    def test_portable_zip_preserves_chinese_filenames_as_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "旭影的摄影工具集"
            source.mkdir()
            (source / "旭影的摄影工具集.exe").write_bytes(b"test")
            output = root / "portable.zip"

            create_portable_zip(source, output)

            with ZipFile(output) as archive:
                item = archive.infolist()[0]
                self.assertEqual(
                    item.filename,
                    "旭影的摄影工具集/旭影的摄影工具集.exe",
                )
                self.assertTrue(item.flag_bits & 0x800)


if __name__ == "__main__":
    unittest.main()
