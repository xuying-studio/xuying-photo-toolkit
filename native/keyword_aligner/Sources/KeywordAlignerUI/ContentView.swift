import AppKit
import SwiftUI
import UniformTypeIdentifiers
import KeywordAlignerCore

public enum KeywordAlignerTheme: String, CaseIterable {
    case professional_dark, nebula_navy, liquid_glass, bento_modular, editorial_minimal, aurora_spatial, soft_3d
}

public enum AppPalette {
    static var theme = KeywordAlignerTheme.professional_dark
    static var background: Color { switch theme { case .editorial_minimal: return Color(red: 0.95, green: 0.93, blue: 0.89); case .bento_modular: return Color(red: 0.045, green: 0.055, blue: 0.09); case .aurora_spatial: return Color(red: 0.018, green: 0.035, blue: 0.10); case .soft_3d: return Color(red: 0.78, green: 0.83, blue: 0.89); case .liquid_glass: return Color(red: 0.07, green: 0.12, blue: 0.17); case .nebula_navy: return Color(red: 0.035, green: 0.05, blue: 0.11); case .professional_dark: return Color(red: 0.055, green: 0.065, blue: 0.078) } }
    static var panel: Color { switch theme { case .editorial_minimal: return Color.white.opacity(0.92); case .bento_modular: return Color(red: 0.12, green: 0.14, blue: 0.22); case .aurora_spatial: return Color(red: 0.05, green: 0.10, blue: 0.19); case .soft_3d: return Color(red: 0.90, green: 0.93, blue: 0.97); case .liquid_glass: return Color.white.opacity(0.42); case .nebula_navy: return Color(red: 0.07, green: 0.09, blue: 0.17); case .professional_dark: return Color(red: 0.09, green: 0.105, blue: 0.125) } }
    static var raised: Color { switch theme { case .editorial_minimal: return Color(red: 0.88, green: 0.86, blue: 0.81); case .bento_modular: return Color(red: 0.13, green: 0.17, blue: 0.28); case .aurora_spatial: return Color(red: 0.08, green: 0.18, blue: 0.26); case .soft_3d: return Color(red: 0.85, green: 0.89, blue: 0.94); case .liquid_glass: return Color.white.opacity(0.22); default: return Color(red: 0.125, green: 0.145, blue: 0.17) } }
    static var border: Color { theme == .editorial_minimal || theme == .soft_3d ? Color.black.opacity(0.18) : (theme == .aurora_spatial ? Color.cyan.opacity(0.28) : Color.white.opacity(0.15)) }
    static var cyan: Color { switch theme { case .editorial_minimal: return Color(red: 0.48, green: 0.16, blue: 0.12); case .bento_modular: return Color(red: 0.95, green: 0.43, blue: 0.12); case .aurora_spatial: return Color(red: 0.72, green: 0.42, blue: 1); case .soft_3d: return Color(red: 0.22, green: 0.38, blue: 0.52); case .liquid_glass: return Color(red: 0.18, green: 0.68, blue: 0.72); default: return Color(red: 0.22, green: 0.82, blue: 0.88) } }
    static var yellow: Color { theme == .editorial_minimal ? Color(red: 0.60, green: 0.20, blue: 0.12) : (theme == .aurora_spatial ? Color(red: 0.30, green: 0.90, blue: 0.70) : (theme == .bento_modular ? Color(red: 1, green: 0.58, blue: 0.18) : Color(red: 1, green: 0.77, blue: 0.18))) }
    static var red: Color { theme == .editorial_minimal ? Color(red: 0.58, green: 0.12, blue: 0.08) : Color(red: 1, green: 0.34, blue: 0.35) }
    static var muted: Color { theme == .editorial_minimal || theme == .soft_3d ? Color.black.opacity(0.62) : Color.white.opacity(0.62) }
    static var primaryText: Color { theme == .editorial_minimal || theme == .soft_3d ? .black : .white }
    static var panelRadius: CGFloat { switch theme { case .bento_modular: return 6; case .editorial_minimal: return 3; case .liquid_glass, .aurora_spatial: return 18; case .soft_3d: return 20; default: return 12 } }
    static var controlRadius: CGFloat { switch theme { case .bento_modular: return 5; case .editorial_minimal: return 3; case .liquid_glass: return 16; case .aurora_spatial: return 12; case .soft_3d: return 14; default: return 9 } }

