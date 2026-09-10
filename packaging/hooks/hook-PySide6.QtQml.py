"""只收集本项目实际使用的 Qt QML 模块。"""

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info


def _is_required_qml_item(item: tuple[str, str]) -> bool:
    destination = item[1].replace("\\", "/")
    prefixes = (
        "PySide6/Qt/qml/QtQuick",
        "PySide6/Qt/qml/QtQml",
        "PySide6/Qt/qml/Qt/labs/platform",
    )
    return any(destination == prefix or destination.startswith(prefix + "/") for prefix in prefixes)


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
qml_binaries, qml_datas = pyside6_library_info.collect_qtqml_files()
binaries += [item for item in qml_binaries if _is_required_qml_item(item)]
datas += [item for item in qml_datas if _is_required_qml_item(item)]
