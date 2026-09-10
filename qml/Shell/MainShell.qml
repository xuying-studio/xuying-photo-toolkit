pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Components"
import "../Pages"
import "../Themes" as Themes

Item {
    id: shell
    objectName: "mainShell"

    required property bool integratedTitleBar
    required property var renameViewModel
    required property var cleanupViewModel
    required property var xmpSyncViewModel
    required property var quickCutViewModel
    property int currentPage: 0
    property bool pageTransitionsEnabled: true
    readonly property string thirdToolLabel: navigationModel.get(2).label

    function selectPage(index) {
        setPage(index, true)
    }

    function selectPageImmediately(index) {
        setPage(index, false)
    }

    function setPage(index, animated) {
        let nextPage = Math.max(0, Math.min(index, navigationModel.count - 1))
        pageTransitionRestore.stop()
        pageTransitionsEnabled = animated
        currentPage = nextPage
        if (!animated)
            pageTransitionRestore.restart()
    }

    function layoutFits() {
        return width >= 1300 && height >= 760 && pageStack.width > 700 &&
               pageStack.height > 560 && sidebar.width >= 220
    }

    ListModel {
        id: navigationModel

        ListElement { label: "01  时间重命名" }
        ListElement { label: "02  配对清理" }
        ListElement { label: "03  颜色星标同步" }
        ListElement { label: "04  关键词快切" }
    }

    Timer {
        id: pageTransitionRestore
        interval: 0
        repeat: false
        onTriggered: shell.pageTransitionsEnabled = true
    }

    Rectangle {
        anchors.fill: parent
        color: Themes.Theme.windowMaterial
        Behavior on color {
            enabled: Themes.Motion.policy !== Themes.Motion.none
            ColorAnimation {
                duration: Themes.Motion.normal
                easing.type: Easing.OutCubic
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: topBar
            objectName: "topBar"
            Layout.fillWidth: true
            Layout.preferredHeight: 66 + (shell.integratedTitleBar ? 28 : 0)
            color: Themes.Theme.chromeMaterial
            border.width: 0

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Themes.Theme.surfaceBorder
            }

            Behavior on color {
                enabled: Themes.Motion.policy !== Themes.Motion.none
                ColorAnimation {
                    duration: Themes.Motion.normal
                    easing.type: Easing.OutCubic
                }
            }

            MouseArea {
                objectName: "topBarDragArea"
                anchors.fill: parent
                enabled: shell.integratedTitleBar
                acceptedButtons: Qt.LeftButton
                onPressed: function(mouse) {
                    if (topBar.Window.window) {
                        topBar.Window.window.startSystemMove()
                        mouse.accepted = true
                    }
                }
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Themes.Theme.spaceXl
                anchors.rightMargin: Themes.Theme.spaceXl
                anchors.topMargin: shell.integratedTitleBar ? 28 : 0
                spacing: Themes.Theme.spaceLg

                RowLayout {
                    Layout.preferredWidth: 280
                    spacing: Themes.Theme.spaceMd

                    Image {
                        objectName: "brandIcon"
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        source: "../Assets/app_icon.png"
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        mipmap: true
                    }
                    ColumnLayout {
                        spacing: 0
                        Label {
                            text: "旭影工具箱"
                            color: Themes.Theme.title
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: 17
                            font.weight: Font.DemiBold
                        }
                        Label {
                            text: "本地照片工作流"
                            color: Themes.Theme.tertiary
                            font.family: Themes.Theme.fontFamily
                            font.pixelSize: 10
                            font.letterSpacing: 0.8
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Label {
                    text: "界面皮肤"
                    color: Themes.Theme.secondary
                    font.family: Themes.Theme.fontFamily
                    font.pixelSize: Themes.Theme.fontCaption
                }
                ThemePicker {}

            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                id: sidebar
                objectName: "sidebar"
                Layout.preferredWidth: Themes.Theme.sidebarWidth
                Layout.fillHeight: true
                color: Themes.Theme.chromeMaterial
                border.width: 0

                Rectangle {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    width: 1
                    color: Themes.Theme.surfaceBorder
                }

                Behavior on color {
                    enabled: Themes.Motion.policy !== Themes.Motion.none
                    ColorAnimation {
                        duration: Themes.Motion.normal
                        easing.type: Easing.OutCubic
                    }
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Themes.Theme.spaceLg
                    spacing: Themes.Theme.spaceSm

                    Label {
                        text: "工作流程"
                        color: Themes.Theme.tertiary
                        font.family: Themes.Theme.fontFamily
                        font.pixelSize: Themes.Theme.fontCaption
                        font.weight: Font.DemiBold
                        Layout.leftMargin: Themes.Theme.spaceSm
                        Layout.bottomMargin: Themes.Theme.spaceSm
                    }

                    Repeater {
                        id: navigationRepeater
                        objectName: "navigationRepeater"
                        model: navigationModel

                        delegate: Item {
                            id: navigationItem
                            required property int index
                            required property string label
                            Layout.fillWidth: true
                            Layout.preferredHeight: navigationButton.implicitHeight

                            NavButton {
                                id: navigationButton
                                objectName: "sidebarButton_" + navigationItem.index
                                anchors.fill: parent
                                label: navigationItem.label
                                index: navigationItem.index
                                active: shell.currentPage === navigationItem.index
                                animateState: shell.pageTransitionsEnabled
                                onActivated: function(pageIndex, animated) {
                                    if (animated)
                                        shell.selectPage(pageIndex)
                                    else
                                        shell.selectPageImmediately(pageIndex)
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Item {
                    id: pageStack
                    objectName: "pageStack"
                    anchors.fill: parent
                    anchors.margins: Themes.Theme.contentMargin
                    readonly property int currentIndex: shell.currentPage

                    RenamePage {
                        id: renamePage
                        objectName: "renamePage"
                        anchors.fill: parent
                        viewModel: shell.renameViewModel
                        enabled: shell.currentPage === 0
                        visible: enabled || opacity > 0.01
                        opacity: enabled ? 1 : 0
                        z: enabled ? 2 : 1
                        Behavior on opacity {
                            enabled: shell.pageTransitionsEnabled &&
                                     Themes.Motion.policy !== Themes.Motion.none
                            NumberAnimation {
                                duration: Themes.Motion.pageTransition
                                easing.type: Easing.OutCubic
                            }
                        }
                        transform: Translate {
                            id: renamePageTranslate
                            objectName: "renamePageTranslate"
                            x: Themes.Motion.policy === Themes.Motion.full &&
                               !renamePage.enabled ? -16 : 0
                            Behavior on x {
                                enabled: shell.pageTransitionsEnabled &&
                                         Themes.Motion.policy === Themes.Motion.full
                                NumberAnimation {
                                    duration: Themes.Motion.pageTransition
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }
                    }
                    CleanupPage {
                        id: cleanupPage
                        objectName: "cleanupPage"
                        anchors.fill: parent
                        viewModel: shell.cleanupViewModel
                        enabled: shell.currentPage === 1
                        visible: enabled || opacity > 0.01
                        opacity: enabled ? 1 : 0
                        z: enabled ? 2 : 1
                        Behavior on opacity {
                            enabled: shell.pageTransitionsEnabled &&
                                     Themes.Motion.policy !== Themes.Motion.none
                            NumberAnimation {
                                duration: Themes.Motion.pageTransition
                                easing.type: Easing.OutCubic
                            }
                        }
                        transform: Translate {
                            id: cleanupPageTranslate
                            objectName: "cleanupPageTranslate"
                            x: Themes.Motion.policy === Themes.Motion.full && !cleanupPage.enabled ?
                                   (shell.currentPage > 1 ? -16 : 16) : 0
                            Behavior on x {
                                enabled: shell.pageTransitionsEnabled &&
                                         Themes.Motion.policy === Themes.Motion.full
                                NumberAnimation {
                                    duration: Themes.Motion.pageTransition
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }
                    }
                    XmpSyncPage {
                        id: xmpSyncPage
                        objectName: "xmpSyncPage"
                        anchors.fill: parent
                        viewModel: shell.xmpSyncViewModel
                        enabled: shell.currentPage === 2
                        visible: enabled || opacity > 0.01
                        opacity: enabled ? 1 : 0
                        z: enabled ? 2 : 1
                        Behavior on opacity {
                            enabled: shell.pageTransitionsEnabled &&
                                     Themes.Motion.policy !== Themes.Motion.none
                            NumberAnimation {
                                duration: Themes.Motion.pageTransition
                                easing.type: Easing.OutCubic
                            }
                        }
                        transform: Translate {
                            id: xmpSyncPageTranslate
                            objectName: "xmpSyncPageTranslate"
                            x: Themes.Motion.policy === Themes.Motion.full && !xmpSyncPage.enabled ?
                                   (shell.currentPage > 2 ? -16 : 16) : 0
                            Behavior on x {
                                enabled: shell.pageTransitionsEnabled &&
                                         Themes.Motion.policy === Themes.Motion.full
                                NumberAnimation {
                                    duration: Themes.Motion.pageTransition
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }
                    }
                    QuickCutPage {
                        id: quickCutPage
                        objectName: "quickCutPage"
                        anchors.fill: parent
                        viewModel: shell.quickCutViewModel
                        enabled: shell.currentPage === 3
                        visible: enabled || opacity > 0.01
                        opacity: enabled ? 1 : 0
                        z: enabled ? 2 : 1
                        Behavior on opacity {
                            enabled: shell.pageTransitionsEnabled &&
                                     Themes.Motion.policy !== Themes.Motion.none
                            NumberAnimation {
                                duration: Themes.Motion.pageTransition
                                easing.type: Easing.OutCubic
                            }
                        }
                        transform: Translate {
                            id: quickCutPageTranslate
                            objectName: "quickCutPageTranslate"
                            x: Themes.Motion.policy === Themes.Motion.full &&
                               !quickCutPage.enabled ? 16 : 0
                            Behavior on x {
                                enabled: shell.pageTransitionsEnabled &&
                                         Themes.Motion.policy === Themes.Motion.full
                                NumberAnimation {
                                    duration: Themes.Motion.pageTransition
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }
                    }
                }
            }
        }

    }

    Shortcut { sequence: "Ctrl+1"; onActivated: shell.selectPageImmediately(0) }
    Shortcut { sequence: "Ctrl+2"; onActivated: shell.selectPageImmediately(1) }
    Shortcut { sequence: "Ctrl+3"; onActivated: shell.selectPageImmediately(2) }
    Shortcut { sequence: "Ctrl+4"; onActivated: shell.selectPageImmediately(3) }
}