    public static func setTheme(_ id: String) {
        theme = KeywordAlignerTheme(rawValue: id) ?? .professional_dark
    }
}

public struct ContentView: View {
    @ObservedObject var store: ProjectStore

    public init(store: ProjectStore) {
        self.store = store
    }

    public var body: some View {
        Group {
            if store.workflowStarted {
                EditorView(store: store)
            } else {
                SetupView(store: store)
            }
        }
        .preferredColorScheme(AppPalette.theme == .editorial_minimal || AppPalette.theme == .soft_3d ? .light : .dark)
        .background(AppPalette.background)
        .alert(
            "提示",
            isPresented: Binding(
                get: { store.alertMessage != nil },
                set: { if !$0 { store.alertMessage = nil } }
            )
        ) {
            Button("知道了") { store.alertMessage = nil }
        } message: {
            Text(store.alertMessage ?? "")
        }
    }
}

private struct SetupView: View {
    @ObservedObject var store: ProjectStore

    var body: some View {
        ZStack {
            AppPalette.background.ignoresSafeArea()
            VStack(spacing: 24) {
                HStack(alignment: .bottom) {
                    VStack(alignment: .leading, spacing: 7) {
                        Text("关键词对齐器")
                            .font(.system(size: 34, weight: .black, design: .rounded))
                        Text("把截图里的同一个词，稳定锁在同一块画面里")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(AppPalette.muted)
                    }
                    Spacer()
                    Text("OFFLINE · VISION OCR")
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .tracking(1.4)
                        .foregroundStyle(AppPalette.cyan)
                }

                HStack(alignment: .top, spacing: 18) {
                    VStack(spacing: 18) {
                        ToolPanel(title: "01 画面规格", subtitle: "先确定最终素材的画布和节奏") {
                            ProjectSpecControls(store: store, compact: false)
                        }

                        ToolPanel(title: "02 关键词", subtitle: "每批只输入一次，优先选择画面中间的同名词") {
                            HStack(spacing: 12) {
                                TextField("例如：婚礼摄影", text: $store.keyword)
                                    .textFieldStyle(.roundedBorder)
                                    .font(.system(size: 16, weight: .semibold))
                                Image(systemName: "viewfinder")
                                    .font(.system(size: 18, weight: .bold))
                                    .foregroundStyle(AppPalette.yellow)
                            }
                        }
                    }
                    .frame(maxWidth: 520)

                    VStack(spacing: 18) {
                        ImportPanel(store: store)
                        DurationSummaryCard(store: store, prominent: true)
                    }
                    .frame(maxWidth: .infinity)
                }

                if let error = store.settingsValidationMessage {
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(AppPalette.red)
                }

                HStack {
                    Text(store.operationMessage)
                        .font(.system(size: 12))
                        .foregroundStyle(AppPalette.muted)
                    Spacer()
                    Button {
                        store.startRecognition()
                    } label: {
                        HStack(spacing: 9) {
                            Text("开始识别并对齐")
                            Image(systemName: "arrow.right")
                        }
                        .font(.system(size: 15, weight: .bold))
                        .padding(.horizontal, 12)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppPalette.cyan)
                    .disabled(!store.canStartRecognition)
                    .keyboardShortcut(.return, modifiers: .command)
                }
            }
            .padding(30)
            .frame(maxWidth: 1180)
        }
        .onDrop(of: [UTType.fileURL], isTargeted: nil) { providers in
            FileDropLoader.load(providers, into: store)
        }
    }
}

private struct ToolPanel<Content: View>: View {
    let title: String
    let subtitle: String
    @ViewBuilder let content: Content

    init(title: String, subtitle: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.subtitle = subtitle
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 13, weight: .black, design: .monospaced))
                    .tracking(0.7)
                    .foregroundStyle(AppPalette.cyan)
                Text(subtitle)
                    .font(.system(size: 12))
                    .foregroundStyle(AppPalette.muted)
            }
            content
        }
        .padding(18)
        .background(AppPalette.panel)
        .overlay(RoundedRectangle(cornerRadius: AppPalette.panelRadius).stroke(AppPalette.border))
        .clipShape(RoundedRectangle(cornerRadius: AppPalette.panelRadius))
    }
}

private struct ProjectSpecControls: View {
    @ObservedObject var store: ProjectStore
    let compact: Bool

