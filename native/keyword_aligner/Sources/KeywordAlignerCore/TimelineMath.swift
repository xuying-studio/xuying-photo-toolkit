import Foundation

/// 计算离散图片时间线的帧数、时长及显示格式。
public struct TimelineMath: Equatable {
    public enum ValidationError: Error, Equatable {
        case imageCountOutOfRange
        case framesPerImageOutOfRange
        case fpsOutOfRange
        case frameCountOverflow
    }

    public let imageCount: Int
    public let framesPerImage: Int
    public let fps: Double

    public init(imageCount: Int, framesPerImage: Int, fps: Double) throws {
        guard imageCount >= 0 else { throw ValidationError.imageCountOutOfRange }
        guard (1...10_000).contains(framesPerImage) else {
            throw ValidationError.framesPerImageOutOfRange
        }
        guard fps.isFinite, (1...120).contains(fps) else {
            throw ValidationError.fpsOutOfRange
        }
        let (_, overflow) = imageCount.multipliedReportingOverflow(by: framesPerImage)
        guard !overflow else { throw ValidationError.frameCountOverflow }
        self.imageCount = imageCount
        self.framesPerImage = framesPerImage
        self.fps = fps
    }

    public var totalFrames: Int { imageCount * framesPerImage }

    public var durationSeconds: Double { Double(totalFrames) / fps }

    /// 返回 HH:MM:SS.mmm，毫秒按四舍五入显示并处理进位。
    public var timecode: String {
        let milliseconds = Int((durationSeconds * 1000).rounded())
        let hours = milliseconds / 3_600_000
        let minutes = (milliseconds % 3_600_000) / 60_000
        let seconds = (milliseconds % 60_000) / 1000
        let millis = milliseconds % 1000
        return String(format: "%02d:%02d:%02d.%03d", hours, minutes, seconds, millis)
    }

    public var summary: String { String(format: "约%.2f秒", durationSeconds) }
}
