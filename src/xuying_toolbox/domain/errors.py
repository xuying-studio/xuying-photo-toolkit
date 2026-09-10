"""跨层共享但不依赖 Qt 的错误模型。"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """稳定错误码，避免界面依赖异常文字。"""

    BOOTSTRAP_FAILED = "bootstrap_failed"
    QML_NOT_FOUND = "qml_not_found"
    QML_LOAD_FAILED = "qml_load_failed"
    UNSUPPORTED_PLATFORM = "unsupported_platform"


class AppError(Exception):
    """可安全传递给上层的结构化错误。"""

    def __init__(
        self,
        code: ErrorCode,
        user_message: str,
        *,
        detail: str | None = None,
        recoverable: bool = False,
    ) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message
        self.detail = detail
        self.recoverable = recoverable

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "user_message": self.user_message,
            "detail": self.detail,
            "recoverable": self.recoverable,
        }
