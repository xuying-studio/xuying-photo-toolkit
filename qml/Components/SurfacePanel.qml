import QtQuick
import "../Themes" as Themes

Rectangle {
    id: root

    // 面板只提供容器视觉，不承载业务状态。
    color: Themes.Theme.panelMaterial
    radius: Themes.Theme.radiusLarge
    border.width: 1
    border.color: Themes.Theme.surfaceBorder

    Behavior on color {
        enabled: Themes.Motion.policy !== Themes.Motion.none
        ColorAnimation {
            duration: Themes.Motion.normal
            easing.type: Easing.OutCubic
        }
    }

    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: root.radius
        anchors.rightMargin: root.radius
        height: 1
        color: Themes.Theme.surfaceHighlight
    }
}
