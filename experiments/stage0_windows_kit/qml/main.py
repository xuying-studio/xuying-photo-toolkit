import os
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

app = QGuiApplication(sys.argv)
engine = QQmlApplicationEngine()
engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), "Main.qml")))
if not engine.rootObjects():
    raise SystemExit(2)
raise SystemExit(app.exec())
