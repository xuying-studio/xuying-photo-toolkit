"""核心功能的无损临时目录测试。"""

from __future__ import annotations

import json
import os
import sys
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
    def test_non_recursive_rename_ignores_backup_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup = root / "备份"
            backup.mkdir()
            for folder in (root, backup):
                (folder / "B_DSC09252.ARW").write_bytes(b"raw")
                (folder / "B_DSC09252.JPG").write_bytes(MINIMAL_JPEG)

            plan = core.build_rename_plan(root, recursive=False)

            self.assertEqual(plan.stats.total_images, 2)
            self.assertEqual(plan.image_count, 2)
            self.assertTrue(
                all(Path(operation.source).parent == root for operation in plan.operations)
            )
            target_stems = {
                Path(operation.target).stem for operation in plan.operations
            }
            self.assertEqual(len(target_stems), 1)
            self.assertTrue(next(iter(target_stems)).endswith("-00001"))

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
    def test_non_recursive_cleanup_ignores_backup_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup = root / "备份"
            backup.mkdir()
            current = root / "A001.JPG"
            nested = backup / "A002.JPG"
            current.write_bytes(MINIMAL_JPEG)
            nested.write_bytes(MINIMAL_JPEG)

            result = core.scan_cleanup(
                root,
                "JPG",
                recursive=False,
            )

            self.assertEqual(result.total_images, 1)
            self.assertEqual(result.target_count, 1)
            self.assertEqual([Path(item.path) for item in result.items], [current])

    def test_windows_app_data_uses_roaming_profile(self) -> None:
        roaming = str(Path("C:/Users/test/AppData/Roaming"))
        with mock.patch.object(core.sys, "platform", "win32"), mock.patch.dict(
            core.os.environ,
            {"APPDATA": roaming},
        ):
            self.assertEqual(
                core.app_data_dir("旭影的摄影工具集"),
                Path(roaming) / "旭影的摄影工具集",
            )

    def test_windows_trash_is_managed_by_system_api(self) -> None:
        with mock.patch.object(core.sys, "platform", "win32"):
            self.assertIsNone(core._trash_dir_for_path(Path("C:/照片/A001.jpg")))

    def test_windows_directory_identity_accepts_short_path_alias(self) -> None:
        with mock.patch.object(core.os.path, "samefile", return_value=True):
            self.assertTrue(
                core._same_windows_directory(
                    r"C:\Users\RUNNER~1\Temp",
                    r"C:\Users\runneradmin\Temp",
                )
            )

    def test_windows_restore_fallback_never_calls_finder(self) -> None:
        with mock.patch.object(core.sys, "platform", "win32"), mock.patch.object(
            core,
            "_restore_with_finder",
        ) as finder_mock, mock.patch.object(
            core,
            "_restore_from_windows_recycle_bin",
            return_value=(True, None),
        ) as recycle_mock:
            succeeded, error = core._restore_with_platform_fallback(
                Path("C:/照片/A001.jpg"),
                {"deleted_at": "2026-08-23T12:00:00+08:00"},
            )

        self.assertTrue(succeeded)
        self.assertIsNone(error)
        finder_mock.assert_not_called()
        recycle_mock.assert_called_once()

    def test_windows_cleanup_uses_only_recycle_bin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            photo = root / "A001.jpg"
            recycle_bin = root / "模拟回收站"
            recycle_bin.mkdir()
            photo.write_bytes(MINIMAL_JPEG)
            undo_file = root / "cleanup_undo.json"

            def fake_send_to_trash(path: str) -> None:
                Path(path).rename(recycle_bin / Path(path).name)

            def fake_restore(
                original: Path,
                deleted_at: str | None,
            ) -> tuple[bool, str | None]:
                self.assertIsNotNone(deleted_at)
                (recycle_bin / original.name).replace(original)
                return True, None

            with mock.patch.object(core.sys, "platform", "win32"), mock.patch.object(
                core,
                "APP_SUPPORT_DIR",
                root,
            ), mock.patch.object(
                core,
                "RENAME_BACKUP_DIR",
                root / "rename",
            ), mock.patch.object(
                core,
                "XMP_BACKUP_DIR",
                root / "xmp",
            ), mock.patch.object(
                core,
                "CLEANUP_UNDO_FILE",
                undo_file,
            ), mock.patch.object(
                core,
                "send2trash",
                side_effect=fake_send_to_trash,
            ), mock.patch.object(
                core,
                "_restore_from_windows_recycle_bin",
                side_effect=fake_restore,
            ):
                moved, errors = core.move_cleanup_items_to_trash(
                    [core.CleanupItem(str(photo), "RAW")]
                )
                self.assertEqual(moved, 1)
                self.assertFalse(errors)
                record = json.loads(undo_file.read_text(encoding="utf-8"))["items"][0]
                self.assertIsNone(record["trash_path"])
                self.assertIsNone(record["recovery_path"])
                self.assertIsNotNone(record["deleted_at"])
                self.assertFalse((root / core.RECOVERY_DIR_NAME).exists())

                restored, restore_errors = core.restore_latest_cleanup()

            self.assertEqual(restored, 1)
            self.assertFalse(restore_errors)
            self.assertTrue(photo.exists())

    def test_windows_recycle_restore_uses_low_level_shell_move(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            original = root / "A001.jpg"

            def fake_move(source: str | Path, target: str | Path) -> None:
                self.assertEqual(source, r"C:\$Recycle.Bin\$RTEST.jpg")
                self.assertEqual(Path(target), original)
                original.write_bytes(MINIMAL_JPEG)
                return None

            fake_pythoncom = mock.Mock()

            with mock.patch.object(
                core,
                "_pythoncom",
                fake_pythoncom,
            ), mock.patch.object(
                core,
                "_pywintypes",
                mock.Mock(),
            ), mock.patch.object(
                core,
                "_win32_shell",
                mock.Mock(),
            ), mock.patch.object(
                core,
                "_win32_shellcon",
                mock.Mock(),
            ), mock.patch.object(
                core,
                "_find_windows_recycled_path",
                return_value=(r"C:\$Recycle.Bin\$RTEST.jpg", None),
            ) as find_mock, mock.patch.object(
                core,
                "_move_windows_shell_path",
                side_effect=fake_move,
            ) as move_mock:
                succeeded, error = core._restore_from_windows_recycle_bin(
                    original,
                    core.datetime.now().astimezone().isoformat(),
                )

            self.assertTrue(succeeded)
            self.assertIsNone(error)
            find_mock.assert_called_once()
            move_mock.assert_called_once()
            fake_pythoncom.CoInitialize.assert_called_once_with()
            fake_pythoncom.CoUninitialize.assert_called_once_with()

    def test_windows_shell_move_accepts_two_value_pywin32_result(self) -> None:
        fake_shell = mock.Mock()
        fake_shell.SHFileOperation.return_value = (0, False)
        fake_shellcon = mock.Mock()
        fake_shellcon.FOF_NOCONFIRMATION = 16
        fake_shellcon.FOF_NOERRORUI = 1024
        fake_shellcon.FOF_SILENT = 4
        fake_shellcon.FO_MOVE = 1

        with mock.patch.object(
            core,
            "_win32_shell",
            fake_shell,
        ), mock.patch.object(
            core,
            "_win32_shellcon",
            fake_shellcon,
        ):
            error = core._move_windows_shell_path(
                r"C:\$Recycle.Bin\$RTEST.jpg",
                r"C:\照片\A001.jpg",
            )

        self.assertIsNone(error)
        fake_shell.SHFileOperation.assert_called_once()

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

    @unittest.skipIf(sys.platform == "win32", "Windows 直接使用系统回收站")
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
    @staticmethod
    def jpeg_with_xmp(xml: bytes) -> bytes:
        payload = core.XMP_JPEG_HEADER + xml
        segment_length = len(payload) + 2
        segment = b"\xff\xe1" + segment_length.to_bytes(2, "big") + payload
        return MINIMAL_JPEG[:2] + segment + MINIMAL_JPEG[2:]

    def test_raw_xmp_reads_alternate_prefix_single_quotes_and_utf16(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "A001.ARW"
            raw.write_bytes(b"raw")
            xml = """<?xml version='1.0' encoding='UTF-16'?>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
         xmlns:xap='http://ns.adobe.com/xap/1.0/'>
  <rdf:Description xap:Rating='2' />
</rdf:RDF>"""
            raw.with_suffix(".xmp").write_bytes(xml.encode("utf-16"))

            self.assertEqual(core.read_xmp_properties(raw), (2, None))

    def test_newest_duplicate_raw_sidecar_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "A001.ARW"
            raw.write_bytes(b"raw")
            standard = root / "A001.xmp"
            legacy = root / "A001.ARW.xmp"
            standard.write_text("<xmp:Rating>1</xmp:Rating>", encoding="utf-8")
            legacy.write_text("<xmp:Rating>2</xmp:Rating>", encoding="utf-8")
            os.utime(standard, (1_000, 1_000))
            os.utime(legacy, (2_000, 2_000))

            self.assertEqual(core._preferred_sidecar(raw), legacy)
            self.assertEqual(core.read_xmp_properties(raw), (2, None))

    def test_raw_to_jpg_sync_keeps_four_one_star_and_four_two_star(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            expected_ratings: dict[str, int] = {}
            for index in range(8):
                rating = 1 if index < 4 else 2
                stem = f"IMG{index + 1:04d}"
                raw = root / f"{stem}.ARW"
                jpg = root / f"{stem}.JPG"
                sidecar = root / f"{stem}.xmp"
                raw.write_bytes(b"raw")
                jpg.write_bytes(MINIMAL_JPEG)
                if index == 7:
                    xml = f"""<?xml version='1.0' encoding='UTF-16'?>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
         xmlns:xap='http://ns.adobe.com/xap/1.0/'>
  <rdf:Description xap:Rating='{rating}' />
</rdf:RDF>"""
                    sidecar.write_bytes(xml.encode("utf-16"))
                elif index >= 4:
                    sidecar.write_text(
                        "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
                        "xmlns:xap='http://ns.adobe.com/xap/1.0/'>"
                        f"<rdf:Description><xap:Rating> {rating} </xap:Rating>"
                        "</rdf:Description></rdf:RDF>",
                        encoding="utf-8",
                    )
                else:
                    sidecar.write_text(
                        "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
                        "xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
                        f"<rdf:Description xmp:Rating=\"{rating}\" />"
                        "</rdf:RDF>",
                        encoding="utf-8",
                    )
                expected_ratings[jpg.name] = rating

            with mock.patch.object(
                core,
                "_pair_for",
                side_effect=AssertionError("同步扫描不应逐张遍历目录"),
            ):
                result = core.scan_sync(root, "RAW → JPG", True, False)

            self.assertEqual(result.source_count, 8)
            self.assertEqual(result.target_count, 8)
            self.assertEqual(result.matched_count, 8)
            self.assertEqual(result.marked_count, 8)
            self.assertEqual(result.up_to_date_count, 0)
            self.assertEqual(len(result.operations), 8)
            self.assertEqual(
                sorted(operation.rating for operation in result.operations),
                [1, 1, 1, 1, 2, 2, 2, 2],
            )

            support = root / "support"
            with mock.patch.object(core, "APP_SUPPORT_DIR", support), mock.patch.object(
                core,
                "RENAME_BACKUP_DIR",
                support / "rename",
            ), mock.patch.object(
                core,
                "XMP_BACKUP_DIR",
                support / "xmp",
            ):
                count, _ = core.execute_sync_plan(result.operations)

            self.assertEqual(count, 8)
            for jpg_name, rating in expected_ratings.items():
                self.assertEqual(core.read_xmp_properties(root / jpg_name)[0], rating)

    def test_raw_to_jpg_updates_existing_xap_packet_without_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "A001.ARW"
            jpg = root / "A001.JPG"
            raw.write_bytes(b"raw")
            raw.with_suffix(".xmp").write_text(
                "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
                "xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
                "<rdf:Description xmp:Rating='2' /></rdf:RDF>",
                encoding="utf-8",
            )
            existing_xap = (
                b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
                b"xmlns:xap='http://ns.adobe.com/xap/1.0/'>"
                b"<rdf:Description><xap:CreatorTool>Adobe Bridge</xap:CreatorTool>"
                b"</rdf:Description></rdf:RDF>"
            )
            exif_payload = b"Exif\x00\x00camera-metadata"
            exif_segment = (
                b"\xff\xe1"
                + (len(exif_payload) + 2).to_bytes(2, "big")
                + exif_payload
            )
            jpeg_content = self.jpeg_with_xmp(existing_xap)
            jpg.write_bytes(jpeg_content[:2] + exif_segment + jpeg_content[2:])

            result = core.scan_sync(root, "RAW → JPG", True, False)
            self.assertEqual(len(result.operations), 1)

            support = root / "support"
            with mock.patch.object(core, "APP_SUPPORT_DIR", support), mock.patch.object(
                core,
                "RENAME_BACKUP_DIR",
                support / "rename",
            ), mock.patch.object(
                core,
                "XMP_BACKUP_DIR",
                support / "xmp",
            ):
                count, _ = core.execute_sync_plan(result.operations)

            updated = jpg.read_bytes()
            segment = core._find_jpeg_xmp_segment(updated)
            self.assertEqual(count, 1)
            self.assertIsNotNone(segment)
            assert segment is not None
            stored_length = int.from_bytes(
                updated[segment.start + 2:segment.start + 4],
                "big",
            )
            self.assertEqual(stored_length, len(segment.payload) + 2)
            self.assertEqual(segment.end - segment.start, stored_length + 2)
            self.assertEqual(updated.count(core.XMP_JPEG_HEADER), 1)
            self.assertIn(exif_payload, updated)
            self.assertIn(b"<xap:CreatorTool>Adobe Bridge</xap:CreatorTool>", updated)
            self.assertIn(b"<xap:Rating>2</xap:Rating>", updated)
            self.assertEqual(core.read_xmp_properties(jpg)[0], 2)

    def test_jpg_rating_scan_reads_xmp_segment_without_full_file_reader(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            jpg = root / "A001.JPG"
            xmp = (
                b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
                b"xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
                b"<rdf:Description xmp:Rating='2' /></rdf:RDF>"
            )
            jpg.write_bytes(
                self.jpeg_with_xmp(xmp)[:-2]
                + b"\xff\xda\x00\x08"
                + b"compressed-pixel-data" * 100_000
            )

            with mock.patch.object(
                core,
                "_read_bytes",
                side_effect=AssertionError("JPG 不应整文件读取"),
            ):
                self.assertEqual(core.read_xmp_properties(jpg), (2, None))

    def test_non_recursive_sync_ignores_marked_backup_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup = root / "备份"
            backup.mkdir()
            for folder, stem in ((root, "A001"), (backup, "A002")):
                (folder / f"{stem}.ARW").write_bytes(b"raw")
                (folder / f"{stem}.JPG").write_bytes(MINIMAL_JPEG)
                (folder / f"{stem}.xmp").write_text(
                    "<xmp:Rating>2</xmp:Rating>",
                    encoding="utf-8",
                )

            result = core.scan_sync(
                root,
                "RAW → JPG",
                True,
                False,
                recursive=False,
            )

            self.assertEqual(result.source_count, 1)
            self.assertEqual(result.matched_count, 1)
            self.assertEqual(len(result.operations), 1)
            self.assertEqual(Path(result.operations[0].source).parent, root)

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
