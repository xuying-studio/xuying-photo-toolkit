import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Themes" as Themes

Item {
    id: root
    objectName: "toolPlaceholderPage"

    property string step: "01"
    property string title: "工具"
    property string description: ""
    property string statusText: "共享核心已就绪"
    property string emptyText: "选择文件夹并扫描后，这里显示预览结果"
    property var columns: []
    property var optionLabels: []

    ColumnLayout {
        anchors.fill: parent
        spacing: Themes.Theme.spaceLg

        PageHeader {
            Layout.fillWidth: true
            eyebrow: "工具 " + root.step + " / 04"
            title: root.title
            description: root.description
            statusText: root.statusText
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Themes.Theme.spaceLg

            SurfacePanel {
                Layout.preferredWidth: 350
                Layout.minimumWidth: 320
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Themes.Theme.spaceXl
                    spacing: Themes.Theme.spaceMd

                    Label {
                        text: "工作目录"
                        color: Themes.Theme.text
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: Themes.Theme.fontBody
                        font.weight: Font.DemiBold
                    }

                    XyTextField {
                        objectName: "directoryField"
                        Layout.fillWidth: true
                        readOnly: true
                        accessibleName: "照片文件夹"
                        placeholderText: "尚未选择文件夹"
                    }

                    XyButton {
                        objectName: "chooseFolderButton"
                        Layout.fillWidth: true
                        text: "阶段 4 接入文件夹选择"
                        enabled: false
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Themes.Theme.tableGrid
                        Layout.topMargin: Themes.Theme.spaceSm
                        Layout.bottomMargin: Themes.Theme.spaceSm
                    }

                    Label {
                        text: "当前流程"
                        color: Themes.Theme.secondary
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: Themes.Theme.fontCaption
                        font.weight: Font.DemiBold
                    }

                    Repeater {
                        model: root.optionLabels
                        delegate: RowLayout {
                            id: optionRow
                            required property int index
                            required property string modelData
                            Layout.fillWidth: true
                            spacing: Themes.Theme.spaceSm

                            Rectangle {
                                Layout.preferredWidth: 22
                                Layout.preferredHeight: 22
                                radius: 11
                                color: optionRow.index === 0 ? Themes.Theme.accentSoft : Themes.Theme.panelAlt
                                border.color: optionRow.index === 0 ? Themes.Theme.accent : Themes.Theme.border
                                Label {
                                    anchors.centerIn: parent
                                    text: optionRow.index + 1
                                    color: Themes.Theme.text
                                    font.pixelSize: 11
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: optionRow.modelData
                                color: optionRow.index === 0 ? Themes.Theme.text : Themes.Theme.secondary
                                font: Themes.Theme.bodyFont
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    Label {
                        Layout.fillWidth: true
                        text: "所有修改操作仍需经过扫描、预览和确认。"
                        color: Themes.Theme.tertiary
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: Themes.Theme.fontCaption
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SurfacePanel {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Themes.Theme.spaceLg
                    spacing: Themes.Theme.spaceMd

                    RowLayout {
                        Layout.fillWidth: true

                        Label {
                            text: "执行前预览"
                            color: Themes.Theme.text
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: Themes.Theme.fontTitle
                            font.weight: Font.DemiBold
                        }
                        Item { Layout.fillWidth: true }
                        MetricChip { label: "照片"; value: "—" }
                        MetricChip { label: "待处理"; value: "—" }
                        MetricChip { label: "冲突"; value: "—" }
                    }

                    DataTable {
                        objectName: "previewTable"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: root.columns
                        rows: []
                        emptyText: root.emptyText
                    }

                    XyProgressBar {
                        objectName: "placeholderProgress"
                        Layout.fillWidth: true
                        value: 0
                    }
                }
            }
        }
    }
}
