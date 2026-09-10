"""测试环境必须在导入 PySide6 前固定为无界面平台。"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolate_application_support(monkeypatch, tmp_path) -> None:
    """测试只能写临时 v2 目录，不能碰用户真实应用数据。"""

    monkeypatch.setenv("XUYING_SUPPORT_ROOT", str(tmp_path / "application-support-v2"))