    private let columns = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        LazyVGrid(columns: columns, alignment: .leading, spacing: compact ? 10 : 14) {
            LabeledControl("画面比例") {
                Picker("画面比例", selection: Binding(
                    get: { store.aspectRatio },
                    set: { store.selectAspectRatio($0) }
                )) {
                    ForEach(AspectRatioPreset.allCases) { ratio in
                        Text(ratio.rawValue).tag(ratio)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            LabeledControl("常用分辨率") {
                Menu {
                    if store.aspectRatio.resolutions.isEmpty {
                        Text("自定义宽高")
                    } else {
                        ForEach(store.aspectRatio.resolutions) { resolution in
                            Button(resolution.label) { store.selectResolution(resolution) }
                        }
                    }
                } label: {
                    Text("\(store.widthText) × \(store.heightText)")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .menuStyle(.borderlessButton)
            }

            LabeledControl("宽度 px") {
                TextField("1080", text: Binding(
                    get: { store.widthText },
                    set: { store.updateWidth($0) }
                ))
                .textFieldStyle(.roundedBorder)
            }

            LabeledControl("高度 px") {
                TextField("1920", text: Binding(
                    get: { store.heightText },
                    set: { store.updateHeight($0) }
                ))
                .textFieldStyle(.roundedBorder)
                .disabled(store.aspectRatio != .custom)
                .opacity(store.aspectRatio == .custom ? 1 : 0.64)
            }

            LabeledControl("输出帧率") {
                HStack(spacing: 6) {
                    TextField("30", text: $store.frameRateText)
                        .textFieldStyle(.roundedBorder)
                    Menu {
                        ForEach(ProjectStore.frameRatePresets, id: \.self) { fps in
                            Button(frameRateLabel(fps)) { store.setFrameRate(fps) }
                        }
                    } label: {
                        Image(systemName: "chevron.down")
                    }
                    .menuStyle(.borderlessButton)
                    .frame(width: 18)
                }
            }

            LabeledControl("每张保持帧数") {
                HStack(spacing: 6) {
                    Button { store.incrementFrames(-1) } label: { Image(systemName: "minus") }
                        .buttonStyle(.borderless)
                    TextField("4", text: $store.framesPerImageText)
                        .textFieldStyle(.roundedBorder)
                        .multilineTextAlignment(.center)
                    Button { store.incrementFrames(1) } label: { Image(systemName: "plus") }
                        .buttonStyle(.borderless)
                }
            }
        }
    }

    private func frameRateLabel(_ value: Double) -> String {
        value.rounded() == value ? "\(Int(value)) fps" : "\(value) fps"
    }
}

private struct LabeledControl<Content: View>: View {
    let label: String
    @ViewBuilder let content: Content

    init(_ label: String, @ViewBuilder content: () -> Content) {
        self.label = label
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label)
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(AppPalette.muted)
            content
                .frame(minHeight: 24)
        }
    }
}

private struct ImportPanel: View {
    @ObservedObject var store: ProjectStore
    @State private var dropTargeted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("03 截图来源")
                        .font(.system(size: 13, weight: .black, design: .monospaced))
                        .tracking(0.7)
                        .foregroundStyle(AppPalette.cyan)
                    Text("文件夹只读取当前层，不扫描子目录")
                        .font(.system(size: 12))
                        .foregroundStyle(AppPalette.muted)
                }
                Spacer()
                Text("\(store.items.count) 张")
                    .font(.system(size: 20, weight: .black, design: .rounded))
                    .foregroundStyle(AppPalette.yellow)
            }

            VStack(spacing: 10) {
                Image(systemName: dropTargeted ? "arrow.down.doc.fill" : "folder.badge.plus")
                    .font(.system(size: 34, weight: .medium))
                    .foregroundStyle(dropTargeted ? AppPalette.yellow : AppPalette.cyan)
                Text(dropTargeted ? "松开即可导入" : "拖入图片或文件夹")
                    .font(.system(size: 16, weight: .bold))
                Text("PNG · JPG · HEIC")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundStyle(AppPalette.muted)
            }
            .frame(maxWidth: .infinity, minHeight: 116)
            .background(AppPalette.raised.opacity(dropTargeted ? 1 : 0.62))
            .overlay(
                RoundedRectangle(cornerRadius: AppPalette.controlRadius)
                    .stroke(dropTargeted ? AppPalette.yellow : AppPalette.border, style: StrokeStyle(lineWidth: 1.5, dash: [7, 6]))
            )
            .clipShape(RoundedRectangle(cornerRadius: AppPalette.controlRadius))
            .onDrop(of: [UTType.fileURL], isTargeted: $dropTargeted) { providers in
                FileDropLoader.load(providers, into: store)
            }

            HStack(spacing: 10) {
                Button { FilePicker.chooseImages(for: store) } label: {
                    Label("选择图片…", systemImage: "photo.on.rectangle")
                }
                    .buttonStyle(.bordered)
                Button { FilePicker.chooseFolder(for: store) } label: {
                    Label("选择文件夹…", systemImage: "folder")
                }
                    .buttonStyle(.bordered)
                Spacer()
                if store.ignoredFileCount > 0 {
                    Text("已忽略 \(store.ignoredFileCount) 个")
                        .font(.system(size: 11))
                        .foregroundStyle(AppPalette.muted)
                }
            }
        }
        .padding(18)
        .background(AppPalette.panel)
        .overlay(RoundedRectangle(cornerRadius: AppPalette.panelRadius).stroke(AppPalette.border))
        .clipShape(RoundedRectangle(cornerRadius: AppPalette.panelRadius))
    }
}

