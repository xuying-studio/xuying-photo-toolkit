import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Themes" as Themes

Button {
    id: root

    property int index: -1
    property string label: ""
    property bool active: false
    property bool animateState: true
    property bool keyboardActivation: false
    readonly property string stepLabel: label.length >= 2 ? label.slice(0, 2) : ""
    readonly property string titleLabel: label.length > 4 ? label.slice(4) : label
    signal activated(int index, bool animated)

    implicitWidth: Math.max(160, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(40, implicitContentHeight + topPadding + bottomPadding)
    leftPadding: 16
    rightPadding: 16
    topPadding: 8
    bottomPadding: 8
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    onClicked: activated(root.index, !root.keyboardActivation)
    Accessible.name: label

    // 导航依靠颜色与焦点表达状态，避免高频缩放造成晃动。
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

    contentItem: RowLayout {
        spacing: Themes.Theme.spaceSm

        Text {
            Layout.preferredWidth: 24
            text: root.stepLabel
            color: root.enabled ?
                       (root.active ? Themes.Theme.accent : Themes.Theme.tertiary) :
                       Themes.Theme.textDisabled
            font.family: Themes.Theme.fontFamily
            font.pixelSize: Themes.Theme.fontCaption
            font.weight: Font.DemiBold
            verticalAlignment: Text.AlignVCenter
        }

        Text {
            Layout.fillWidth: true
            text: root.titleLabel
            color: root.enabled ?
                       (root.active ? Themes.Theme.navActiveText : Themes.Theme.navText) :
                       Themes.Theme.textDisabled
            font.family: Themes.Theme.fontFamily
            font.pixelSize: Themes.Theme.fontBody
            font.weight: root.active ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
            maximumLineCount: 1
            verticalAlignment: Text.AlignVCenter
        }
    }

    background: Rectangle {
        color: {
            if (!root.enabled)
                return Themes.Theme.controlDisabled
            if (root.pressed)
                return Themes.Theme.navPressed
            if (root.active)
                return Themes.Theme.navActive
            if (root.hovered)
                return Themes.Theme.navHover
            return "transparent"
        }
        radius: Themes.Theme.radiusMedium
        border.width: root.activeFocus ? 2 : 0
        border.color: Themes.Theme.focus

        Rectangle {
            anchors.left: parent.left
            anchors.leftMargin: 5
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: 20
            radius: 1.5
            visible: root.active
            color: Themes.Theme.accent
        }
        Behavior on color {
            enabled: root.animateState && !root.keyboardActivation &&
                     Themes.Motion.policy !== Themes.Motion.none
            ColorAnimation {
                duration: Themes.Motion.fast
                easing.type: Easing.OutCubic
            }
        }
        Behavior on border.color {
            enabled: root.animateState && !root.keyboardActivation &&
                     Themes.Motion.policy !== Themes.Motion.none
            ColorAnimation {
                duration: Themes.Motion.fast
                easing.type: Easing.OutCubic
            }
        }
    }
}
