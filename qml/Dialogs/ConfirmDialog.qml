import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Components"
import "../Themes" as Themes

Popup {
    id: dialog
    objectName: "confirmDialog"
    modal: true
    focus: true
    width: 440
    padding: 24
    closePolicy: Popup.CloseOnEscape

    property string titleText: "确认操作"
    property string description: "此操作可能影响现有文件。"
    property bool destructive: false

    signal confirmed()
    signal cancelled()

    Overlay.modal: Rectangle {
        color: Themes.Theme.overlayScrim
    }

    enter: Transition {
        ParallelAnimation {
            NumberAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: Themes.Motion.toastEnter
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                property: "scale"
                from: Themes.Motion.policy === Themes.Motion.full ? 0.97 : 1
                to: 1
                duration: Themes.Motion.toastEnter
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
                duration: Themes.Motion.toastExit
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                property: "scale"
                from: 1
                to: Themes.Motion.policy === Themes.Motion.full ? 0.98 : 1
                duration: Themes.Motion.toastExit
                easing.type: Easing.OutCubic
            }
        }
    }

    background: Rectangle {
        color: Themes.Theme.panel
        radius: Themes.Theme.panelRadius
        border.width: dialog.destructive ? 2 : 1
        border.color: dialog.destructive ? Themes.Theme.danger : Themes.Theme.border
    }

    contentItem: ColumnLayout {
        spacing: 14

        Label {
            objectName: "confirmTitle"
            text: dialog.titleText
            color: Themes.Theme.title
            font.family: Themes.Theme.fontFamily
            font.pixelSize: Themes.Theme.fontTitle
            font.bold: true
            Layout.fillWidth: true
        }

        Label {
            objectName: "confirmDescription"
            text: dialog.description
            color: Themes.Theme.secondary
            font: Themes.Theme.bodyFont
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: 10

            XyButton {
                objectName: "cancelButton"
                text: "取消"
                quiet: true
                onClicked: {
                    dialog.cancelled()
                    dialog.close()
                }
            }

            XyButton {
                objectName: "confirmButton"
                text: "确认"
                destructive: dialog.destructive
                prominent: true
                onClicked: {
                    dialog.confirmed()
                    dialog.close()
                }
            }
        }
    }
}
