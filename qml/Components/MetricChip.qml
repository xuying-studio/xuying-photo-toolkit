import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Themes" as Themes

Rectangle {
    id: root
    implicitWidth: content.implicitWidth + 22
    implicitHeight: 32
    radius: Themes.Theme.controlRadius
    color: Themes.Theme.panelAlt
    border.width: 0

    Behavior on color {
        enabled: Themes.Motion.policy !== Themes.Motion.none
        ColorAnimation {
            duration: Themes.Motion.normal
            easing.type: Easing.OutCubic
        }
    }

    property string label: ""
    property string value: "—"

    RowLayout {
        id: content
        anchors.centerIn: parent
        spacing: Themes.Theme.spaceSm

        Label {
            text: root.label
            color: Themes.Theme.tertiary
            font.family: Themes.Theme.fontFamily
            font.pixelSize: Themes.Theme.fontCaption
        }
        Label {
            text: root.value
            color: Themes.Theme.text
            font.family: Themes.Theme.fontFamily
            font.pixelSize: Themes.Theme.fontCaption
            font.weight: Font.DemiBold
        }
    }
}
