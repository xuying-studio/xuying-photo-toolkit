"""只在真实 Windows 环境执行的回收站集成测试。"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from photo_assistant import core


@unittest.skipUnless(sys.platform == "win32", "仅在 Windows 执行")
class WindowsRecycleBinIntegrationTests(unittest.TestCase):
    def test_cleanup_and_restore_use_real_recycle_bin_without_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            support_dir = root / "应用记录"
            photo = root / f"回收站还原测试-{uuid.uuid4().hex}.jpg"
            photo.write_bytes(b"windows recycle bin integration test")
            undo_file = support_dir / "cleanup_undo.json"

            with mock.patch.object(
                core,
                "APP_SUPPORT_DIR",
                support_dir,
            ), mock.patch.object(
                core,
                "RENAME_BACKUP_DIR",
                support_dir / "rename",
            ), mock.patch.object(
                core,
                "XMP_BACKUP_DIR",
                support_dir / "xmp",
            ), mock.patch.object(
                core,
                "CLEANUP_UNDO_FILE",
                undo_file,
            ):
                moved, errors = core.move_cleanup_items_to_trash(
                    [core.CleanupItem(str(photo), "RAW")]
                )

                self.assertEqual(moved, 1)
                self.assertFalse(errors)
                self.assertFalse(photo.exists())
                record = json.loads(undo_file.read_text(encoding="utf-8"))["items"][0]
                self.assertIsNone(record["recovery_path"])
                self.assertFalse(any(root.rglob(core.RECOVERY_DIR_NAME)))

                restored, restore_errors = core.restore_latest_cleanup()

            self.assertEqual(restored, 1)
            self.assertFalse(restore_errors)
            self.assertTrue(photo.exists())
            self.assertEqual(
                photo.read_bytes(),
                b"windows recycle bin integration test",
            )


if __name__ == "__main__":
    unittest.main()
