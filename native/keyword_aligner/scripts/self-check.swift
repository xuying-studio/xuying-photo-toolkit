import Foundation

@main
struct KeywordAlignerSelfCheck {
    static func main() throws {
        let timeline = try TimelineMath(imageCount: 26, framesPerImage: 4, fps: 30)
        precondition(timeline.totalFrames == 104)
        precondition(timeline.timecode == "00:00:03.467")

        let fractional = try TimelineMath(imageCount: 10, framesPerImage: 3, fps: 29.97)
        precondition(abs(fractional.durationSeconds - 30.0 / 29.97) < 0.000_001)

        let source = NormalizedRect(x: 0.4, y: 0.3, width: 0.2, height: 0.05)
        let target = NormalizedRect(x: 0.25, y: 0.45, width: 0.5, height: 0.08)
        let geometry = AlignmentMath.geometry(
            inputWidth: 1080,
            inputHeight: 1920,
            outputWidth: 1080,
            outputHeight: 1920,
            selectedBox: source,
            targetBox: target
        )
        let aligned = AlignmentMath.transformedBox(
            source,
            inputWidth: 1080,
            inputHeight: 1920,
            outputWidth: 1080,
            outputHeight: 1920,
            geometry: geometry
        )
        precondition(abs(aligned.centerX - target.centerX) < 0.000_001)
        precondition(abs(aligned.centerY - target.centerY) < 0.000_001)
        precondition(abs(aligned.width - target.width) < 0.000_001)

        print("SELF-CHECK OK: 104帧，\(timeline.timecode)，关键词位置与宽度对齐")
    }
}