private struct DurationSummaryCard: View {
    @ObservedObject var store: ProjectStore
    let prominent: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                Label("预计成片时长", systemImage: "timer")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(AppPalette.muted)
                Spacer()
                if let timeline = store.timeline {
                    Text(timeline.timecode)
                        .font(.system(size: prominent ? 23 : 18, weight: .black, design: .monospaced))
                        .foregroundStyle(AppPalette.yellow)
                } else {
                    Text("--:--:--.---")
                        .font(.system(size: prominent ? 23 : 18, weight: .black, design: .monospaced))
                        .foregroundStyle(AppPalette.red)
                }
            }
            if let timeline = store.timeline {
                Text("\(store.items.count) 张 × \(timeline.framesPerImage) 帧 = \(timeline.totalFrames) 帧 · \(frameRateText(timeline.fps))fps · \(timeline.summary)")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(AppPalette.primaryText.opacity(0.8))
                if timeline.totalFrames > 30_000 {
                    Label("当前设置会产生大量帧文件或较大视频。", systemImage: "externaldrive.badge.exclamationmark")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(AppPalette.yellow)
                }
            } else {
                Text(store.settingsValidationMessage ?? "请完成帧率和保持帧数设置")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(AppPalette.red)
            }
        }
        .padding(prominent ? 18 : 14)
        .background(AppPalette.yellow.opacity(0.08))
        .overlay(RoundedRectangle(cornerRadius: AppPalette.controlRadius).stroke(AppPalette.yellow.opacity(0.32)))
        .clipShape(RoundedRectangle(cornerRadius: AppPalette.controlRadius))
    }

    private func frameRateText(_ value: Double) -> String {
        value.rounded() == value ? String(Int(value)) : String(value)
    }
}

private struct EditorView: View {
    @ObservedObject var store: ProjectStore

    var body: some View {
        VStack(spacing: 0) {
            EditorToolbar(store: store)
            Divider().overlay(AppPalette.border)
            HStack(spacing: 0) {
                ScreenshotSidebar(store: store)
                    .frame(width: 250)
                Divider().overlay(AppPalette.border)
                EditorCanvas(store: store)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                Divider().overlay(AppPalette.border)
                InspectorPanel(store: store)
                    .frame(width: 310)
            }
            Divider().overlay(AppPalette.border)
            OperationBar(store: store)
        }
        .background(AppPalette.background)
        .onDrop(of: [UTType.fileURL], isTargeted: nil) { providers in
            FileDropLoader.load(providers, into: store)
        }
    }
}

private struct EditorToolbar: View {
    @ObservedObject var store: ProjectStore

