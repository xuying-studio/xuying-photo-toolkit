import AppKit
import AVFoundation
import CoreImage
import Foundation
import KeywordAlignerCore

struct ExportItem: Sendable {
    let url: URL
    let selectedBox: NormalizedRect?
}

final class CancellationToken: @unchecked Sendable {
    private let lock = NSLock()
    private var cancelled = false

    func cancel() {
        lock.lock()
        cancelled = true
        lock.unlock()
    }

    var isCancelled: Bool {
        lock.lock()
        defer { lock.unlock() }
        return cancelled
    }
}

enum ExportServiceError: LocalizedError {
    case noItems
    case cannotCreateWriter(String)
    case cannotCreatePixelBuffer
    case writerFailed(String)
    case cancelled

    var errorDescription: String? {
        switch self {
        case .noItems:
            return "没有可导出的图片。"
        case .cannotCreateWriter(let message):
            return "无法创建视频编码器：\(message)"
        case .cannotCreatePixelBuffer:
            return "无法创建视频帧。"
        case .writerFailed(let message):
            return "视频导出失败：\(message)"
        case .cancelled:
            return "操作已取消。"
        }
    }
}

enum ExportService {
    typealias ProgressHandler = @Sendable (_ progress: Double, _ message: String) -> Void

    static func export(
        items: [ExportItem],
        settings: ProjectSettings,
        destination: URL,
        token: CancellationToken,
        progress: @escaping ProgressHandler
    ) async throws -> URL {
        guard !items.isEmpty else { throw ExportServiceError.noItems }
        let outputFolder = try makeOutputFolder(in: destination, keyword: settings.keyword)

        switch settings.exportMode {
        case .alignedPNGs:
            try exportAlignedPNGs(items: items, settings: settings, folder: outputFolder, token: token, progress: progress)
        case .frameSequence:
            try exportFrameSequence(items: items, settings: settings, folder: outputFolder, token: token, progress: progress)
        case .mp4:
            try await exportMP4(items: items, settings: settings, folder: outputFolder, token: token, progress: progress)
        }
        return outputFolder
    }

    private static func makeOutputFolder(in destination: URL, keyword: String) throws -> URL {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        let safeKeyword = sanitizedFileName(keyword.isEmpty ? "关键词" : keyword)
        var folder = destination.appendingPathComponent("\(safeKeyword)-\(formatter.string(from: Date()))", isDirectory: true)
        var suffix = 2
        while FileManager.default.fileExists(atPath: folder.path) {
            folder = destination.appendingPathComponent("\(safeKeyword)-\(formatter.string(from: Date()))-\(suffix)", isDirectory: true)
            suffix += 1
        }
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        return folder
    }

    private static func exportAlignedPNGs(
        items: [ExportItem],
        settings: ProjectSettings,
        folder: URL,
        token: CancellationToken,
        progress: ProgressHandler
    ) throws {
        for (index, item) in items.enumerated() {
            guard !token.isCancelled else { throw ExportServiceError.cancelled }
            let image = try ImageRenderer.render(url: item.url, selectedBox: item.selectedBox, settings: settings)
            let data = try ImageRenderer.pngData(from: image)
            let originalName = item.url.deletingPathExtension().lastPathComponent
            let fileName = String(format: "%03d-%@.png", index + 1, sanitizedFileName(originalName))
            try data.write(to: folder.appendingPathComponent(fileName), options: .atomic)
            progress(Double(index + 1) / Double(items.count), "正在导出 \(index + 1)/\(items.count)")
        }
    }

    private static func exportFrameSequence(
        items: [ExportItem],
        settings: ProjectSettings,
        folder: URL,
        token: CancellationToken,
        progress: ProgressHandler
    ) throws {
        let totalFrames = items.count * settings.framesPerImage
        var frameNumber = 1
        for item in items {
            guard !token.isCancelled else { throw ExportServiceError.cancelled }
            let image = try ImageRenderer.render(url: item.url, selectedBox: item.selectedBox, settings: settings)
            let data = try ImageRenderer.pngData(from: image)
            for _ in 0..<settings.framesPerImage {
                guard !token.isCancelled else { throw ExportServiceError.cancelled }
                let fileName = String(format: "%06d.png", frameNumber)
                try data.write(to: folder.appendingPathComponent(fileName), options: .atomic)
                progress(Double(frameNumber) / Double(totalFrames), "正在导出第 \(frameNumber)/\(totalFrames) 帧")
                frameNumber += 1
            }
        }
    }

    private static func exportMP4(
        items: [ExportItem],
        settings: ProjectSettings,
        folder: URL,
        token: CancellationToken,
        progress: @escaping ProgressHandler
    ) async throws {
        let outputURL = folder.appendingPathComponent("\(sanitizedFileName(settings.keyword))-effect.mp4")
        let writer: AVAssetWriter
        do {
            writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)
        } catch {
            throw ExportServiceError.cannotCreateWriter(error.localizedDescription)
        }

