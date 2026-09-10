pragma Singleton

import QtQuick

// 七套皮肤只覆盖 Token，所有页面和控件共享同一套状态规则。
QtObject {
    id: root

    readonly property var themeIds: [
        "professional_dark",
        "nebula_navy",
        "liquid_glass",
        "bento_modular",
        "editorial_minimal",
        "aurora_spatial",
        "soft_3d"
    ]
    readonly property var themes: [
        { id: "professional_dark", name: "专业深黑", description: "克制、清晰的高密度深色工作界面" },
        { id: "nebula_navy", name: "星雾深蓝", description: "深海军蓝层级与柔和蓝紫环境光" },
        { id: "liquid_glass", name: "流光玻璃", description: "轻盈通透的蓝灰玻璃材质与高亮边缘" },
        { id: "bento_modular", name: "模块拼盘", description: "暖橙强调色与清晰的模块化工作区" },
        { id: "editorial_minimal", name: "编辑部极简", description: "纸张暖白、细线层级与摄影杂志气质" },
        { id: "aurora_spatial", name: "极光空间", description: "深夜空间层级与紫绿极光状态光" },
        { id: "soft_3d", name: "柔软三维", description: "浅灰蓝浮雕层级与柔和低饱和控件" }
    ]
    readonly property var palettes: ({
        professional_dark: {
            window: "#0B0E14", chrome: "#0D1118", surface: "#0B0E14",
            panel: "#141923", panelAlt: "#1A202B", border: "#282D36",
            tableGrid: "#2A303B", panelHighlight: "#303743", shadow: "#07090D",
            text: "#F5F7FA", title: "#F5F7FA", secondary: "#8B93A5", tertiary: "#626B7D",
            accent: "#2F6BFF", accentActive: "#2457D6", accentText: "#FFFFFF",
            accentSoft: "#182A53", glow: "#2F6BFF", glowSoft: "#182A53",
            danger: "#EF4444", dangerActive: "#DC2626", dangerSoft: "#3A1C22",
            warning: "#F59E0B", warningSoft: "#3B2B12", selection: "#1D3975",
            success: "#22C55E", successSoft: "#153923", panelRadius: 16, controlRadius: 11
        },
        nebula_navy: {
            window: "#070B1A", chrome: "#0C1228", surface: "#0A1024",
            panel: "#101A35", panelAlt: "#162345", border: "#26365F",
            tableGrid: "#243252", panelHighlight: "#405FC5", shadow: "#040612",
            text: "#F5F7FF", title: "#7EA0FF", secondary: "#95A2C3", tertiary: "#65739B",
            accent: "#5A6FFF", accentActive: "#4457DD", accentText: "#FFFFFF",
            accentSoft: "#202D68", glow: "#6D5DFB", glowSoft: "#1D2053",
            danger: "#EF4444", dangerActive: "#DC2626", dangerSoft: "#3A1C2D",
            warning: "#F59E0B", warningSoft: "#3B2B18", selection: "#263E8A",
            success: "#22C55E", successSoft: "#153B31", panelRadius: 18, controlRadius: 12
        },
        liquid_glass: {
            window: "#132536", chrome: "#172B3D", surface: "#132536",
            panel: "#1B3449", panelAlt: "#29485E", border: "#54748B",
            tableGrid: "#38566A", panelHighlight: "#7393A8", shadow: "#091722",
            text: "#F4FBFF", title: "#DDF8FF", secondary: "#B5CAD6", tertiary: "#7E9AAA",
            accent: "#6ADCF4", accentActive: "#4EC0D7", accentText: "#06212A",
            accentSoft: "#254B5C", glow: "#83E8FF", glowSoft: "#254B5C",
            danger: "#FF7B7B", dangerActive: "#F25C5C", dangerSoft: "#532D36",
            warning: "#FFD56A", warningSoft: "#554824", selection: "#35677D",
            success: "#58D9A2", successSoft: "#244C40", panelRadius: 22, controlRadius: 16
        },
        bento_modular: {
            window: "#11100E", chrome: "#171614", surface: "#11100E",
            panel: "#201F1C", panelAlt: "#2A2823", border: "#464137",
            tableGrid: "#35322C", panelHighlight: "#5A5142", shadow: "#080706",
            text: "#F4F0E7", title: "#FFD18A", secondary: "#B5AB9B", tertiary: "#81796D",
            accent: "#E68A2E", accentActive: "#C96D16", accentText: "#1A1108",
            accentSoft: "#4B321B", glow: "#D4FF5D", glowSoft: "#354220",
            danger: "#FF6B62", dangerActive: "#E64E45", dangerSoft: "#4A2420",
            warning: "#F3C64E", warningSoft: "#433719", selection: "#5E4021",
            success: "#9DDA5E", successSoft: "#2D4120", panelRadius: 18, controlRadius: 10
        },
        editorial_minimal: {
            window: "#EEE9DF", chrome: "#E5DED2", surface: "#EEE9DF",
            panel: "#FAF7F0", panelAlt: "#E8E1D6", border: "#B9B0A3",
            tableGrid: "#CDC4B7", panelHighlight: "#FFFFFF", shadow: "#CFC6B8",
            text: "#1E1C19", title: "#1E1C19", secondary: "#655F57", tertiary: "#817A71",
            accent: "#A62D2A", accentActive: "#84211F", accentText: "#FFFFFF",
            accentSoft: "#E9C8C3", glow: "#A62D2A", glowSoft: "#E9C8C3",
            danger: "#B42318", dangerActive: "#8F1C13", dangerSoft: "#F2D5D0",
            warning: "#8A5B00", warningSoft: "#F4E8CA", selection: "#E7CCC8",
            success: "#26734D", successSoft: "#D8EADD", panelRadius: 3, controlRadius: 2
        },
        aurora_spatial: {
            window: "#080B19", chrome: "#0E1126", surface: "#0A0E20",
            panel: "#151A39", panelAlt: "#242451", border: "#4B4F7B",
            tableGrid: "#34375D", panelHighlight: "#6C68A1", shadow: "#030511",
            text: "#F6F2FF", title: "#C9C2FF", secondary: "#AAA6C8", tertiary: "#777699",
            accent: "#8F7DFF", accentActive: "#7360E5", accentText: "#FFFFFF",
            accentSoft: "#332C70", glow: "#4CE5D0", glowSoft: "#174C4C",
            danger: "#FF6D92", dangerActive: "#E64B75", dangerSoft: "#4A2038",
            warning: "#F4C95D", warningSoft: "#453A1D", selection: "#42398C",
            success: "#4CE5D0", successSoft: "#164943", panelRadius: 18, controlRadius: 12
        },
        soft_3d: {
            window: "#E8EDF5", chrome: "#DEE6F1", surface: "#E8EDF5",
            panel: "#F4F7FB", panelAlt: "#E8EEF7", border: "#C2CDDB",
            tableGrid: "#D2DAE5", panelHighlight: "#FFFFFF", shadow: "#AAB6C8",
            text: "#273347", title: "#393653", secondary: "#5A687C", tertiary: "#7A8798",
            accent: "#6558D8", accentActive: "#5043BC", accentText: "#FFFFFF",
            accentSoft: "#DDD9F8", glow: "#8277E8", glowSoft: "#DDD9F8",
            danger: "#B94C61", dangerActive: "#9F384C", dangerSoft: "#F0D5DC",
            warning: "#9A5C22", warningSoft: "#F3E3D1", selection: "#D2D0F2",
            success: "#34785A", successSoft: "#D6E9DF", panelRadius: 22, controlRadius: 14
        }
    })

    property string themeId: "professional_dark"
    property string effectPolicy: "solid"
    readonly property var palette: palettes[themeId] || palettes.professional_dark
    readonly property int themeIndex: Math.max(0, themeIds.indexOf(themeId))
    readonly property string name: themes[themeIndex].name
    readonly property string description: themes[themeIndex].description
    readonly property bool isDark: themeId !== "editorial_minimal" && themeId !== "soft_3d"
    readonly property bool isGlass: ["nebula_navy", "liquid_glass", "aurora_spatial"].indexOf(themeId) >= 0

    readonly property color window: palette.window
    readonly property color chrome: palette.chrome
    readonly property color surface: palette.surface
    readonly property color panel: palette.panel
    readonly property color panelAlt: palette.panelAlt
    readonly property color border: palette.border
    readonly property color tableGrid: palette.tableGrid
    readonly property color panelHighlight: palette.panelHighlight
    readonly property color shadow: palette.shadow
    readonly property color text: palette.text
    readonly property color title: palette.title
    readonly property color secondary: palette.secondary
    readonly property color tertiary: palette.tertiary
    readonly property color accent: palette.accent
    readonly property color accentActive: palette.accentActive
    readonly property color accentText: palette.accentText
    readonly property color accentSoft: palette.accentSoft
    readonly property color glow: palette.glow
    readonly property color glowSoft: palette.glowSoft
    readonly property color danger: palette.danger
    readonly property color dangerActive: palette.dangerActive
    readonly property color dangerSoft: palette.dangerSoft
    readonly property color warning: palette.warning
    readonly property color warningSoft: palette.warningSoft
    readonly property color selection: palette.selection
    readonly property color success: palette.success
    readonly property color successSoft: palette.successSoft
    readonly property color canvas: "#15171B"

    readonly property color focus: accent
    readonly property color textDisabled: tertiary
    readonly property color input: panel
    readonly property color selectionText: text
    readonly property color borderHover: panelHighlight
    readonly property color control: panelAlt
    readonly property color controlHover: panelHighlight
    readonly property color controlPressed: accentSoft
    readonly property color controlSelected: accent
    readonly property color controlDisabled: surface
    readonly property color navText: secondary
    readonly property color navActiveText: text
    readonly property color navActive: accentSoft
    readonly property color navHover: panelAlt
    readonly property color navPressed: border
    readonly property color progressTrack: panelAlt
    readonly property color progress: accent
    readonly property color surfaceBorder: Qt.rgba(
        border.r, border.g, border.b, isDark ? 0.82 : 0.74)
    readonly property color surfaceHighlight: Qt.rgba(
        panelHighlight.r, panelHighlight.g, panelHighlight.b, isDark ? 0.18 : 0.72)
    readonly property color focusHalo: Qt.rgba(accent.r, accent.g, accent.b, 0.30)
    readonly property color overlayScrim: Qt.rgba(0.02, 0.025, 0.04, isDark ? 0.62 : 0.34)
    readonly property color subtleShadow: Qt.rgba(
        shadow.r, shadow.g, shadow.b, isDark ? 0.28 : 0.20)
    readonly property real panelRadius: palette.panelRadius
    readonly property real controlRadius: palette.controlRadius
    readonly property real radiusLarge: panelRadius
    readonly property real radiusMedium: controlRadius
    readonly property real materialOpacity: isGlass && effectPolicy === "native" ? 0.94 : 1.0
    readonly property color windowMaterial: Qt.rgba(
        window.r, window.g, window.b,
        isGlass && effectPolicy === "native" ? 0.76 : 1.0)
    readonly property color chromeMaterial: Qt.rgba(
        chrome.r, chrome.g, chrome.b,
        isGlass && effectPolicy === "native" ? 0.82 : 1.0)
    readonly property color panelMaterial: Qt.rgba(
        panel.r, panel.g, panel.b,
        isGlass && effectPolicy === "native" ? 0.88 : 1.0)

    readonly property int spaceXs: 4
    readonly property int spaceSm: 8
    readonly property int spaceMd: 12
    readonly property int spaceLg: 16
    readonly property int spaceXl: 24
    readonly property int spaceXxl: 32
    readonly property int controlHeight: 40
    readonly property int compactControlHeight: 34
    readonly property int sidebarWidth: 248
    readonly property int contentMargin: 24
    readonly property int panelPadding: 24
    readonly property int densePanelPadding: 16
    readonly property int fontCaption: 12
    readonly property int fontBody: 14
    readonly property int fontButton: 14
    readonly property int fontTitle: 20
    readonly property int fontHeading: 30
    readonly property string fontFamily: Qt.platform.os === "osx" ? "PingFang SC" : "Microsoft YaHei UI"
    readonly property font bodyFont: Qt.font({ family: fontFamily, pixelSize: fontBody })
    readonly property font buttonFont: Qt.font({ family: fontFamily, pixelSize: fontButton, weight: Font.DemiBold })

    function setTheme(requestedId) {
        themeId = themeIds.indexOf(requestedId) >= 0 ? requestedId : "professional_dark"
    }

    function setEffectPolicy(requestedPolicy) {
        effectPolicy = requestedPolicy === "native" ? "native" : "solid"
    }
}