    var body: some View {
        HStack(spacing: 12) {
            Text("关键词对齐器")
                .font(.system(size: 16, weight: .black, design: .rounded))
            Text("\(store.widthText)×\(store.heightText) · \(store.frameRateText)fps")
                .font(.system(size: 11, weight: .bold, design: .monospaced))
                .foregroundStyle(AppPalette.muted)
            Spacer()
            Button { FilePicker.chooseImages(for: store) } label: {
                Label("添加图片", systemImage: "photo.badge.plus")
            }
            Button { FilePicker.chooseFolder(for: store) } label: {
                Label("添加文件夹", systemImage: "folder.badge.plus")
            }
            Button { store.startRecognition() } label: {
                Label("重新识别", systemImage: "text.viewfinder")
            }
                .disabled(!store.canStartRecognition)
            Button { store.resetProject() } label: {
                Label("新项目", systemImage: "arrow.counterclockwise")
            }
        }
        .buttonStyle(.borderless)
        .padding(.horizontal, 14)
        .frame(height: 44)
        .background(AppPalette.panel)
    }
}

private struct ScreenshotSidebar: View {
    @ObservedObject var store: ProjectStore

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("截图队列")
                    .font(.system(size: 12, weight: .bold))
                Spacer()
                Text("\(store.items.count)")
                    .font(.system(size: 11, weight: .black, design: .monospaced))
                    .foregroundStyle(AppPalette.cyan)
            }
            .padding(12)

            ScrollView {
                LazyVStack(spacing: 5) {
                    ForEach(Array(store.items.enumerated()), id: \.element.id) { index, item in
                        ScreenshotRow(index: index, item: item, selected: store.selectedItemID == item.id) {
                            store.selectedItemID = item.id
                        } remove: {
                            store.removeItem(item.id)
                        }
                        .onDrag {
                            NSItemProvider(object: item.id.uuidString as NSString)
                        }
                        .onDrop(of: [UTType.text], delegate: ItemReorderDropDelegate(targetID: item.id, store: store))
                    }
                }
                .padding(.horizontal, 7)
                .padding(.bottom, 12)
            }
        }
        .background(AppPalette.panel)
    }
}

private struct ScreenshotRow: View {
    let index: Int
    let item: ScreenshotItem
    let selected: Bool
    let select: () -> Void
    let remove: () -> Void

    var body: some View {
        HStack(spacing: 9) {
            Text(String(format: "%02d", index + 1))
                .font(.system(size: 10, weight: .black, design: .monospaced))
                .foregroundStyle(AppPalette.muted)
                .frame(width: 22)
            Image(nsImage: item.image)
                .resizable()
                .scaledToFill()
                .frame(width: 42, height: 52)
                .clipShape(RoundedRectangle(cornerRadius: 5))
            VStack(alignment: .leading, spacing: 5) {
                Text(item.url.lastPathComponent)
                    .font(.system(size: 11, weight: .semibold))
                    .lineLimit(1)
                Label(item.recognitionState.rawValue, systemImage: statusIcon)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(statusColor)
            }
            Spacer(minLength: 0)
            Button(action: remove) {
                Image(systemName: "xmark")
                    .font(.system(size: 9, weight: .bold))
            }
            .buttonStyle(.plain)
            .foregroundStyle(AppPalette.muted)
        }
        .padding(7)
        .background(selected ? AppPalette.cyan.opacity(0.15) : Color.clear)
        .overlay(RoundedRectangle(cornerRadius: 7).stroke(selected ? AppPalette.cyan.opacity(0.55) : Color.clear))
        .contentShape(Rectangle())
        .onTapGesture(perform: select)
    }

    private var statusIcon: String {
        switch item.recognitionState {
        case .matched: return "checkmark.circle.fill"
        case .fuzzyMatched: return "questionmark.circle.fill"
        case .notFound, .failed: return "exclamationmark.triangle.fill"
        case .recognizing: return "ellipsis.circle.fill"
        case .pending: return "circle.dotted"
        }
    }

    private var statusColor: Color {
        switch item.recognitionState {
        case .matched: return AppPalette.cyan
        case .fuzzyMatched: return AppPalette.yellow
        case .notFound, .failed: return AppPalette.red
        case .recognizing, .pending: return AppPalette.muted
        }
    }
}

private struct EditorCanvas: View {
    @ObservedObject var store: ProjectStore

