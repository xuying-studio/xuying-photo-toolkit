"""阶段 0 的最小 PySide6/QML 启动与打包验证程序。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


def main() -> int:
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    qml_path = Path(__file__).with_name("Main.qml")
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        return 1

    # 自动退出只用于无界面验证，正常启动时不设置该环境变量。
    auto_quit_ms = int(os.environ.get("QML_PROOF_AUTO_QUIT_MS", "0"))
    if auto_quit_ms > 0:
        QTimer.singleShot(auto_quit_ms, app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
