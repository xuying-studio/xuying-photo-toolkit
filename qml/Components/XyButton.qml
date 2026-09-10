import QtQuick
import QtQuick.Controls
import "../Themes" as Themes

Button {
    id: root

    property bool selected: false
    property bool destructive: false
    property bool prominent: false
    property bool quiet: false
    property bool compact: false
    property bool keyboardActivation: false

    implicitWidth: Math.max(implicitContentWidth + leftPadding + rightPadding, 96)
    implicitHeight: Math.max(compact ? Themes.Theme.compactControlHeight :
                                      Themes.Theme.controlHeight,
                             implicitContentHeight + topPadding + bottomPadding)
    padding: 12
    leftPadding: 16
    rightPadding: 16
    topPadding: 8
    bottomPadding: 8
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    transformOrigin: Item.Center
    scale: Themes.Motion.policy === Themes.Motion.full &&
           pressed && !keyboardActivation ? 0.97 : 1.0
    Accessible.name: text

    Behavior on scale {
        enabled: Themes.Motion.policy === Themes.Motion.full && !root.keyboardActivation
        NumberAnimation {
            duration: root.pressed ? Themes.Motion.buttonPress : Themes.Motion.buttonRelease
            easing.type: Easing.OutCubic
        }
    }

    // 键盘激活是高频路径，保留功能，但不播放按压动画。
    Keys.onPressed: function(event) {
        if (!event.isAutoRepeat &&
                (event.key === Qt.Key_Space || event.key === Qt.Key_Return ||
                 event.key === Qt.Key_Enter))
            root.keyboardActivation = true
    }
    Keys.onReleased: function(event) {
        if (event.key === Qt.Key_Space || event.key === Qt.Key_Return ||
                event.key === Qt.Key_Enter)
            Qt.callLater(function() { root.keyboardActivation = false })
    }
    onActiveFocusChanged: {
        if (!activeFocus)
            keyboardActivation = false
    }

    contentItem: Text {
        text: root.text
        color: {
            if (!root.enabled)
                return Themes.Theme.textDisabled
            if (root.prominent || root.selected || root.checked ||
                    (root.destructive && root.pressed))
                return Themes.Theme.accentText
            if (root.destructive)
                return Themes.Theme.danger
            return Themes.Theme.text
        }
        font: Themes.Theme.buttonFont
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        maximumLineCount: 1
    }

    background: Rectangle {
        color: {
            if (!root.enabled)
                return Themes.Theme.controlDisabled
            if (root.pressed)
                return root.destructive ? Themes.Theme.dangerActive : Themes.Theme.controlPressed
            if (root.prominent)
                return root.destructive ? Themes.Theme.danger : Themes.Theme.accent
            if (root.selected || root.checked)
                return Themes.Theme.controlSelected
            if (root.hovered)
                return root.destructive ? Themes.Theme.dangerSoft : Themes.Theme.controlHover
            return root.quiet ? "transparent" : Themes.Theme.control
        }
        radius: Themes.Theme.radiusMedium
        border.width: root.activeFocus ? 2 : (root.quiet ? 0 : 1)
        border.color: !root.enabled ?
                          (root.quiet ? "transparent" : Themes.Theme.border) :
                      (root.activeFocus ? Themes.Theme.focus :
                       (root.prominent ?
                            (root.destructive ? Themes.Theme.dangerActive : Themes.Theme.accentActive) :
                            Themes.Theme.border))
        Behavior on color {
            enabled: Themes.Motion.policy !== Themes.Motion.none && !root.keyboardActivation
            ColorAnimation {
                duration: Themes.Motion.fast
                easing.type: Easing.OutCubic
            }
        }
        Behavior on border.color {
            enabled: Themes.Motion.policy !== Themes.Motion.none && !root.keyboardActivation
            ColorAnimation {
                duration: Themes.Motion.fast
                easing.type: Easing.OutCubic
            }
        }
    }
}