    var body: some View {
        GeometryReader { proxy in
            if let item = store.selectedItem, let settings = store.currentSettings {
                let canvasSize = fittedSize(
                    contentAspect: Double(settings.width) / Double(settings.height),
                    inside: CGSize(width: max(proxy.size.width - 52, 1), height: max(proxy.size.height - 52, 1))
                )
                CanvasContent(item: item, settings: settings, canvasSize: canvasSize, store: store)
                    .frame(width: canvasSize.width, height: canvasSize.height)
                    .position(x: proxy.size.width / 2, y: proxy.size.height / 2)
                    .shadow(color: .black.opacity(0.45), radius: 22, y: 10)
            } else {
                VStack(spacing: 12) {
                    Image(systemName: "photo.on.rectangle.angled")
                        .font(.system(size: 40))
                    Text("拖入截图开始")
                        .font(.system(size: 16, weight: .bold))
                }
                .foregroundStyle(AppPalette.muted)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .background(
            CanvasGrid()
                .opacity(0.22)
                .background(AppPalette.background)
        )
    }

    private func fittedSize(contentAspect: Double, inside available: CGSize) -> CGSize {
        if available.width / available.height > contentAspect {
            return CGSize(width: available.height * contentAspect, height: available.height)
        }
        return CGSize(width: available.width, height: available.width / contentAspect)
    }
}

private struct CanvasGrid: View {
    var body: some View {
        Canvas { context, size in
            var path = Path()
            let spacing: CGFloat = 28
            stride(from: 0, through: size.width, by: spacing).forEach {
                path.move(to: CGPoint(x: $0, y: 0))
                path.addLine(to: CGPoint(x: $0, y: size.height))
            }
            stride(from: 0, through: size.height, by: spacing).forEach {
                path.move(to: CGPoint(x: 0, y: $0))
                path.addLine(to: CGPoint(x: size.width, y: $0))
            }
            context.stroke(path, with: .color(.white.opacity(0.15)), lineWidth: 0.5)
        }
    }
}

private struct CanvasContent: View {
    let item: ScreenshotItem
    let settings: ProjectSettings
    let canvasSize: CGSize
    @ObservedObject var store: ProjectStore

    var body: some View {
        let selectedBox = item.selectedCandidate?.box
        let geometry = AlignmentMath.geometry(
            inputWidth: item.pixelSize.width,
            inputHeight: item.pixelSize.height,
            outputWidth: Double(settings.width),
            outputHeight: Double(settings.height),
            selectedBox: selectedBox,
            targetBox: settings.targetRect
        )

        ZStack(alignment: .topLeading) {
            Color.white
            Image(nsImage: item.image)
                .resizable()
                .frame(
                    width: geometry.drawnWidth / Double(settings.width) * canvasSize.width,
                    height: geometry.drawnHeight / Double(settings.height) * canvasSize.height
                )
                .position(
                    x: (geometry.originX + geometry.drawnWidth / 2) / Double(settings.width) * canvasSize.width,
                    y: (geometry.originY + geometry.drawnHeight / 2) / Double(settings.height) * canvasSize.height
                )
                .allowsHitTesting(false)

            ForEach(item.candidates) { candidate in
                let transformed = AlignmentMath.transformedBox(
                    candidate.box,
                    inputWidth: item.pixelSize.width,
                    inputHeight: item.pixelSize.height,
                    outputWidth: Double(settings.width),
                    outputHeight: Double(settings.height),
                    geometry: geometry
                )
                CandidateOverlay(
                    rect: pixelRect(transformed),
                    selected: item.selectedCandidateID == candidate.id,
                    exact: candidate.isExactMatch
                ) {
                    store.selectCandidate(itemID: item.id, candidateID: candidate.id)
                }
            }

            TargetBoxOverlay(rect: settings.targetRect, canvasSize: canvasSize) { rect in
                store.updateTargetRect(rect)
            }
        }
        .frame(width: canvasSize.width, height: canvasSize.height)
        .clipped()
        .overlay(Rectangle().stroke(Color.white.opacity(0.22), lineWidth: 1))
    }

    private func pixelRect(_ rect: NormalizedRect) -> CGRect {
        CGRect(
            x: rect.x * canvasSize.width,
            y: rect.y * canvasSize.height,
            width: rect.width * canvasSize.width,
            height: rect.height * canvasSize.height
        )
    }
}

private struct CandidateOverlay: View {
    let rect: CGRect
    let selected: Bool
    let exact: Bool
    let select: () -> Void

    var body: some View {
        Rectangle()
            .fill((selected ? AppPalette.cyan : AppPalette.red).opacity(selected ? 0.12 : 0.04))
            .overlay(
                Rectangle()
                    .stroke(selected ? AppPalette.cyan : (exact ? AppPalette.yellow : AppPalette.red), lineWidth: selected ? 2 : 1)
            )
            .frame(width: max(rect.width, 4), height: max(rect.height, 4))
            .position(x: rect.midX, y: rect.midY)
            .contentShape(Rectangle())
            .onTapGesture(perform: select)
    }
}

private struct TargetBoxOverlay: View {
    let rect: NormalizedRect
    let canvasSize: CGSize
    let update: (NormalizedRect) -> Void
    @State private var moveStart: NormalizedRect?
    @State private var resizeStart: NormalizedRect?

    var body: some View {
        let pixelRect = CGRect(
            x: rect.x * canvasSize.width,
            y: rect.y * canvasSize.height,
            width: rect.width * canvasSize.width,
            height: rect.height * canvasSize.height
        )

        ZStack(alignment: .topLeading) {
            Rectangle()
                .fill(AppPalette.yellow.opacity(0.08))
                .overlay(
                    Rectangle().stroke(AppPalette.yellow, style: StrokeStyle(lineWidth: 2, dash: [7, 4]))
                )
                .frame(width: pixelRect.width, height: pixelRect.height)
                .position(x: pixelRect.midX, y: pixelRect.midY)
                .contentShape(Rectangle())
                .gesture(
                    DragGesture()
                        .onChanged { value in
                            if moveStart == nil { moveStart = rect }
                            guard let start = moveStart else { return }
                            update(NormalizedRect(
                                x: start.x + value.translation.width / canvasSize.width,
                                y: start.y + value.translation.height / canvasSize.height,
                                width: start.width,
                                height: start.height
                            ).clamped())
                        }
                        .onEnded { _ in moveStart = nil }
                )

            Circle()
                .fill(AppPalette.yellow)
                .overlay(Circle().stroke(Color.black.opacity(0.5), lineWidth: 1))
                .frame(width: 13, height: 13)
                .position(x: pixelRect.maxX, y: pixelRect.maxY)
                .contentShape(Circle().size(width: 28, height: 28))
                .highPriorityGesture(
                    DragGesture()
                        .onChanged { value in
                            if resizeStart == nil { resizeStart = rect }
                            guard let start = resizeStart else { return }
                            update(NormalizedRect(
                                x: start.x,
                                y: start.y,
                                width: start.width + value.translation.width / canvasSize.width,
                                height: start.height + value.translation.height / canvasSize.height
                            ).clamped())
                        }
                        .onEnded { _ in resizeStart = nil }
                )

            Text("关键词目标框")
                .font(.system(size: 9, weight: .black, design: .monospaced))
                .padding(.horizontal, 5)
                .padding(.vertical, 3)
                .background(AppPalette.yellow)
                .foregroundStyle(.black)
                .position(x: pixelRect.minX + 42, y: max(pixelRect.minY - 9, 9))
                .allowsHitTesting(false)
        }
    }
}

private struct InspectorPanel: View {
    @ObservedObject var store: ProjectStore

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                InspectorSection("识别") {
                    LabeledControl("关键词") {
                        TextField("关键词", text: $store.keyword)
                            .textFieldStyle(.roundedBorder)
                    }
                    Button { store.startRecognition() } label: {
                        Label("重新识别全部", systemImage: "text.viewfinder")
                    }
                        .buttonStyle(.bordered)
                        .disabled(!store.canStartRecognition)
                    if let message = store.selectedItem?.recognitionMessage {
                        Label(message, systemImage: "exclamationmark.triangle.fill")
                            .font(.system(size: 11))
                            .foregroundStyle(AppPalette.yellow)
                    }
                }

                InspectorSection("画面与节奏") {
                    ProjectSpecControls(store: store, compact: true)
                }

                DurationSummaryCard(store: store, prominent: false)

                InspectorSection("导出") {
                    LabeledControl("格式") {
                        Picker("导出格式", selection: $store.exportMode) {
                            ForEach(ExportMode.allCases) { mode in
                                Text(mode.rawValue).tag(mode)
                            }
                        }
                        .labelsHidden()
                        .pickerStyle(.segmented)
                    }

                    Button {
                        FilePicker.chooseExportFolder(for: store)
                    } label: {
                        Label("选择位置并导出", systemImage: "square.and.arrow.up")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppPalette.cyan)
                    .disabled(!store.canExport)

                    if let url = store.lastExportURL {
                        Button {
                            NSWorkspace.shared.activateFileViewerSelecting([url])
                        } label: {
                            Label("打开导出文件夹", systemImage: "folder.fill")
                        }
                        .buttonStyle(.bordered)
                    }
                }
            }
            .padding(14)
        }
        .background(AppPalette.panel)
    }
}

