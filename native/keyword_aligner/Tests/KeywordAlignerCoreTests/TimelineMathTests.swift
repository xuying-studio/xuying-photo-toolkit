import XCTest
@testable import KeywordAlignerCore

final class TimelineMathTests: XCTestCase {
    func testDefaultTimeline() throws {
        let timeline = try TimelineMath(imageCount: 26, framesPerImage: 4, fps: 30)
        XCTAssertEqual(timeline.totalFrames, 104)
        XCTAssertEqual(timeline.durationSeconds, 104.0 / 30.0, accuracy: 0.000001)
        XCTAssertEqual(timeline.timecode, "00:00:03.467")
        XCTAssertEqual(timeline.summary, "约3.47秒")
    }

    func testFractionalFPSIsPreserved() throws {
        let timeline = try TimelineMath(imageCount: 10, framesPerImage: 3, fps: 29.97)
        XCTAssertEqual(timeline.fps, 29.97, accuracy: 0.000001)
        XCTAssertEqual(timeline.durationSeconds, 30.0 / 29.97, accuracy: 0.000001)
    }

    func testEmptyImagesHaveZeroDuration() throws {
        let timeline = try TimelineMath(imageCount: 0, framesPerImage: 4, fps: 30)
        XCTAssertEqual(timeline.totalFrames, 0)
        XCTAssertEqual(timeline.durationSeconds, 0)
        XCTAssertEqual(timeline.timecode, "00:00:00.000")
    }

    func testInvalidValuesAreRejected() {
        XCTAssertThrowsError(try TimelineMath(imageCount: 1, framesPerImage: 0, fps: 30))
        XCTAssertThrowsError(try TimelineMath(imageCount: 1, framesPerImage: 10_001, fps: 30))
        XCTAssertThrowsError(try TimelineMath(imageCount: 1, framesPerImage: 4, fps: 0))
        XCTAssertThrowsError(try TimelineMath(imageCount: 1, framesPerImage: 4, fps: 120.01))
        XCTAssertThrowsError(try TimelineMath(imageCount: -1, framesPerImage: 4, fps: 30))
    }

    func testTimecodeCrossesOneHour() throws {
        let timeline = try TimelineMath(imageCount: 90_000, framesPerImage: 1, fps: 25)
        XCTAssertEqual(timeline.timecode, "01:00:00.000")
    }
}
