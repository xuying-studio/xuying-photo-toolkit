from xuying_toolbox.domain.errors import AppError, ErrorCode


def test_app_error_can_be_serialized() -> None:
    error = AppError(
        ErrorCode.QML_LOAD_FAILED,
        "界面加载失败。",
        detail="App.qml",
        recoverable=False,
    )

    assert error.to_dict() == {
        "code": "qml_load_failed",
        "user_message": "界面加载失败。",
        "detail": "App.qml",
        "recoverable": False,
    }
