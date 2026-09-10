"""把关键词快切预览图提供给 QML Image。"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage
from PySide6.QtQuick import QQuickImageProvider


class QuickCutPreviewProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._image = QImage(32, 32, QImage.Format.Format_RGB32)
        self._image.fill(QColor("#090A0C"))

    def set_image(self, image: QImage) -> None:
        self._image = image.copy()

    def clear(self) -> None:
        image = QImage(32, 32, QImage.Format.Format_RGB32)
        image.fill(QColor("#090A0C"))
        self._image = image

    def requestImage(self, _image_id: str, size: QSize, _requested_size: QSize) -> QImage:
        size.setWidth(self._image.width())
        size.setHeight(self._image.height())
        return self._image


__all__ = ["QuickCutPreviewProvider"]
