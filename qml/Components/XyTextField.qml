import QtQuick
import QtQuick.Controls
import "../Themes" as Themes

TextField {
    id: root

    implicitHeight: Themes.Theme.controlHeight
    leftPadding: 12
    rightPadding: 12
    topPadding: 8
    bottomPadding: 8
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    selectByMouse: true
    Accessible.name: accessibleName.length > 0 ? accessibleName : placeholderText

    property string accessibleName: ""

    color: root.enabled ? Themes.Theme.text : Themes.Theme.textDisabled
    placeholderTextColor: Themes.Theme.secondary
    selectionColor: Themes.Theme.selection
    selectedTextColor: Themes.Theme.selectionText
    font: Themes.Theme.bodyFont

    background: Rectangle {
        color: root.enabled ? Themes.Theme.input : Themes.Theme.controlDisabled
        radius: Themes.Theme.radiusMedium
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? Themes.Theme.focus :
                       (root.hovered ? Themes.Theme.borderHover : Themes.Theme.border)
        Behavior on border.color {
            enabled: Themes.Motion.policy !== Themes.Motion.none
            ColorAnimation {
                duration: Themes.Motion.fast
                easing.type: Easing.OutCubic
            }
        }
    }
}
