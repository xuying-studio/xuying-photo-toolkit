"""使用 Qt 图像栈渲染关键词对齐画面。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter

from xuying_toolbox.domain.models.quickcut import NormalizedRect, ProjectSettings
from xuying_toolbox.domain.services.quickcut import alignment_geometry


class ImageRenderError(RuntimeError):
    """源图无法读取或目标图无法创建。"""


class QtQuickCutRenderer:
    def read(self, image_path: Path) -> QImage:
        reader = QImageReader(str(image_path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ImageRenderError(reader.errorString() or f"无法读取图片：{image_path.name}")
        return image

    def render(
        self,
        image_path: Path,
        source_box: NormalizedRect | None,
        settings: ProjectSettings,
    ) -> QImage:
        if message := settings.validation_message:
            raise ImageRenderError(message)
        source = self.read(image_path)
        geometry = alignment_geometry(
            source.width(),
            source.height(),
            settings.width,
            settings.height,
            source_box,
            settings.target_rect,
        )
        output = QImage(settings.width, settings.height, QImage.Format.Format_RGB32)
        output.fill(QColor("#090A0C"))
        painter = QPainter(output)
        try:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(
                QRectF(
                    geometry.origin_x,
                    geometry.origin_y,
                    geometry.drawn_width,
                    geometry.drawn_height,
                ),
                source,
            )
        finally:
            painter.end()
        return output

    def save_png(self, image: QImage, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(destination), "PNG"):
            raise ImageRenderError(f"无法写入 PNG：{destination.name}")

    def scaled_preview(self, image: QImage, maximum_size: int = 1600) -> QImage:
        return image.scaled(
            maximum_size,
            maximum_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