        let compression: [String: Any] = [
            AVVideoAverageBitRateKey: max(2_000_000, Int(Double(settings.width * settings.height) * settings.frameRate * 0.07)),
            AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
            AVVideoAllowFrameReorderingKey: false,
            AVVideoExpectedSourceFrameRateKey: settings.frameRate,
        ]
        let videoSettings: [String: Any] = [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: settings.width,
            AVVideoHeightKey: settings.height,
            AVVideoCompressionPropertiesKey: compression,
        ]
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
        input.expectsMediaDataInRealTime = false
        let frameClock = FrameClock(frameRate: settings.frameRate)
        writer.movieTimeScale = frameClock.timescale
        input.mediaTimeScale = frameClock.timescale
        let attributes: [String: Any] = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
            kCVPixelBufferWidthKey as String: settings.width,
            kCVPixelBufferHeightKey as String: settings.height,
            kCVPixelBufferCGImageCompatibilityKey as String: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
        ]
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: attributes)
        guard writer.canAdd(input) else {
            throw ExportServiceError.cannotCreateWriter("当前编码器不接受所选画面规格")
        }
        writer.add(input)
        guard writer.startWriting() else {
            throw ExportServiceError.writerFailed(writer.error?.localizedDescription ?? "无法开始写入")
        }
        writer.startSession(atSourceTime: .zero)

        let totalFrames = items.count * settings.framesPerImage
        let ciContext = CIContext(options: [.workingColorSpace: CGColorSpace(name: CGColorSpace.sRGB) as Any])
        var frameIndex = 0

        for item in items {
            guard !token.isCancelled else {
                writer.cancelWriting()
                throw ExportServiceError.cancelled
            }
            let image = try ImageRenderer.render(url: item.url, selectedBox: item.selectedBox, settings: settings)
            guard let pixelBuffer = makePixelBuffer(
                image: image,
                width: settings.width,
                height: settings.height,
                pool: adaptor.pixelBufferPool,
                context: ciContext
            ) else {
                writer.cancelWriting()
                throw ExportServiceError.cannotCreatePixelBuffer
            }

            for _ in 0..<settings.framesPerImage {
                guard !token.isCancelled else {
                    writer.cancelWriting()
                    throw ExportServiceError.cancelled
                }
                while !input.isReadyForMoreMediaData {
                    if token.isCancelled {
                        writer.cancelWriting()
                        throw ExportServiceError.cancelled
                    }
                    try await Task.sleep(nanoseconds: 2_000_000)
                }
                let presentationTime = frameClock.time(forFrame: frameIndex)
                guard adaptor.append(pixelBuffer, withPresentationTime: presentationTime) else {
                    writer.cancelWriting()
                    throw ExportServiceError.writerFailed(writer.error?.localizedDescription ?? "第 \(frameIndex + 1) 帧写入失败")
                }
                frameIndex += 1
                progress(Double(frameIndex) / Double(totalFrames), "正在编码第 \(frameIndex)/\(totalFrames) 帧")
            }
        }

        let duration = frameClock.time(forFrame: totalFrames)
        input.markAsFinished()
        writer.endSession(atSourceTime: duration)
        await withCheckedContinuation { continuation in
            writer.finishWriting {
                continuation.resume()
            }
        }
        guard writer.status == .completed else {
            throw ExportServiceError.writerFailed(writer.error?.localizedDescription ?? "未知编码错误")
        }
    }

    private static func makePixelBuffer(
        image: CGImage,
        width: Int,
        height: Int,
        pool: CVPixelBufferPool?,
        context: CIContext
    ) -> CVPixelBuffer? {
        var pixelBuffer: CVPixelBuffer?
        if let pool {
            CVPixelBufferPoolCreatePixelBuffer(nil, pool, &pixelBuffer)
        } else {
            let attributes: [String: Any] = [
                kCVPixelBufferCGImageCompatibilityKey as String: true,
                kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
            ]
            CVPixelBufferCreate(
                nil,
                width,
                height,
                kCVPixelFormatType_32BGRA,
                attributes as CFDictionary,
                &pixelBuffer
            )
        }
        guard let pixelBuffer else { return nil }
        let colorSpace = CGColorSpace(name: CGColorSpace.sRGB)!
        context.render(
            CIImage(cgImage: image),
            to: pixelBuffer,
            bounds: CGRect(x: 0, y: 0, width: width, height: height),
            colorSpace: colorSpace
        )
        return pixelBuffer
    }

    /// 使用有理数时间基，避免 23.976/29.97/59.94fps 被容器粗略取整。
    private struct FrameClock {
        let timescale: CMTimeScale
        let frameValue: Int64

        init(frameRate: Double) {
            let knownRates: [(rate: Double, numerator: Int32, denominator: Int64)] = [
                (23.976, 24_000, 1_001),
                (29.97, 30_000, 1_001),
                (59.94, 60_000, 1_001),
            ]
            if let known = knownRates.first(where: { abs($0.rate - frameRate) < 0.000_5 }) {
                timescale = known.numerator
                frameValue = known.denominator
                return
            }

            let rawNumerator = max(1, Int64((frameRate * 1_000).rounded()))
            let rawDenominator: Int64 = 1_000
            let divisor = Self.greatestCommonDivisor(rawNumerator, rawDenominator)
            timescale = CMTimeScale(rawNumerator / divisor)
            frameValue = rawDenominator / divisor
        }

        func time(forFrame frame: Int) -> CMTime {
            CMTime(value: Int64(frame) * frameValue, timescale: timescale)
        }

        private static func greatestCommonDivisor(_ lhs: Int64, _ rhs: Int64) -> Int64 {
            var a = abs(lhs)
            var b = abs(rhs)
            while b != 0 {
                let remainder = a % b
                a = b
                b = remainder
            }
            return max(a, 1)
        }
    }

    private static func sanitizedFileName(_ value: String) -> String {
        let illegal = CharacterSet(charactersIn: "/\\:?%*|\"<>")
        let components = value.components(separatedBy: illegal)
        let result = components.joined(separator: "-").trimmingCharacters(in: .whitespacesAndNewlines)
        return result.isEmpty ? "关键词" : result
    }
}
