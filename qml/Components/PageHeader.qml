import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Themes" as Themes

Item {
    id: root
    implicitHeight: 80

    property string eyebrow: ""
    property string title: ""
    property string description: ""
    property string statusText: ""

    RowLayout {
        anchors.fill: parent
        spacing: Themes.Theme.spaceLg

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Themes.Theme.spaceXs

            Label {
                text: root.eyebrow
                color: Themes.Theme.accent
                font.family: Themes.Theme.fontFamily
                font.pixelSize: Themes.Theme.fontCaption
                font.weight: Font.DemiBold
                font.letterSpacing: 1.2
            }

            Label {
                text: root.title
                color: Themes.Theme.title
                font.family: Themes.Theme.fontFamily
                font.pixelSize: Themes.Theme.fontHeading
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Label {
                text: root.description
                color: Themes.Theme.secondary
                font: Themes.Theme.bodyFont
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }

        Rectangle {
            visible: root.statusText.length > 0
            implicitWidth: statusContent.implicitWidth + 24
            implicitHeight: 32
            radius: Themes.Theme.controlRadius
            color: Themes.Theme.panelAlt
            border.width: 0

            RowLayout {
                id: statusContent
                anchors.centerIn: parent
                spacing: Themes.Theme.spaceSm

                Rectangle {
                    Layout.preferredWidth: 7
                    Layout.preferredHeight: 7
                    radius: 3.5
                    color: Themes.Theme.accent
                }

                Label {
                    text: root.statusText
                    color: Themes.Theme.secondary
                    font.family: Themes.Theme.fontFamily
                    font.pixelSize: Themes.Theme.fontCaption
                }
            }
        }
    }
}
