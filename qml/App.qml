import QtQuick
import QtQuick.Controls
import "Shell"
import "Themes" as Themes

ApplicationWindow {
    id: appWindow
    objectName: "appWindow"

    required property string applicationName
    required property string applicationVersion
    required property string platformName
    required property string motionPolicy
    required property string effectPolicy
    required property var applicationSettings
    required property var renameViewModel
    required property var cleanupViewModel
    required property var xmpSyncViewModel
    required property var quickCutViewModel

    readonly property string currentThemeId: Themes.Theme.themeId
    readonly property string currentMotionPolicy: Themes.Motion.policy
    readonly property var availableThemeIds: Themes.Theme.themeIds
    readonly property color currentTextColor: Themes.Theme.text
    readonly property color currentPanelColor: Themes.Theme.panel
    readonly property color currentCanvasColor: Themes.Theme.canvas
    readonly property int motionFast: Themes.Motion.fast
    readonly property int motionNormal: Themes.Motion.normal
    readonly property int motionSlow: Themes.Motion.slow
    property bool integratedTitleBar: false

    visible: true
    width: 1440
    height: 900
    minimumWidth: 1300
    minimumHeight: 760
    title: applicationName
    topPadding: 0
    flags: Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint |
           Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint |
           (platformName === "macOS" ?
                Qt.WindowFullscreenButtonHint | Qt.ExpandedClientAreaHint |
                Qt.NoTitleBarBackgroundHint : 0)
    color: effectPolicy === "native" ? "transparent" : Themes.Theme.window

    function setTheme(themeId) {
        Themes.Theme.setTheme(themeId)
    }

    function setMotionPolicy(policy) {
        Themes.Motion.setPolicy(policy)
    }

    function layoutFits() {
        return mainShell.layoutFits()
    }

    Component.onCompleted: {
        Themes.Motion.setPolicy(appWindow.motionPolicy)
        Themes.Theme.setEffectPolicy(appWindow.effectPolicy)
        Themes.Theme.setTheme(appWindow.applicationSettings.themeId)
    }

    Connections {
        target: Themes.Theme
        function onThemeIdChanged() {
            appWindow.applicationSettings.setThemeId(Themes.Theme.themeId)
        }
    }

    MainShell {
        id: mainShell
        anchors.fill: parent
        integratedTitleBar: appWindow.integratedTitleBar
        renameViewModel: appWindow.renameViewModel
        cleanupViewModel: appWindow.cleanupViewModel
        xmpSyncViewModel: appWindow.xmpSyncViewModel
        quickCutViewModel: appWindow.quickCutViewModel
    }
}