private struct InspectorSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    init(_ title: String, @ViewBuilder content: () -> Content) {
        self.title = title
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 11) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .black, design: .monospaced))
                .tracking(1.1)
                .foregroundStyle(AppPalette.cyan)
            content
        }
        .padding(13)
        .background(AppPalette.raised.opacity(0.7))
        .overlay(RoundedRectangle(cornerRadius: AppPalette.panelRadius).stroke(AppPalette.border))
        .clipShape(RoundedRectangle(cornerRadius: AppPalette.panelRadius))
    }
}

private struct OperationBar: View {
    @ObservedObject var store: ProjectStore

    var body: some View {
        HStack(spacing: 12) {
            if store.isRecognizing || store.isExporting {
                ProgressView(value: store.operationProgress)
                    .progressViewStyle(.linear)
                    .frame(width: 180)
                Button("取消") { store.cancelCurrentOperation() }
                    .buttonStyle(.borderless)
                    .foregroundStyle(AppPalette.red)
            } else {
                Circle()
                    .fill(store.failedRecognitionCount == 0 ? AppPalette.cyan : AppPalette.yellow)
                    .frame(width: 7, height: 7)
            }
            Text(store.operationMessage.isEmpty ? "就绪" : store.operationMessage)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(AppPalette.muted)
                .lineLimit(1)
            Spacer()
            if let timeline = store.timeline {
                Text("\(timeline.totalFrames) FRAMES  ·  \(timeline.timecode)")
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .foregroundStyle(AppPalette.yellow)
            }
        }
        .padding(.horizontal, 13)
        .frame(height: 34)
        .background(AppPalette.panel)
    }
}

