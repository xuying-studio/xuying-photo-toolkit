#!/usr/bin/env python3
"""使用真实素材副本验证 Mac 发布候选版的四个核心工作流。"""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from xuying_toolbox.application.cleanup import CleanupUseCase
from xuying_toolbox.application.quickcut import QuickCutUseCase
from xuying_toolbox.domain.models.quickcut import ExportMode, ProjectSettings, RecognitionState
from xuying_toolbox.infrastructure.composition import (
    create_rename_use_case,
    create_xmp_sync_use_case,
)
from xuying_toolbox.infrastructure.filesystem.catalog import LocalPhotoCatalog
from xuying_toolbox.infrastructure.filesystem.quickcut_input import LocalQuickCutInputExpander
from xuying_toolbox.infrastructure.imaging.quickcut_renderer import QtQuickCutRenderer
from xuying_toolbox.infrastructure.metadata import xmp_file
from xuying_toolbox.infrastructure.ocr.macos_vision import MacVisionOCRAdapter
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.infrastructure.video.ffmpeg_export import FFmpegQuickCutExporter
from xuying_toolbox.platform.macos.trash import MacTrashAdapter

ROOT = Path(__file__).resolve().parents[1]
VERSION_LABEL = "2.0.0-rc.1"
DEFAULT_RELEASE_DIR = ROOT / "artifacts/releases" / VERSION_LABEL / "macos-arm64"
DEFAULT_WORK_DIR = ROOT / "build/stage8-macos-rc"
DEFAULT_REPORT = ROOT / "docs/stage8/macos-validation-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--photo-fixtures", type=Path, required=True)
    parser.add_argument("--quickcut-fixtures", type=Path, required=True)
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE_DIR)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def copy_fixture(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def choose_photo_pair(folder: Path) -> tuple[Path, Path]:
    raw_by_stem = {
        path.stem.casefold(): path
        for path in sorted(folder.iterdir())
        if path.suffix.casefold() in {".arw", ".cr2", ".cr3", ".nef", ".raf", ".dng"}
    }
    for jpg in sorted(folder.iterdir()):
        if jpg.suffix.casefold() not in {".jpg", ".jpeg"}:
            continue
        if raw := raw_by_stem.get(jpg.stem.casefold()):
            return raw, jpg
    raise FileNotFoundError("测试目录中没有同名 RAW/JPG 配对。")


def choose_second_jpg(folder: Path, first: Path) -> Path:
    for path in sorted(folder.iterdir()):
        if path.suffix.casefold() in {".jpg", ".jpeg"} and path.stem != first.stem:
            return path
    raise FileNotFoundError("测试目录中没有可用于孤立文件测试的第二张 JPG。")


def choose_quickcut_images(folder: Path, limit: int = 2) -> list[Path]:
    images = [
        path
        for path in sorted(folder.iterdir())
        if path.is_file() and path.suffix.casefold() in {".jpg", ".jpeg", ".png"}
    ]
    if len(images) < limit:
        raise FileNotFoundError(f"快切测试目录至少需要 {limit} 张图片。")
    return images[:limit]


def no_progress(_current: int, _total: int, _message: str) -> None:
    return None


def validate_rename(pair: tuple[Path, Path], work: Path) -> dict[str, object]:
    photos = work / "rename/photos"
    copied = [copy_fixture(path, photos / path.name) for path in pair]
    original_state = {path.name: digest(path) for path in copied}
    use_case = create_rename_use_case(SupportPaths.from_root(work / "rename/support"))

    plan = use_case.scan(photos)
    if plan.conflicts or len(plan.operations) != 2:
        raise AssertionError("真实 RAW/JPG 配对没有生成两条无冲突的重命名操作。")
    manifest = use_case.execute(plan)
    manifest_created = manifest.is_file()
    renamed_names = sorted(Path(operation.target).name for operation in plan.operations)
    if not all((photos / name).is_file() for name in renamed_names):
        raise AssertionError("重命名后的文件不完整。")
    undone = use_case.undo()
    restored_state = {path.name: digest(path) for path in copied}
    if restored_state != original_state:
        raise AssertionError("重命名撤回后文件名或内容未完整恢复。")
    return {
        "passed": True,
        "operations": len(plan.operations),
        "undoOperations": undone,
        "manifestCreated": manifest_created,
        "journalClearedAfterUndo": not manifest.exists(),
        "contentRestored": True,
    }


def validate_cleanup(pair: tuple[Path, Path], orphan: Path, work: Path) -> dict[str, object]:
    photos = work / "cleanup/photos"
    for path in pair:
        copy_fixture(path, photos / path.name)
    copied_orphan = copy_fixture(orphan, photos / orphan.name)
    orphan_digest = digest(copied_orphan)
    trash = work / "cleanup/simulated-trash"
    trash.mkdir(parents=True, exist_ok=True)

    def simulated_trash(path_value: str) -> Path:
        source = Path(path_value)
        destination = trash / source.name
        source.rename(destination)
        return destination

    support = SupportPaths.from_root(work / "cleanup/support")
    use_case = CleanupUseCase(
        LocalPhotoCatalog(),
        MacTrashAdapter(support, send_to_trash=simulated_trash),
    )
    preview = use_case.scan(photos, "JPG")
    if [Path(item.path).name for item in preview.items] != [orphan.name]:
        raise AssertionError("配对清理未精确找到孤立 JPG。")
    moved, move_errors = use_case.execute()
    if moved != 1 or move_errors or copied_orphan.exists():
        raise AssertionError("孤立 JPG 没有安全移入模拟废纸篓。")
    restored, restore_errors = use_case.restore()
    if restored != 1 or restore_errors or digest(copied_orphan) != orphan_digest:
        raise AssertionError("清理恢复后的 JPG 与原副本不一致。")
    return {
        "passed": True,
        "scannedImages": preview.total_images,
        "orphanCount": len(preview.items),
        "moved": moved,
        "restored": restored,
        "contentRestored": True,
    }


def validate_xmp(pair: tuple[Path, Path], work: Path) -> dict[str, object]:
    raw_source, jpg_source = pair
    photos = work / "xmp/photos"
    raw = copy_fixture(raw_source, photos / raw_source.name)
    jpg = copy_fixture(jpg_source, photos / jpg_source.name)
    raw_before = digest(raw)
    xmp_file.write(jpg, 5, "Select")
    jpg_with_xmp = digest(jpg)
    use_case = create_xmp_sync_use_case(SupportPaths.from_root(work / "xmp/support"))

    preview = use_case.scan(photos, "JPG → RAW", True, True)
    if len(preview.operations) != 1:
        raise AssertionError("JPG → RAW 没有生成唯一 XMP 同步操作。")
    executed, manifest = use_case.execute(preview.operations)
    sidecar = raw.with_suffix(".xmp")
    properties = xmp_file.read(raw)
    if (
        executed != 1
        or not sidecar.is_file()
        or properties.rating != 5
        or properties.label != "Select"
        or digest(raw) != raw_before
    ):
        raise AssertionError("XMP 同步结果不完整或 RAW 本体被改动。")
    undone = use_case.undo()
    if sidecar.exists() or digest(raw) != raw_before or digest(jpg) != jpg_with_xmp:
        raise AssertionError("XMP 撤回后没有恢复到执行前状态。")
    return {
        "passed": True,
        "operations": executed,
        "undoOperations": undone,
        "manifestCreated": manifest.is_file(),
        "rating": properties.rating,
        "label": properties.label,
        "rawBytesUnchanged": True,
        "sidecarRemovedAfterUndo": True,
    }


def probe_mp4(path: Path) -> dict[str, object]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return {"available": False}
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            "stream=codec_type,avg_frame_rate,nb_read_frames",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    streams = json.loads(completed.stdout).get("streams", [])
    return {"available": True, "streams": streams}


def validate_quickcut(
    sources: list[Path],
    work: Path,
    vision_library: Path,
    ffmpeg: Path,
) -> dict[str, object]:
    inputs = work / "quickcut/inputs"
    copied = [copy_fixture(path, inputs / path.name) for path in sources]
    renderer = QtQuickCutRenderer()
    use_case = QuickCutUseCase(
        MacVisionOCRAdapter(vision_library),
        FFmpegQuickCutExporter(renderer, ffmpeg_path=str(ffmpeg)),
        LocalQuickCutInputExpander(),
    )
    queue = use_case.add_inputs([inputs])
    if len(queue.added) != len(copied) or queue.duplicates or queue.ignored:
        raise AssertionError("快切输入队列未完整接收图片副本。")
    items = use_case.recognize(use_case.new_items(queue.added), "AGI", no_progress)
    if any(item.state is not RecognitionState.MATCHED for item in items):
        raise AssertionError("Apple Vision 未在所有截图副本中精确识别 AGI。")

    destination = work / "quickcut/outputs"
    results: dict[str, object] = {}
    for mode in (ExportMode.ALIGNED_PNG, ExportMode.FRAME_SEQUENCE, ExportMode.MP4):
        settings = ProjectSettings(
            keyword="AGI",
            width=360,
            height=640,
            frame_rate=30,
            frames_per_image=2,
            export_mode=mode,
        )
        result = use_case.export(items, settings, destination, no_progress)
        expected_count = len(items) if mode is ExportMode.ALIGNED_PNG else len(items) * 2
        outputs_exist = all(path.is_file() for path in result.files)
        if result.total_frames != expected_count or not outputs_exist:
            raise AssertionError(f"{mode.value} 导出的文件数或帧数不正确。")
        mode_result: dict[str, object] = {
            "fileCount": len(result.files),
            "totalFrames": result.total_frames,
            "bytes": sum(path.stat().st_size for path in result.files),
        }
        if mode is ExportMode.MP4:
            mode_result["probe"] = probe_mp4(result.files[0])
        results[mode.name] = mode_result
    return {
        "passed": True,
        "inputCount": len(items),
        "exactMatches": sum(item.state is RecognitionState.MATCHED for item in items),
        "visionLibraryFromReleaseApp": True,
        "ffmpegFromReleaseApp": True,
        "exports": results,
    }


def command_result(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def validate_release_gate(release_dir: Path) -> dict[str, object]:
    manifest_path = release_dir / "release-manifest.json"
    app = release_dir / "旭影工具箱.app"
    info_path = app / "Contents/Info.plist"
    if not manifest_path.is_file() or not info_path.is_file():
        raise FileNotFoundError("阶段 7 Mac 候选包不完整。")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    info = plistlib.loads(info_path.read_bytes())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    expected_files = {
        item["name"]: item
        for item in manifest.get("files", [])
        if item["name"].startswith("Xuying-Toolbox-")
        or item["name"] == "sources/ffmpeg-9.0.1.tar.xz"
    }
    sums = {}
    for line in (release_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected_digest, name = line.split(maxsplit=1)
        sums[name] = expected_digest
    artifact_results = []
    for name, expected in expected_files.items():
        path = release_dir / name
        artifact_results.append(
            {
                "name": name,
                "exists": path.is_file(),
                "sizeMatches": path.is_file() and path.stat().st_size == expected["size"],
                "sha256Matches": path.is_file() and digest(path) == expected["sha256"],
                "sha256SumsMatches": sums.get(name) == expected["sha256"],
            }
        )

    codesign = command_result(["codesign", "--verify", "--deep", "--strict", str(app)])
    gatekeeper = command_result(["spctl", "-a", "-vv", "--type", "execute", str(app)])
    staple = command_result(["xcrun", "stapler", "validate", str(app)])
    identities = command_result(["security", "find-identity", "-v", "-p", "codesigning"])
    git_status = command_result(["git", "status", "--porcelain"])
    expected_tag = f"v{VERSION_LABEL}"
    tag_check = command_result(["git", "tag", "--list", expected_tag])
    windows_root = ROOT / "artifacts/releases" / VERSION_LABEL / "windows-x64"

    project_version = project["project"]["version"]
    version_policy_ok = (
        project_version == "2.0.0rc1"
        and manifest.get("version") == VERSION_LABEL
        and info.get("CFBundleShortVersionString") == "2.0.0"
        and info.get("CFBundleVersion") == "1"
    )
    return {
        "candidateIntegrityPassed": all(
            item["exists"]
            and item["sizeMatches"]
            and item["sha256Matches"]
            and item["sha256SumsMatches"]
            for item in artifact_results
        ),
        "artifactChecks": artifact_results,
        "versions": {
            "projectPep440": project_version,
            "releaseLabel": manifest.get("version"),
            "bundleMarketingVersion": info.get("CFBundleShortVersionString"),
            "bundleBuild": info.get("CFBundleVersion"),
            "policyPassed": version_policy_ok,
        },
        "identity": {
            "displayName": info.get("CFBundleDisplayName"),
            "bundleId": info.get("CFBundleIdentifier"),
            "architecture": manifest.get("architecture"),
            "minimumSystem": manifest.get("minimumSystem"),
        },
        "signing": {
            "codeStructureValid": codesign.returncode == 0,
            "developerIdAvailable": "0 valid identities found"
            not in f"{identities.stdout}\n{identities.stderr}",
            "gatekeeperAccepted": gatekeeper.returncode == 0,
            "notarizationTicketStapled": staple.returncode == 0,
        },
        "publication": {
            "cleanWorktree": not git_status.stdout.strip(),
            "expectedTag": expected_tag,
            "tagExists": bool(tag_check.stdout.strip()),
            "githubRemoteConfigured": bool(
                command_result(["git", "remote", "get-url", "origin"]).stdout.strip()
            ),
            "githubReleaseVerified": False,
        },
        "windows": {
            "artifactDirectoryExists": windows_root.is_dir(),
            "realMachineAcceptancePassed": False,
        },
    }


def main() -> int:
    args = parse_args()
    if sys.platform != "darwin":
        raise RuntimeError("此验证器只允许在 macOS 运行。")
    photo_root = args.photo_fixtures.expanduser().resolve()
    quickcut_root = args.quickcut_fixtures.expanduser().resolve()
    release_dir = args.release_dir.expanduser().resolve()
    work = args.work_dir.expanduser().resolve()
    report_path = args.report.expanduser().resolve()
    if not photo_root.is_dir() or not quickcut_root.is_dir():
        raise FileNotFoundError("指定的真实测试素材目录不存在。")

    app_frameworks = release_dir / "旭影工具箱.app/Contents/Frameworks"
    vision_library = app_frameworks / "native/libXuyingVision.dylib"
    ffmpeg = app_frameworks / "bin/ffmpeg"
    if not vision_library.is_file() or not ffmpeg.is_file():
        raise FileNotFoundError("候选 App 中缺少 Vision 或 FFmpeg 组件。")

    pair = choose_photo_pair(photo_root)
    orphan = choose_second_jpg(photo_root, pair[1])
    quickcut_sources = choose_quickcut_images(quickcut_root)
    source_files = [*pair, orphan, *quickcut_sources]
    source_before = {str(path): digest(path) for path in source_files}

    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    results = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC).isoformat(),
        "platform": "macOS",
        "architecture": "arm64",
        "version": VERSION_LABEL,
        "fixturePolicy": {
            "sourceDirectoriesReadOnly": True,
            "photoPairCount": 1,
            "cleanupOrphanCount": 1,
            "quickCutImageCount": len(quickcut_sources),
            "workingCopiesInsideProjectBuild": True,
        },
        "workflows": {
            "rename": validate_rename(pair, work),
            "cleanup": validate_cleanup(pair, orphan, work),
            "xmpSync": validate_xmp(pair, work),
            "quickCut": validate_quickcut(
                quickcut_sources,
                work,
                vision_library,
                ffmpeg,
            ),
        },
        "releaseGate": validate_release_gate(release_dir),
    }
    source_after = {str(path): digest(path) for path in source_files}
    results["fixturePolicy"]["sourceBytesUnchanged"] = source_before == source_after
    if source_before != source_after:
        raise AssertionError("真实测试素材在验收过程中发生了变化。")

    gate = results["releaseGate"]
    workflows_passed = all(workflow["passed"] for workflow in results["workflows"].values())
    signing = gate["signing"]
    publication = gate["publication"]
    windows = gate["windows"]
    results["summary"] = {
        "macWorkflowRegressionPassed": workflows_passed,
        "macCandidateIntegrityPassed": gate["candidateIntegrityPassed"],
        "formalMacReleaseReady": all(signing.values()) and publication["cleanWorktree"],
        "crossPlatformReleaseReady": all(signing.values())
        and publication["cleanWorktree"]
        and windows["artifactDirectoryExists"]
        and windows["realMachineAcceptancePassed"],
        "status": "internal-rc-validated",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(results["summary"], ensure_ascii=False, indent=2))
    print(f"报告：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
