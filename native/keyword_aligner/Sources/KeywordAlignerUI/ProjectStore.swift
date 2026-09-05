import AppKit
import Combine
import Foundation
import KeywordAlignerCore

struct ScreenshotItem: Identifiable {
    let id: UUID
    let url: URL
    let image: NSImage
    let pixelSize: CGSize
    var candidates: [OCRCandidate]
    var selectedCandidateID: UUID?
    var recognitionState: RecognitionState
    var recognitionMessage: String?

    init(url: URL, image: NSImage, pixelSize: CGSize) {
        id = UUID()
        self.url = url
        self.image = image
        self.pixelSize = pixelSize
        candidates = []
        selectedCandidateID = nil
        recognitionState = .pending
        recognitionMessage = nil
    }

    var selectedCandidate: OCRCandidate? {
        guard let selectedCandidateID else { return nil }
        return candidates.first(where: { $0.id == selectedCandidateID })
    }
}

@MainActor
public final class ProjectStore: ObservableObject {
    static let supportedExtensions = Set(["png", "jpg", "jpeg", "heic"])
    static let frameRatePresets: [Double] = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]
    static let defaultTargetRect = NormalizedRect(x: 0.33, y: 0.475, width: 0.34, height: 0.05)

    @Published var aspectRatio: AspectRatioPreset { didSet { persistSettingsIfValid() } }
    @Published var widthText: String { didSet { persistSettingsIfValid() } }
    @Published var heightText: String { didSet { persistSettingsIfValid() } }
    @Published var frameRateText: String { didSet { persistSettingsIfValid() } }
    @Published var framesPerImageText: String { didSet { persistSettingsIfValid() } }
    @Published var keyword: String { didSet { persistSettingsIfValid() } }
    @Published var targetRect: NormalizedRect { didSet { persistSettingsIfValid() } }
    @Published var exportMode: ExportMode { didSet { persistSettingsIfValid() } }

    @Published var items: [ScreenshotItem] = []
    @Published var selectedItemID: UUID?
    @Published var workflowStarted = false
    @Published var isRecognizing = false
    @Published var isExporting = false
    @Published var operationProgress = 0.0
    @Published var operationMessage = ""
    @Published var ignoredFileCount = 0
    @Published var lastExportURL: URL?
    @Published var alertMessage: String?

    private var ocrCache: [String: [OCRCandidate]] = [:]
    private var operationTask: Task<Void, Never>?
    private var cancellationToken: CancellationToken?
    private let defaultsKey = "KeywordAligner.ProjectSettings.v1"

    public init() {
        let currentData = UserDefaults.standard.data(forKey: defaultsKey)
        let legacyData = UserDefaults(suiteName: "com.xuying.keyword-aligner")?
            .data(forKey: defaultsKey)
        let savedData = currentData ?? legacyData
        if currentData == nil, let legacyData {
            // 只把旧版设置复制到当前应用域，不反向改写独立版配置。
            UserDefaults.standard.set(legacyData, forKey: defaultsKey)
        }
        if let data = savedData,
           let saved = try? JSONDecoder().decode(ProjectSettings.self, from: data) {
            aspectRatio = saved.aspectRatio
            widthText = String(saved.width)
            heightText = String(saved.height)
            frameRateText = Self.displayFrameRate(saved.frameRate)
            framesPerImageText = String(saved.framesPerImage)
            keyword = saved.keyword
            targetRect = saved.targetRect.clamped()
            exportMode = saved.exportMode
        } else {
            let settings = ProjectSettings()
            aspectRatio = settings.aspectRatio
            widthText = String(settings.width)
            heightText = String(settings.height)
            frameRateText = Self.displayFrameRate(settings.frameRate)
            framesPerImageText = String(settings.framesPerImage)
            keyword = settings.keyword
            targetRect = settings.targetRect
            exportMode = settings.exportMode
        }
    }

    public var isBusy: Bool { isRecognizing || isExporting }

    var width: Int? { Int(widthText.trimmingCharacters(in: .whitespaces)) }
    var height: Int? { Int(heightText.trimmingCharacters(in: .whitespaces)) }
    var frameRate: Double? { Double(frameRateText.trimmingCharacters(in: .whitespaces)) }
    var framesPerImage: Int? { Int(framesPerImageText.trimmingCharacters(in: .whitespaces)) }

    var settingsValidationMessage: String? {
        guard let width, let height else { return "请输入有效的画面宽高。" }
        guard (64...8192).contains(width), (64...8192).contains(height) else {
            return "画面宽高需要在 64–8192 像素之间。"
        }
        guard width.isMultiple(of: 2), height.isMultiple(of: 2) else {
            return "画面宽高必须是偶数，才能稳定导出 MP4。"
        }
        guard let frameRate, frameRate.isFinite, (1...120).contains(frameRate) else {
            return "帧率需要在 1–120fps 之间。"
        }
        guard let framesPerImage, (1...10_000).contains(framesPerImage) else {
            return "每张保持帧数需要是 1–10000 的整数。"
        }
        return nil
    }

    var currentSettings: ProjectSettings? {
        guard settingsValidationMessage == nil,
              let width, let height, let frameRate, let framesPerImage else { return nil }
        return ProjectSettings(
            aspectRatio: aspectRatio,
            width: width,
            height: height,
            frameRate: frameRate,
            framesPerImage: framesPerImage,
            keyword: keyword.trimmingCharacters(in: .whitespacesAndNewlines),
            targetRect: targetRect.clamped(),
            exportMode: exportMode
        )
    }

    var timeline: TimelineMath? {
        guard let frameRate, let framesPerImage else { return nil }
        return try? TimelineMath(imageCount: items.count, framesPerImage: framesPerImage, fps: frameRate)
    }

    var canStartRecognition: Bool {
        currentSettings != nil && !items.isEmpty && !keyword.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isRecognizing && !isExporting
    }

    var canExport: Bool {
        currentSettings != nil && !items.isEmpty && !keyword.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isExporting && !isRecognizing
    }

    var selectedItem: ScreenshotItem? {
        guard let selectedItemID else { return items.first }
        return items.first(where: { $0.id == selectedItemID }) ?? items.first
    }

    var failedRecognitionCount: Int {
        items.filter { $0.recognitionState == .notFound || $0.recognitionState == .failed }.count
    }

    func selectAspectRatio(_ newValue: AspectRatioPreset) {
        let changed = aspectRatio != newValue
        aspectRatio = newValue
        if newValue != .custom {
            selectResolution(newValue.defaultResolution)
        }
        if changed {
            targetRect = Self.defaultTargetRect
        }
    }

    func selectResolution(_ resolution: ResolutionPreset) {
        widthText = String(resolution.width)
        heightText = String(resolution.height)
    }

    func updateWidth(_ value: String) {
        widthText = value.filter { $0.isNumber }
        guard aspectRatio != .custom,
              let ratio = aspectRatio.numericRatio,
              let width = Int(widthText), width > 0 else { return }
        var calculatedHeight = Int((Double(width) / ratio).rounded())
        if !calculatedHeight.isMultiple(of: 2) { calculatedHeight += 1 }
        heightText = String(calculatedHeight)
    }

    func updateHeight(_ value: String) {
        guard aspectRatio == .custom else { return }
        heightText = value.filter { $0.isNumber }
    }

    func setFrameRate(_ value: Double) {
        frameRateText = Self.displayFrameRate(value)
    }

    func incrementFrames(_ delta: Int) {
        let current = framesPerImage ?? 4
        framesPerImageText = String(min(max(current + delta, 1), 10_000))
    }

    func addInputURLs(_ urls: [URL]) {
        var ignored = 0
        var candidates: [URL] = []
        for url in urls {
            let values = try? url.resourceValues(forKeys: [.isDirectoryKey, .isRegularFileKey, .isHiddenKey])
            if values?.isDirectory == true {
                let children = (try? FileManager.default.contentsOfDirectory(
                    at: url,
                    includingPropertiesForKeys: [.isRegularFileKey, .isHiddenKey],
                    options: [.skipsHiddenFiles]
                )) ?? []
                for child in children {
                    let childValues = try? child.resourceValues(forKeys: [.isRegularFileKey, .isHiddenKey])
                    if childValues?.isRegularFile == true, isSupportedImage(child), childValues?.isHidden != true {
                        candidates.append(child)
                    } else {
                        ignored += 1
                    }
                }
            } else if values?.isRegularFile == true, isSupportedImage(url), values?.isHidden != true {
                candidates.append(url)
            } else {
                ignored += 1
            }
        }

        let existingPaths = Set(items.map { canonicalPath($0.url) })
        var seen = existingPaths
        var newItems: [ScreenshotItem] = []
        for url in candidates.sorted(by: { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }) {
            let path = canonicalPath(url)
            guard !seen.contains(path) else {
                ignored += 1
                continue
            }
            do {
                let image = try ImageRenderer.loadImage(url)
                newItems.append(ScreenshotItem(url: url, image: image, pixelSize: ImageRenderer.pixelSize(of: image)))
                seen.insert(path)
            } catch {
                ignored += 1
            }
        }

        items.append(contentsOf: newItems)
        ignoredFileCount = ignored
        if selectedItemID == nil {
            selectedItemID = items.first?.id
        }
        if !newItems.isEmpty {
            operationMessage = "已导入 \(newItems.count) 张图片" + (ignored > 0 ? "，忽略 \(ignored) 个文件" : "")
        } else if ignored > 0 {
            operationMessage = "没有新增图片，忽略了 \(ignored) 个文件"
        }
    }

    func removeItem(_ id: UUID) {
        guard let index = items.firstIndex(where: { $0.id == id }) else { return }
        items.remove(at: index)
        if selectedItemID == id {
            selectedItemID = items.indices.contains(index) ? items[index].id : items.last?.id
        }
    }

    func moveItem(_ draggedID: UUID, before targetID: UUID) {
        guard draggedID != targetID,
              let sourceIndex = items.firstIndex(where: { $0.id == draggedID }),
              let targetIndex = items.firstIndex(where: { $0.id == targetID }) else { return }
        let item = items.remove(at: sourceIndex)
        let adjustedTarget = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex
        items.insert(item, at: adjustedTarget)
    }

    func selectCandidate(itemID: UUID, candidateID: UUID) {
        guard let index = items.firstIndex(where: { $0.id == itemID }) else { return }
        items[index].selectedCandidateID = candidateID
        if let candidate = items[index].candidates.first(where: { $0.id == candidateID }) {
            items[index].recognitionState = candidate.isExactMatch ? .matched : .fuzzyMatched
        }
    }

    func updateTargetRect(_ rect: NormalizedRect) {
        targetRect = rect.clamped()
    }

    func startRecognition() {
        guard canStartRecognition else { return }
        workflowStarted = true
        isRecognizing = true
        operationProgress = 0
        operationMessage = "正在准备 OCR…"
        let token = CancellationToken()
        cancellationToken = token
        let trimmedKeyword = keyword.trimmingCharacters(in: .whitespacesAndNewlines)

        operationTask?.cancel()
        operationTask = Task { [weak self] in
            guard let self else { return }
            for itemIndex in self.items.indices {
                if token.isCancelled || Task.isCancelled { break }
                let url = self.items[itemIndex].url
                let cacheKey = self.ocrCacheKey(url: url, keyword: trimmedKeyword)
                self.items[itemIndex].recognitionState = .recognizing
                self.items[itemIndex].recognitionMessage = nil
                self.operationMessage = "正在识别 \(itemIndex + 1)/\(self.items.count)：\(url.lastPathComponent)"

                do {
                    let candidates: [OCRCandidate]
                    if let cached = self.ocrCache[cacheKey] {
                        candidates = cached
                    } else {
                        candidates = try await Task.detached(priority: .userInitiated) {
                            try OCRService.recognize(url: url, keyword: trimmedKeyword)
                        }.value
                        self.ocrCache[cacheKey] = candidates
                    }
                    guard self.items.indices.contains(itemIndex) else { continue }
                    self.items[itemIndex].candidates = candidates
                    self.items[itemIndex].selectedCandidateID = candidates.first?.id
                    if let first = candidates.first {
                        self.items[itemIndex].recognitionState = first.isExactMatch ? .matched : .fuzzyMatched
                        self.items[itemIndex].recognitionMessage = first.isExactMatch ? nil : "未找到完全一致文字，已使用最接近结果"
                    } else {
                        self.items[itemIndex].recognitionState = .notFound
                        self.items[itemIndex].recognitionMessage = "没有识别到关键词，将按原图居中输出"
                    }
                } catch {
                    guard self.items.indices.contains(itemIndex) else { continue }
                    self.items[itemIndex].recognitionState = .failed
                    self.items[itemIndex].recognitionMessage = error.localizedDescription
                }
                self.operationProgress = Double(itemIndex + 1) / Double(max(self.items.count, 1))
            }

            self.isRecognizing = false
            if token.isCancelled || Task.isCancelled {
                self.operationMessage = "识别已取消"
            } else {
                self.operationProgress = 1
                self.operationMessage = self.failedRecognitionCount == 0
                    ? "识别完成，所有图片都已找到候选关键词"
                    : "识别完成，\(self.failedRecognitionCount) 张图片需要留意"
            }
        }
    }

    func startExport(to destination: URL) {
        guard let settings = currentSettings, canExport else { return }
        isExporting = true
        operationProgress = 0
        operationMessage = "正在准备导出…"
        lastExportURL = nil
        let exportItems = items.map { ExportItem(url: $0.url, selectedBox: $0.selectedCandidate?.box) }
        let token = CancellationToken()
        cancellationToken = token

        operationTask?.cancel()
        operationTask = Task { [weak self] in
            guard let self else { return }
            do {
                let url = try await Task.detached(priority: .userInitiated) {
                    try await ExportService.export(
                        items: exportItems,
                        settings: settings,
                        destination: destination,
                        token: token
                    ) { progress, message in
                        Task { @MainActor [weak self] in
                            self?.operationProgress = progress
                            self?.operationMessage = message
                        }
                    }
                }.value
                self.lastExportURL = url
                self.operationProgress = 1
                self.operationMessage = "导出完成"
            } catch {
                self.alertMessage = error.localizedDescription
                self.operationMessage = error.localizedDescription
            }
            self.isExporting = false
        }
    }

    public func cancelCurrentOperation() {
        cancellationToken?.cancel()
        operationTask?.cancel()
        operationMessage = "正在取消…"
    }

    public func resetProject() {
        cancelCurrentOperation()
        items.removeAll()
        selectedItemID = nil
        workflowStarted = false
        ignoredFileCount = 0
        operationProgress = 0
        operationMessage = ""
        lastExportURL = nil
    }

    private func persistSettingsIfValid() {
        guard let settings = currentSettings,
              let data = try? JSONEncoder().encode(settings) else { return }
        UserDefaults.standard.set(data, forKey: defaultsKey)
    }

    private func isSupportedImage(_ url: URL) -> Bool {
        Self.supportedExtensions.contains(url.pathExtension.lowercased())
    }

    private func canonicalPath(_ url: URL) -> String {
        url.standardizedFileURL.resolvingSymlinksInPath().path
    }

    private func ocrCacheKey(url: URL, keyword: String) -> String {
        let modified = (try? url.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate?.timeIntervalSince1970) ?? 0
        return "\(canonicalPath(url))|\(modified)|\(keyword)"
    }

    private static func displayFrameRate(_ value: Double) -> String {
        value.rounded() == value ? String(Int(value)) : String(format: "%.3f", value).replacingOccurrences(of: #"0+$"#, with: "", options: .regularExpression).replacingOccurrences(of: #"\.$"#, with: "", options: .regularExpression)
    }
}