private struct ItemReorderDropDelegate: DropDelegate {
    let targetID: UUID
    @ObservedObject var store: ProjectStore

    func dropEntered(info: DropInfo) {
        guard let provider = info.itemProviders(for: [UTType.text]).first else { return }
        provider.loadObject(ofClass: NSString.self) { object, _ in
            guard let value = object as? String, let draggedID = UUID(uuidString: value) else { return }
            Task { @MainActor in
                store.moveItem(draggedID, before: targetID)
            }
        }
    }

    func performDrop(info: DropInfo) -> Bool { true }
}

private enum FilePicker {
    @MainActor
    static func chooseImages(for store: ProjectStore) {
        let panel = NSOpenPanel()
        panel.title = "选择截图"
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        panel.allowedContentTypes = [.png, .jpeg, .heic]
        if panel.runModal() == .OK {
            store.addInputURLs(panel.urls)
        }
    }

    @MainActor
    static func chooseFolder(for store: ProjectStore) {
        let panel = NSOpenPanel()
        panel.title = "选择截图文件夹（只读取当前层）"
        panel.prompt = "导入这个文件夹"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            store.addInputURLs([url])
        }
    }

    @MainActor
    static func chooseExportFolder(for store: ProjectStore) {
        let panel = NSOpenPanel()
        panel.title = "选择导出位置"
        panel.prompt = "导出到这里"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            store.startExport(to: url)
        }
    }
}

private enum FileDropLoader {
    static func load(_ providers: [NSItemProvider], into store: ProjectStore) -> Bool {
        let matching = providers.filter { $0.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) }
        guard !matching.isEmpty else { return false }
        let lock = NSLock()
        let group = DispatchGroup()
        var urls: [URL] = []
        for provider in matching {
            group.enter()
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                defer { group.leave() }
                var url: URL?
                if let itemURL = item as? URL {
                    url = itemURL
                } else if let data = item as? Data {
                    url = URL(dataRepresentation: data, relativeTo: nil)
                } else if let nsURL = item as? NSURL {
                    url = nsURL as URL
                }
                guard let url else { return }
                lock.lock()
                urls.append(url)
                lock.unlock()
            }
        }
        group.notify(queue: .main) {
            lock.lock()
            let collectedURLs = urls
            lock.unlock()
            Task { @MainActor in
                store.addInputURLs(collectedURLs)
            }
        }
        return true
    }
}
