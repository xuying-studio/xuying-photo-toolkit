"""关键词快切的 PNG、帧序列和无声 MP4 导出。"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from xuying_toolbox.domain.models.quickcut import ExportMode, ProjectSettings
from xuying_toolbox.domain.ports.quickcut_export import (
    QuickCutExportResult,
    QuickCutExportSource,
)
from xuying_toolbox.domain.services.progress import ProgressCallback
from xuying_toolbox.domain.services.quickcut import Timeline, frame_rate_fraction
from xuying_toolbox.infrastructure.imaging.quickcut_renderer import QtQuickCutRenderer


class QuickCutExportError(RuntimeError):
    """渲染或视频编码失败。"""


def safe_output_stem(keyword: str) -> str:
    cleaned = "".join(character if character.isalnum() else "-" for character in keyword)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned[:48] or "quickcut"


def default_ffmpeg_path() -> str | None:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled = Path(bundle_root) / "bin/ffmpeg"
        if bundled.is_file():
            return str(bundled)
    for candidate in (Path("/opt/homebrew/bin/ffmpeg"), Path("/usr/local/bin/ffmpeg")):
        if candidate.is_file():
            return str(candidate)
    return shutil.which("ffmpeg")


def default_video_encoder() -> str:
    # Mac 发布包使用系统 VideoToolbox，避免捆绑 GPL 编码库。
    return "h264_videotoolbox" if sys.platform == "darwin" else "libx264"


class FFmpegQuickCutExporter:
    def __init__(
        self,
        renderer: QtQuickCutRenderer | None = None,
        *,
        ffmpeg_path: str | None = None,
        video_encoder: str | None = None,
        now=None,
    ) -> None:
        self._renderer = renderer or QtQuickCutRenderer()
        self._ffmpeg_path = ffmpeg_path or default_ffmpeg_path()
        self._video_encoder = video_encoder or default_video_encoder()
        self._now = now or datetime.now

    def export(
        self,
        sources: tuple[QuickCutExportSource, ...],
        settings: ProjectSettings,
        destination: Path,
        progress: ProgressCallback,
    ) -> QuickCutExportResult:
        if not sources:
            raise QuickCutExportError("请先导入图片。")
        if message := settings.validation_message:
            raise QuickCutExportError(message)

        final_directory, partial_directory = self._reserve_directory(
            destination,
            safe_output_stem(settings.keyword),
        )
        try:
            if settings.export_mode is ExportMode.ALIGNED_PNG:
                files = self._export_aligned(sources, settings, partial_directory, progress)
                total_frames = len(files)
            else:
                frame_files = self._export_frames(sources, settings, partial_directory, progress)
                total_frames = len(frame_files)
                if settings.export_mode is ExportMode.MP4:
                    files = (self._encode_mp4(partial_directory, settings),)
                    for frame in frame_files:
                        frame.unlink()
                    (partial_directory / "frames").rmdir()
                else:
                    files = frame_files
            partial_directory.rename(final_directory)
        except Exception:
            shutil.rmtree(partial_directory, ignore_errors=True)
            raise
        return QuickCutExportResult(
            directory=final_directory,
            files=tuple(final_directory / path.relative_to(partial_directory) for path in files),
            total_frames=total_frames,
        )

    def _reserve_directory(self, destination: Path, stem: str) -> tuple[Path, Path]:
        destination.mkdir(parents=True, exist_ok=True)
        timestamp = self._now().strftime("%Y%m%d-%H%M%S")
        base = f"{stem}-{timestamp}"
        suffix = 0
        while True:
            name = base if suffix == 0 else f"{base}-{suffix}"
            final = destination / name
            partial = destination / f".{name}.partial"
            if not final.exists() and not partial.exists():
                partial.mkdir()
                return final, partial
            suffix += 1

    def _export_aligned(
        self,
        sources: tuple[QuickCutExportSource, ...],
        settings: ProjectSettings,
        directory: Path,
        progress: ProgressCallback,
    ) -> tuple[Path, ...]:
        files: list[Path] = []
        for index, source in enumerate(sources, start=1):
            progress(index - 1, len(sources), f"正在渲染 {source.path.name}")
            output = directory / f"{index:03d}-{safe_output_stem(source.path.stem)}.png"
            self._renderer.save_png(
                self._renderer.render(source.path, source.source_box, settings),
                output,
            )
            files.append(output)
        progress(len(sources), len(sources), "处理后 PNG 已生成")
        return tuple(files)

    def _export_frames(
        self,
        sources: tuple[QuickCutExportSource, ...],
        settings: ProjectSettings,
        directory: Path,
        progress: ProgressCallback,
    ) -> tuple[Path, ...]:
        frames_directory = directory / "frames"
        frames_directory.mkdir()
        timeline = Timeline(len(sources), settings.frames_per_image, settings.frame_rate)
        files: list[Path] = []
        frame_number = 1
        for source in sources:
            image = self._renderer.render(source.path, source.source_box, settings)
            for _ in range(settings.frames_per_image):
                progress(frame_number - 1, timeline.total_frames, f"正在生成第 {frame_number} 帧")
                output = frames_directory / f"{frame_number:06d}.png"
                self._renderer.save_png(image, output)
                files.append(output)
                frame_number += 1
        progress(timeline.total_frames, timeline.total_frames, "PNG 帧序列已生成")
        return tuple(files)

    def _encode_mp4(self, directory: Path, settings: ProjectSettings) -> Path:
        if not self._ffmpeg_path:
            raise QuickCutExportError("找不到 FFmpeg，暂时无法导出 MP4。")
        rate = frame_rate_fraction(settings.frame_rate)
        output = directory / f"{safe_output_stem(settings.keyword)}-effect.mp4"
        command = [
            self._ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            f"{rate.numerator}/{rate.denominator}",
            "-i",
            str(directory / "frames/%06d.png"),
            "-c:v",
            self._video_encoder,
        ]
        if self._video_encoder == "h264_videotoolbox":
            command.extend(["-b:v", "8M", "-allow_sw", "1"])
        command.extend(
            [
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(output),
            ]
        )
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "FFmpeg 返回未知错误。"
            raise QuickCutExportError(f"MP4 编码失败：{detail}")
        return output
