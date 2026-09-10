import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: root
    width: 520
    height: 300
    visible: true
    title: "旭影工具箱 · 阶段 0 验证"
    color: "#151922"

    Column {
        anchors.centerIn: parent
        spacing: 12

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "PySide6 + QML 已成功启动"
            color: "#F5F7FA"
            font.pixelSize: 22
        }

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "此窗口只验证启动、QML 插件与打包，不包含正式业务。"
            color: "#AAB2C0"
            font.pixelSize: 14
        }
    }
}
