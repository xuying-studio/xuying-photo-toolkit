pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import "../Themes" as Themes

ComboBox {
    id: root

    implicitHeight: Math.max(Themes.Theme.controlHeight,
                             implicitContentHeight + topPadding + bottomPadding)
    leftPadding: 12
    rightPadding: 36
    topPadding: 8
    bottomPadding: 8
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font: Themes.Theme.bodyFont
    Accessible.name: accessibleName.length > 0 ? accessibleName : displayText

    property string accessibleName: ""

    contentItem: Text {
        text: root.displayText
        color: root.enabled ? Themes.Theme.text : Themes.Theme.textDisabled
        font: root.font
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
        maximumLineCount: 1
    }

    indicator: Text {
        text: "⌄"
        color: root.enabled ? Themes.Theme.secondary : Themes.Theme.textDisabled
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        rotation: root.popup.visible ? 180 : 0
        Behavior on rotation {
            enabled: Themes.Motion.policy === Themes.Motion.full
            NumberAnimation {
                duration: Themes.Motion.fast
                easing.type: Easing.OutCubic
            }
        }
    }

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

    delegate: ItemDelegate {
        id: delegateItem
        required property int index
        required property var modelData
        width: root.popup.width
        text: root.textRole.length > 0 ? root.model[index][root.textRole] : modelData
        highlighted: root.highlightedIndex === delegateItem.index
        font: root.font
        contentItem: Text {
            text: delegateItem.text
            color: Themes.Theme.text
            font: root.font
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: delegateItem.highlighted ? Themes.Theme.selection : Themes.Theme.panel
        }
    }

    popup: Popup {
        y: root.height + 6
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 2, 280)
        padding: 1
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
        }
        background: Rectangle {
            color: Themes.Theme.panel
            radius: Themes.Theme.radiusMedium
            border.color: Themes.Theme.surfaceBorder
        }
        enter: Transition {
            ParallelAnimation {
                NumberAnimation {
                    property: "opacity"
                    from: 0
                    to: 1
                    duration: Themes.Motion.fast
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    property: "scale"
                    from: Themes.Motion.policy === Themes.Motion.full ? 0.98 : 1
                    to: 1
                    duration: Themes.Motion.fast
                    easing.type: Easing.OutCubic
                }
            }
        }
        exit: Transition {
            ParallelAnimation {
                NumberAnimation {
                    property: "opacity"
                    from: 1
                    to: 0
                    duration: Themes.Motion.buttonRelease
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    property: "scale"
                    from: 1
                    to: Themes.Motion.policy === Themes.Motion.full ? 0.98 : 1
                    duration: Themes.Motion.buttonRelease
                    easing.type: Easing.OutCubic
                }
            }
        }
    }
}
