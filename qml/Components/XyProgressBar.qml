import QtQuick
import QtQuick.Controls
import "../Themes" as Themes

ProgressBar {
    id: root

    implicitHeight: 8
    from: 0
    to: 1
    property bool trackVisible: value > from
    opacity: trackVisible ? 1 : 0

    Behavior on opacity {
        enabled: Themes.Motion.policy !== Themes.Motion.none
        NumberAnimation {
            duration: Themes.Motion.fast
            easing.type: Easing.OutCubic
        }
    }

    background: Rectangle {
        implicitHeight: 8
        radius: height / 2
        color: Themes.Theme.progressTrack
    }

    contentItem: Item {
        clip: true
        Rectangle {
            id: progressFill
            objectName: "progressFill"
            width: parent.width
            height: parent.height
            radius: height / 2
            color: Themes.Theme.progress
            transform: Scale {
                id: progressScale
                objectName: "progressScale"
                origin.x: 0
                origin.y: progressFill.height / 2
                xScale: root.visualPosition
            }
        }
    }
}
