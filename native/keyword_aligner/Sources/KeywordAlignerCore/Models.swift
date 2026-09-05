import Foundation

public struct NormalizedRect: Codable, Equatable, Hashable, Sendable {
    public var x: Double
    public var y: Double
    public var width: Double
    public var height: Double

    public init(x: Double, y: Double, width: Double, height: Double) {
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    }

    public var centerX: Double { x + width / 2 }
    public var centerY: Double { y + height / 2 }

    public func clamped() -> NormalizedRect {
        let safeWidth = min(max(width, 0.01), 1)
        let safeHeight = min(max(height, 0.01), 1)
        return NormalizedRect(
            x: min(max(x, 0), 1 - safeWidth),
            y: min(max(y, 0), 1 - safeHeight),
            width: safeWidth,
            height: safeHeight
        )
    }
}

public struct ResolutionPreset: Identifiable, Equatable, Hashable, Sendable {
    public let width: Int
    public let height: Int

    public init(width: Int, height: Int) {
        self.width = width
        self.height = height
    }

    public var id: String { "\(width)x\(height)" }
    public var label: String { "\(width) × \(height)" }
}

public enum AspectRatioPreset: String, CaseIterable, Codable, Identifiable, Sendable {
    case portrait = "9:16"
    case landscape = "16:9"
    case square = "1:1"
    case socialPortrait = "4:5"
    case classicPortrait = "3:4"
    case custom = "自定义"

    public var id: String { rawValue }

    public var numericRatio: Double? {
        switch self {
        case .portrait: return 9.0 / 16.0
        case .landscape: return 16.0 / 9.0
        case .square: return 1
        case .socialPortrait: return 4.0 / 5.0
        case .classicPortrait: return 3.0 / 4.0
        case .custom: return nil
        }
    }

    public var resolutions: [ResolutionPreset] {
        switch self {
        case .portrait:
            return [.init(width: 720, height: 1280), .init(width: 1080, height: 1920), .init(width: 2160, height: 3840)]
        case .landscape:
            return [.init(width: 1280, height: 720), .init(width: 1920, height: 1080), .init(width: 3840, height: 2160)]
        case .square:
            return [.init(width: 720, height: 720), .init(width: 1080, height: 1080), .init(width: 2160, height: 2160)]
        case .socialPortrait:
            return [.init(width: 864, height: 1080), .init(width: 1080, height: 1350), .init(width: 2160, height: 2700)]
        case .classicPortrait:
            return [.init(width: 810, height: 1080), .init(width: 1080, height: 1440), .init(width: 2160, height: 2880)]
        case .custom:
            return []
        }
    }

    public var defaultResolution: ResolutionPreset {
        resolutions.dropFirst().first ?? ResolutionPreset(width: 1080, height: 1920)
    }
}

public enum ExportMode: String, CaseIterable, Codable, Identifiable, Sendable {
    case alignedPNGs = "处理后 PNG"
    case frameSequence = "逐帧 PNG"
    case mp4 = "MP4"

    public var id: String { rawValue }
}

public struct ProjectSettings: Codable, Equatable, Sendable {
    public var aspectRatio: AspectRatioPreset
    public var width: Int
    public var height: Int
    public var frameRate: Double
    public var framesPerImage: Int
    public var keyword: String
    public var targetRect: NormalizedRect
    public var exportMode: ExportMode

    public init(
        aspectRatio: AspectRatioPreset = .portrait,
        width: Int = 1080,
        height: Int = 1920,
        frameRate: Double = 30,
        framesPerImage: Int = 4,
        keyword: String = "",
        targetRect: NormalizedRect = .init(x: 0.33, y: 0.475, width: 0.34, height: 0.05),
        exportMode: ExportMode = .mp4
    ) {
        self.aspectRatio = aspectRatio
        self.width = width
        self.height = height
        self.frameRate = frameRate
        self.framesPerImage = framesPerImage
        self.keyword = keyword
        self.targetRect = targetRect
        self.exportMode = exportMode
    }
}

public struct OCRCandidate: Identifiable, Equatable, Hashable, Sendable {
    public let id: UUID
    public let text: String
    public let box: NormalizedRect
    public let confidence: Float
    public let isExactMatch: Bool
    public let similarity: Double

    public init(
        id: UUID = UUID(),
        text: String,
        box: NormalizedRect,
        confidence: Float,
        isExactMatch: Bool,
        similarity: Double
    ) {
        self.id = id
        self.text = text
        self.box = box
        self.confidence = confidence
        self.isExactMatch = isExactMatch
        self.similarity = similarity
    }
}

public enum RecognitionState: String, Equatable, Sendable {
    case pending = "待识别"
    case recognizing = "识别中"
    case matched = "已匹配"
    case fuzzyMatched = "模糊匹配"
    case notFound = "未识别"
    case failed = "识别失败"
}

public struct AlignmentGeometry: Equatable, Sendable {
    public let originX: Double
    public let originY: Double
    public let drawnWidth: Double
    public let drawnHeight: Double
    public let scale: Double

    public init(originX: Double, originY: Double, drawnWidth: Double, drawnHeight: Double, scale: Double) {
        self.originX = originX
        self.originY = originY
        self.drawnWidth = drawnWidth
        self.drawnHeight = drawnHeight
        self.scale = scale
    }
}

public enum AlignmentMath {
    public static func geometry(
        inputWidth: Double,
        inputHeight: Double,
        outputWidth: Double,
        outputHeight: Double,
        selectedBox: NormalizedRect?,
        targetBox: NormalizedRect
    ) -> AlignmentGeometry {
        guard let selectedBox, selectedBox.width > 0 else {
            let scale = min(outputWidth / inputWidth, outputHeight / inputHeight)
            let width = inputWidth * scale
            let height = inputHeight * scale
            return AlignmentGeometry(
                originX: (outputWidth - width) / 2,
                originY: (outputHeight - height) / 2,
                drawnWidth: width,
                drawnHeight: height,
                scale: scale
            )
        }

        let targetWidth = targetBox.width * outputWidth
        let scale = targetWidth / (selectedBox.width * inputWidth)
        let drawnWidth = inputWidth * scale
        let drawnHeight = inputHeight * scale
        let selectedCenterX = selectedBox.centerX * inputWidth * scale
        let selectedCenterY = selectedBox.centerY * inputHeight * scale
        let targetCenterX = targetBox.centerX * outputWidth
        let targetCenterY = targetBox.centerY * outputHeight

        return AlignmentGeometry(
            originX: targetCenterX - selectedCenterX,
            originY: targetCenterY - selectedCenterY,
            drawnWidth: drawnWidth,
            drawnHeight: drawnHeight,
            scale: scale
        )
    }

    public static func transformedBox(
        _ sourceBox: NormalizedRect,
        inputWidth: Double,
        inputHeight: Double,
        outputWidth: Double,
        outputHeight: Double,
        geometry: AlignmentGeometry
    ) -> NormalizedRect {
        NormalizedRect(
            x: (geometry.originX + sourceBox.x * inputWidth * geometry.scale) / outputWidth,
            y: (geometry.originY + sourceBox.y * inputHeight * geometry.scale) / outputHeight,
            width: sourceBox.width * inputWidth * geometry.scale / outputWidth,
            height: sourceBox.height * inputHeight * geometry.scale / outputHeight
        )
    }
}
