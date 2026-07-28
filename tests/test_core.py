"""核心功能的无损临时目录测试。"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from photo_assistant import core


MINIMAL_JPEG = b"\xff\xd8\xff\xd9"


def assert_progress_complete(
    test_case: unittest.TestCase,
    updates: list[tuple[int, int, str]],
) -> None:
    """确认任务持续上报进度，并在总量位置结束。"""

    test_case.assertTrue(updates)
    current, total, message = updates[-1]
    test_case.assertGreater(total, 0)
    test_case.assertEqual(current, total)
    test_case.assertTrue(message)


class RenameTests(unittest.TestCase):
    def test_rename_raw_jpg_and_sidecar_then_undo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "DSC0001.ARW"
            jpg = root / "DSC0001.JPG"
            sidecar = root / "DSC0001.xmp"
            raw.write_bytes(b"raw")
            jpg.write_bytes(MINIMAL_JPEG)
            sidecar.write_text("<xmp:Rating>5</xmp:Rating>", encoding="utf-8")
            timestamp = datetime(2026, 7, 25, 10, 0).timestamp()
            for path in (raw, jpg, sidecar):
                os.utime(path, (timestamp, timestamp))

            backup_dir = root / "rename_backups"
            with mock.patch.object(core, "RENAME_BACKUP_DIR", backup_dir), mock.patch.object(
                core,
                "APP_SUPPORT_DIR",
                root,
            ), mock.patch.object(core, "XMP_BACKUP_DIR", root / "xmp"):
                scan_updates: list[tuple[int, int, str]] = []
                execute_updates: list[tuple[int, int, str]] = []
                undo_updates: list[tuple[int, int, str]] = []
                plan = core.build_rename_plan(
                    root,
                    progress=lambda *update: scan_updates.append(update),
                )
                self.assertEqual(plan.image_count, 2)
                self.assertFalse(plan.conflicts)
                self.assertEqual(plan.stats.total_images, 2)
                self.assertEqual(plan.stats.raw_count, 1)
                self.assertEqual(plan.stats.jpg_count, 1)
                self.assertEqual(plan.stats.xmp_count, 1)
                assert_progress_complete(self, scan_updates)
                self.assertTrue(
                    all(current < total for current, total, _ in scan_updates[:-1])
                )
                self.assertTrue(
                    any("正在生成重命名预览" in message for _, _, message in scan_updates)
                )
                core.execute_rename_plan(
                    plan,
                    progress=lambda *update: execute_updates.append(update),
                )
                assert_progress_complete(self, execute_updates)

                self.assertTrue((root / "DSC26-07-25-00001.arw").exists())
                self.assertTrue((root / "DSC26-07-25-00001.jpg").exists())
                self.assertTrue((root / "DSC26-07-25-00001.xmp").exists())

                restored = core.undo_latest_rename(
                    progress=lambda *update: undo_updates.append(update),
                )
                self.assertEqual(restored, 3)
                assert_progress_complete(self, undo_updates)
                self.assertTrue(raw.exists())
                self.assertTrue(jpg.exists())
                self.assertTrue(sidecar.exists())

    def test_existing_formatted_file_is_kept_and_counter_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "DSC0001.JPG"
            source.write_bytes(MINIMAL_JPEG)
            timestamp = datetime(2026, 7, 25).timestamp()
            os.utime(source, (timestamp, timestamp))
            (root / "DSC26-07-25-00001.jpg").write_bytes(MINIMAL_JPEG)

            plan = core.build_rename_plan(root)
            self.assertFalse(plan.conflicts)
            self.assertEqual(
                Path(plan.operations[0].target).name,
                "DSC26-07-25-00002.jpg",
            )


class CleanupTests(unittest.TestCase):
    def test_recursive_case_insensitive_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "子目录"
            nested.mkdir()
            (nested / "A001.JPG").write_bytes(MINIMAL_JPEG)
            (nested / "a001.ArW").write_bytes(b"raw")
            orphan = nested / "A002.JPG"
            orphan.write_bytes(MINIMAL_JPEG)

            plan = core.build_cleanup_plan(root, "JPG", recursive=True)
            self.assertEqual([Path(item.path).name for item in plan], [orphan.name])
            scan_updates: list[tuple[int, int, str]] = []
            result = core.scan_cleanup(
                root,
                "JPG",
                recursive=True,
                progress=lambda *update: scan_updates.append(update),
            )
            self.assertEqual(result.total_images, 3)
            self.assertEqual(result.raw_count, 1)
            self.assertEqual(result.jpg_count, 2)
            self.assertEqual(result.target_count, 2)
            self.assertEqual(result.paired_target_count, 1)
            self.assertEqual(len(result.items), 1)
            assert_progress_complete(self, scan_updates)

    def test_restore_uses_recorded_trash_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original_dir = root / "照片"
            trash_dir = root / "模拟废纸篓"
            original_dir.mkdir()
            trash_dir.mkdir()
            trashed = trash_dir / "A001.jpg"
            trashed.write_bytes(MINIMAL_JPEG)
            original = original_dir / "A001.jpg"
            undo_file = root / "cleanup_undo.json"
            undo_file.write_text(
                json.dumps(
                    {
                        "paths": [str(original)],
                        "items": [
                            {
                                "original_path": str(original),
                                "trash_path": str(trashed),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.object(core, "CLEANUP_UNDO_FILE", undo_file):
                restored, errors = core.restore_latest_cleanup()

            self.assertEqual(restored, 1)
            self.assertFalse(errors)
            self.assertTrue(original.exists())
            self.assertFalse(undo_file.exists())

    def test_finder_fallback_does_not_enumerate_trash(self) -> None:
        completed = mock.Mock(returncode=0, stdout="OK\n", stderr="")
        with mock.patch.object(core.subprocess, "run", return_value=completed) as run_mock:
            succeeded, error = core._restore_with_finder(Path("/tmp/照片/A001.jpg"))

        self.assertTrue(succeeded)
        self.assertIsNone(error)
        script = run_mock.call_args.args[0][-1]
        self.assertNotIn("every item of trash", script)
        self.assertIn('item "A001.jpg" of trash', script)

    def test_cleanup_recovery_does_not_depend_on_trash_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            photo = root / "A001.jpg"
            fake_trash = root / "系统废纸篓"
            fake_trash.mkdir()
            photo.write_bytes(MINIMAL_JPEG)
            undo_file = root / "cleanup_undo.json"

            def fake_send_to_trash(path: str) -> None:
                Path(path).rename(fake_trash / Path(path).name)

            with mock.patch.object(core, "APP_SUPPORT_DIR", root), mock.patch.object(
                core,
                "RENAME_BACKUP_DIR",
                root / "rename",
            ), mock.patch.object(core, "XMP_BACKUP_DIR", root / "xmp"), mock.patch.object(
                core,
                "CLEANUP_UNDO_FILE",
                undo_file,
            ), mock.patch.object(
                core,
                "send2trash",
                side_effect=fake_send_to_trash,
            ), mock.patch.object(
                core,
                "_trash_dir_for_path",
                return_value=fake_trash,
            ):
                execute_updates: list[tuple[int, int, str]] = []
                restore_updates: list[tuple[int, int, str]] = []
                moved, errors = core.move_cleanup_items_to_trash(
                    [core.CleanupItem(str(photo), "RAW")],
                    progress=lambda *update: execute_updates.append(update),
                )
                self.assertEqual(moved, 1)
                self.assertFalse(errors)
                self.assertFalse(photo.exists())
                assert_progress_complete(self, execute_updates)

                payload = json.loads(undo_file.read_text(encoding="utf-8"))
                recovery_path = Path(payload["items"][0]["recovery_path"])
                self.assertTrue(recovery_path.exists())

                restored, restore_errors = core.restore_latest_cleanup(
                    progress=lambda *update: restore_updates.append(update),
                )

            self.assertEqual(restored, 1)
            self.assertFalse(restore_errors)
            assert_progress_complete(self, restore_updates)
            self.assertTrue(photo.exists())
            self.assertEqual(photo.read_bytes(), MINIMAL_JPEG)
            self.assertTrue((fake_trash / photo.name).exists())


class XmpTests(unittest.TestCase):
    def test_jpeg_without_xmp_gets_valid_embedded_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            jpg = Path(temp_dir) / "A001.jpg"
            jpg.write_bytes(MINIMAL_JPEG)

            core._write_properties(jpg, 4, "Select")

            data = jpg.read_bytes()
            self.assertTrue(data.startswith(b"\xff\xd8\xff\xe1"))
            self.assertIn(core.XMP_JPEG_HEADER, data)
            self.assertEqual(core.read_xmp_properties(jpg), (4, "Select"))

    def test_sync_scan_statistics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for number, rating in (("001", 5), ("002", 0)):
                jpg = root / f"A{number}.jpg"
                raw = root / f"A{number}.ARW"
                jpg.write_bytes(core._insert_jpeg_xmp(MINIMAL_JPEG, rating, None))
                raw.write_bytes(b"raw")

            result = core.scan_sync(root, "JPG → RAW", True, False)

            self.assertEqual(result.total_images, 4)
            self.assertEqual(result.source_count, 2)
            self.assertEqual(result.target_count, 2)
            self.assertEqual(result.matched_count, 2)
            self.assertEqual(result.marked_count, 1)
            self.assertEqual(len(result.operations), 1)

    def test_raw_sync_creates_sidecar_and_undo_removes_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            jpg = root / "A001.jpg"
            raw = root / "A001.ARW"
            jpg.write_bytes(core._insert_jpeg_xmp(MINIMAL_JPEG, 5, "Approved"))
            raw.write_bytes(b"raw")

            support = root / "support"
            xmp_backups = support / "xmp_backups"
            with mock.patch.object(core, "APP_SUPPORT_DIR", support), mock.patch.object(
                core,
                "RENAME_BACKUP_DIR",
                support / "rename",
            ), mock.patch.object(core, "XMP_BACKUP_DIR", xmp_backups):
                scan_updates: list[tuple[int, int, str]] = []
                execute_updates: list[tuple[int, int, str]] = []
                undo_updates: list[tuple[int, int, str]] = []
                plan = core.build_sync_plan(
                    root,
                    "JPG → RAW",
                    True,
                    True,
                    progress=lambda *update: scan_updates.append(update),
                )
                self.assertEqual(len(plan), 1)
                assert_progress_complete(self, scan_updates)
                count, manifest = core.execute_sync_plan(
                    plan,
                    progress=lambda *update: execute_updates.append(update),
                )
                self.assertEqual(count, 1)
                assert_progress_complete(self, execute_updates)
                self.assertTrue(manifest.exists())
                self.assertEqual(core.read_xmp_properties(raw), (5, "Approved"))

                restored = core.undo_latest_sync(
                    progress=lambda *update: undo_updates.append(update),
                )
                self.assertEqual(restored, 1)
                assert_progress_complete(self, undo_updates)
                self.assertFalse(raw.with_suffix(".xmp").exists())

    def test_sync_manifest_contains_full_jpeg_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "A001.ARW"
            sidecar = root / "A001.xmp"
            jpg = root / "A001.jpg"
            raw.write_bytes(b"raw")
            sidecar.write_bytes(core._make_xmp_xml(3, "Review"))
            jpg.write_bytes(MINIMAL_JPEG)

            support = root / "support"
            with mock.patch.object(core, "APP_SUPPORT_DIR", support), mock.patch.object(
                core,
                "RENAME_BACKUP_DIR",
                support / "rename",
            ), mock.patch.object(core, "XMP_BACKUP_DIR", support / "xmp_backups"):
                plan = core.build_sync_plan(root, "RAW → JPG", True, True)
                _, manifest = core.execute_sync_plan(plan)
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                backup_name = payload["entries"][0]["backup_name"]
                self.assertEqual((manifest.parent / backup_name).read_bytes(), MINIMAL_JPEG)

    def test_partial_sync_failure_rolls_back_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for number in ("001", "002"):
                jpg = root / f"A{number}.jpg"
                raw = root / f"A{number}.ARW"
                jpg.write_bytes(core._insert_jpeg_xmp(MINIMAL_JPEG, 5, "Select"))
                raw.write_bytes(b"raw")

            support = root / "support"
            with mock.patch.object(core, "APP_SUPPORT_DIR", support), mock.patch.object(
                core,
                "RENAME_BACKUP_DIR",
                support / "rename",
            ), mock.patch.object(core, "XMP_BACKUP_DIR", support / "xmp_backups"):
                plan = core.build_sync_plan(root, "JPG → RAW", True, True)
                original_write = core._write_properties
                call_count = 0

                def fail_on_second(path: Path, rating: int | None, label: str | None) -> None:
                    nonlocal call_count
                    call_count += 1
                    if call_count == 2:
                        raise OSError("模拟第二个目标写入失败")
                    original_write(path, rating, label)

                with mock.patch.object(core, "_write_properties", side_effect=fail_on_second):
                    with self.assertRaises(OSError):
                        core.execute_sync_plan(plan)

                self.assertFalse((root / "A001.xmp").exists())
                self.assertFalse((root / "A002.xmp").exists())


if __name__ == "__main__":
    unittest.main()
