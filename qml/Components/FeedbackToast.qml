import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Themes" as Themes

Rectangle {
    id: toast
    objectName: "feedbackToast"
    width: Math.min(420, Math.max(260, messageLabel.implicitWidth + 58))
    height: Math.max(48, toastContent.implicitHeight + 20)
    radius: Themes.Theme.controlRadius
    visible: message.length > 0
    opacity: shown ? 1 : 0

    property string message: ""
    property string level: "info"
    property string motionMode: Themes.Motion.policy
    property int displayDuration: 3200
    property bool shown: false
    readonly property bool exiting: visible && !shown
    readonly property real motionOffset: toastTranslate.y

    signal dismissed()

    color: {
        switch (toast.level) {
        case "success": return Themes.Theme.successSoft
        case "warning": return Themes.Theme.warningSoft
        case "error": return Themes.Theme.dangerSoft
        default: return Themes.Theme.accentSoft
        }
    }
    border.width: 1
    border.color: {
        switch (toast.level) {
        case "success": return Themes.Theme.success
        case "warning": return Themes.Theme.warning
        case "error": return Themes.Theme.danger
        default: return Themes.Theme.accent
        }
    }
    Behavior on opacity {
        enabled: toast.motionMode !== Themes.Motion.none
        NumberAnimation {
            duration: toast.shown ? Themes.Motion.toastEnter : Themes.Motion.toastExit
            easing.type: Easing.OutCubic
        }
    }

    transform: Translate {
        id: toastTranslate
        objectName: "toastTranslate"
        y: toast.motionMode === Themes.Motion.full && !toast.shown ? 6 : 0
        Behavior on y {
            enabled: toast.motionMode === Themes.Motion.full
            NumberAnimation {
                duration: toast.shown ? Themes.Motion.toastEnter : Themes.Motion.toastExit
                easing.type: Easing.OutCubic
            }
        }
    }

    RowLayout {
        id: toastContent
        objectName: "toastMessage"
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: Themes.Theme.spaceSm

        Rectangle {
            Layout.preferredWidth: 8
            Layout.preferredHeight: 8
            radius: 4
            color: toast.level === "success" ? Themes.Theme.success :
                   (toast.level === "warning" ? Themes.Theme.warning :
                    (toast.level === "error" ? Themes.Theme.danger : Themes.Theme.accent))
        }

        Label {
            id: messageLabel
            Layout.fillWidth: true
            verticalAlignment: Text.AlignVCenter
            color: Themes.Theme.text
            font: Themes.Theme.bodyFont
            text: toast.message
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
    }

    Timer {
        id: hideTimer
        interval: toast.displayDuration
        repeat: false
        onTriggered: toast.beginHide()
    }

    Timer {
        id: clearTimer
        interval: Math.max(1, Themes.Motion.toastExit)
        repeat: false
        onTriggered: toast.finishHide()
    }

    function show(text, kind) {
        clearTimer.stop()
        message = text
        level = kind || "info"
        shown = true
        hideTimer.restart()
    }

    function beginHide() {
        hideTimer.stop()
        shown = false
        if (Themes.Motion.toastExit === 0)
            finishHide()
        else
            clearTimer.restart()
    }

    function finishHide() {
        if (shown)
            return
        clearTimer.stop()
        message = ""
        dismissed()
    }

    function hide() {
        beginHide()
    }
}
