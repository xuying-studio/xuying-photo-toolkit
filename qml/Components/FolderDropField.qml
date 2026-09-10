import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Themes" as Themes

Item {
    id: root

    property alias text: directoryField.text
    property alias placeholderText: directoryField.placeholderText
    property alias accessibleName: directoryField.accessibleName
    property bool dropEnabled: true
    property string labelText: "工作目录"
    signal folderDropped(url folderUrl)

    implicitHeight: content.implicitHeight

    ColumnLayout {
        id: content
        anchors.fill: parent
        spacing: Themes.Theme.spaceSm

        Label {
            text: root.labelText
            color: Themes.Theme.text
            font.family: Themes.Theme.fontFamily
            font.pixelSize: Themes.Theme.fontBody
            font.weight: Font.DemiBold
        }

        XyTextField {
            id: directoryField
            Layout.fillWidth: true
            readOnly: true
        }
    }

    DropArea {
        id: dropArea
        objectName: root.objectName + "DropArea"
        anchors.fill: parent
        enabled: root.dropEnabled

        onEntered: function(drag) {
            if (drag.hasUrls && drag.urls.length === 1)
                drag.acceptProposedAction()
        }
        onDropped: function(drop) {
            if (!drop.hasUrls || drop.urls.length !== 1)
                return
            root.folderDropped(drop.urls[0])
            drop.acceptProposedAction()
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: dropArea.containsDrag
        radius: Themes.Theme.radiusLarge
        color: Themes.Theme.accentSoft
        border.width: 2
        border.color: Themes.Theme.accent

        Label {
            anchors.centerIn: parent
            text: "松开以使用此文件夹"
            color: Themes.Theme.text
            font: Themes.Theme.buttonFont
        }
    }
}
