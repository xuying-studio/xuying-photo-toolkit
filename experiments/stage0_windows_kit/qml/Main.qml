import QtQuick
import QtQuick.Controls

ApplicationWindow {
    visible: true
    width: 640
    height: 360
    title: "旭影阶段0验证"
    Label { anchors.centerIn: parent; text: "阶段0 QML 验证" }
    Timer { interval: 500; running: true; repeat: false; onTriggered: Qt.quit() }
}
