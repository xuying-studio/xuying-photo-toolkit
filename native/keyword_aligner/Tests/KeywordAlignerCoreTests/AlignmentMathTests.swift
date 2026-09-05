import XCTest
@testable import KeywordAlignerCore

final class AlignmentMathTests: XCTestCase {
    func testMatchedKeywordAlignsToTargetCenterAndWidth() {
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
        let transformed = AlignmentMath.transformedBox(
            source,
            inputWidth: 1080,
            inputHeight: 1920,
            outputWidth: 1080,
            outputHeight: 1920,
            geometry: geometry
        )

        XCTAssertEqual(transformed.centerX, target.centerX, accuracy: 0.000_001)
        XCTAssertEqual(transformed.centerY, target.centerY, accuracy: 0.000_001)
        XCTAssertEqual(transformed.width, target.width, accuracy: 0.000_001)
    }

    func testMissingKeywordUsesAspectFit() {
        let geometry = AlignmentMath.geometry(
            inputWidth: 1000,
            inputHeight: 1000,
            outputWidth: 1080,
            outputHeight: 1920,
            selectedBox: nil,
            targetBox: NormalizedRect(x: 0.25, y: 0.45, width: 0.5, height: 0.08)
        )
        XCTAssertEqual(geometry.drawnWidth, 1080, accuracy: 0.001)
        XCTAssertEqual(geometry.drawnHeight, 1080, accuracy: 0.001)
        XCTAssertEqual(geometry.originY, 420, accuracy: 0.001)
    }
}
