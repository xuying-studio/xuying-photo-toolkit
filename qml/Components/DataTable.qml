pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Themes" as Themes

Item {
    id: table
    objectName: "dataTable"

    property var columns: []
    property var rows: null
    property int rowHeight: 42
    property int selectedRow: -1
    property string emptyText: "暂无数据"
    property string emptyHint: "扫描完成后，列表会在这里自动更新"
    readonly property int rowCount: rows && rows.count !== undefined ? rows.count :
                                    (rows && rows.length !== undefined ? rows.length : 0)

    signal rowActivated(int rowIndex)

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: Themes.Theme.surfaceBorder
        radius: Themes.Theme.controlRadius
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            objectName: "tableHeader"
            Layout.fillWidth: true
            Layout.preferredHeight: table.rowHeight
            color: Themes.Theme.panelAlt

            Row {
                anchors.fill: parent
                spacing: 0

                Repeater {
                    model: table.columns
                    delegate: Label {
                        required property var modelData
                        width: modelData.width || 160
                        height: table.rowHeight
                        leftPadding: 12
                        verticalAlignment: Text.AlignVCenter
                        text: modelData.title || ""
                        color: Themes.Theme.secondary
                        font.family: Themes.Theme.fontFamily
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Themes.Theme.tableGrid
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Column {
                objectName: "emptyState"
                id: emptyState
                anchors.centerIn: parent
                visible: table.rowCount === 0
                spacing: Themes.Theme.spaceSm

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 42
                    height: 42
                    radius: 21
                    color: Themes.Theme.panelAlt

                    Label {
                        anchors.centerIn: parent
                        text: "—"
                        color: Themes.Theme.accent
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                    }
                }

                Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: table.emptyText
                    color: Themes.Theme.secondary
                    font: Themes.Theme.bodyFont
                }

                Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: table.emptyHint
                    color: Themes.Theme.tertiary
                    font.family: Themes.Theme.fontFamily
                    font.pixelSize: Themes.Theme.fontCaption
                }
            }

            ListView {
                id: rowView
                objectName: "tableListView"
                anchors.fill: parent
                clip: true
                model: table.rows
                visible: !emptyState.visible
                boundsBehavior: Flickable.StopAtBounds
                cacheBuffer: table.rowHeight * 3

                delegate: Rectangle {
                    id: rowDelegate
                    required property int index
                    required property var modelData
                    property var row: modelData
                    objectName: "tableRow_" + index
                    width: rowView.width
                    height: table.rowHeight
                    color: index === table.selectedRow ? Themes.Theme.selection :
                           (rowMouse.containsMouse ? Themes.Theme.panelAlt : "transparent")
                    border.width: activeFocus ? 1 : 0
                    border.color: Themes.Theme.focus
                    activeFocusOnTab: true
                    Accessible.role: Accessible.ListItem
                    Accessible.name: "第 " + (index + 1) + " 行"
                    Keys.onReturnPressed: activateRow()
                    Keys.onSpacePressed: activateRow()

                    function activateRow() {
                        rowDelegate.forceActiveFocus()
                        table.selectedRow = index
                        table.rowActivated(index)
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: 3
                        height: parent.height - 12
                        radius: 1.5
                        visible: rowDelegate.index === table.selectedRow
                        color: Themes.Theme.accent
                    }

                    Row {
                        anchors.fill: parent
                        spacing: 0
                        Repeater {
                            model: table.columns
                            delegate: Label {
                                required property var modelData
                                width: modelData.width || 160
                                height: table.rowHeight
                                leftPadding: 12
                                verticalAlignment: Text.AlignVCenter
                                text: modelData.key && rowDelegate.row ?
                                          rowDelegate.row[modelData.key] : ""
                                color: Themes.Theme.text
                                font: Themes.Theme.bodyFont
                                elide: Text.ElideRight
                            }
                        }
                    }

                    MouseArea {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: parent.activateRow()
                    }
                }
            }
        }
    }
}
