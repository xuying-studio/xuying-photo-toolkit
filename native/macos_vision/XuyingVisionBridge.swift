import Darwin
import Foundation
import ImageIO
import Vision

// 该桥只负责 Apple Vision 调用和坐标转换，不承载界面或业务状态。

private struct BridgeRect: Codable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

private struct BridgeObservation: Codable {
    let text: String
    let confidence: Float
    let box: BridgeRect
    let matchBox: BridgeRect?

    enum CodingKeys: String, CodingKey {
        case text, confidence, box
        case matchBox = "match_box"
    }
}

private struct BridgeResponse: Codable {
    let ok: Bool
    let width: Int?
    let height: Int?
    let observations: [BridgeObservation]
    let error: String?
}

private struct IndexedCharacter {
    let normalized: String
    let start: String.Index
    let end: String.Index
}

private func indexedCharacters(_ text: String) -> [IndexedCharacter] {
    var result: [IndexedCharacter] = []
    var index = text.startIndex
    while index < text.endIndex {
        let next = text.index(after: index)
        let character = text[index]
        if character.isLetter || character.isNumber {
            result.append(
                IndexedCharacter(
                    normalized: String(character).lowercased(),
                    start: index,
                    end: next
                )
            )
        }
        index = next
    }
    return result
}

private func exactRange(in text: String, keyword: String) -> Range<String.Index>? {
    let source = indexedCharacters(text)
    let target = indexedCharacters(keyword).map(\.normalized)
    guard !source.isEmpty, !target.isEmpty, target.count <= source.count else { return nil }
    for offset in 0...(source.count - target.count) {
        let window = source[offset..<(offset + target.count)].map(\.normalized)
        if window == target {
            return source[offset].start..<source[offset + target.count - 1].end
        }
    }
    return nil
}

private func topLeftRect(_ rect: CGRect) -> BridgeRect {
    BridgeRect(
        x: rect.minX,
        y: 1 - rect.maxY,
        width: rect.width,
        height: rect.height
    )
}

private func imageSize(_ url: URL) -> (Int, Int)? {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil)
            as? [CFString: Any],
          let width = properties[kCGImagePropertyPixelWidth] as? Int,
          let height = properties[kCGImagePropertyPixelHeight] as? Int else {
        return nil
    }
    return (width, height)
}

private func recognize(path: String, keyword: String) throws -> BridgeResponse {
    let url = URL(fileURLWithPath: path)
    guard FileManager.default.fileExists(atPath: path) else {
        throw NSError(
            domain: "XuyingVisionBridge",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "图片不存在。"]
        )
    }
    guard let (width, height) = imageSize(url) else {
        throw NSError(
            domain: "XuyingVisionBridge",
            code: 2,
            userInfo: [NSLocalizedDescriptionKey: "无法读取图片尺寸。"]
        )
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.minimumTextHeight = 0.008
    try VNImageRequestHandler(url: url, options: [:]).perform([request])

    var observations: [BridgeObservation] = []
    for observation in request.results ?? [] {
        for candidate in observation.topCandidates(3) {
            var matchBox: BridgeRect?
            if let range = exactRange(in: candidate.string, keyword: keyword),
               let rectangle = try? candidate.boundingBox(for: range) {
                matchBox = topLeftRect(rectangle.boundingBox)
            }
            observations.append(
                BridgeObservation(
                    text: candidate.string,
                    confidence: candidate.confidence,
                    box: topLeftRect(observation.boundingBox),
                    matchBox: matchBox
                )
            )
        }
    }
    return BridgeResponse(
        ok: true,
        width: width,
        height: height,
        observations: observations,
        error: nil
    )
}

private func encodedCString(_ response: BridgeResponse) -> UnsafeMutablePointer<CChar>? {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys]
    guard let data = try? encoder.encode(response),
          let json = String(data: data, encoding: .utf8) else { return nil }
    return strdup(json)
}

@_cdecl("XUQuickCutRecognize")
public func quickCutRecognize(
    _ pathPointer: UnsafePointer<CChar>?,
    _ keywordPointer: UnsafePointer<CChar>?
) -> UnsafeMutablePointer<CChar>? {
    guard let pathPointer, let keywordPointer else {
        return encodedCString(
            BridgeResponse(
                ok: false,
                width: nil,
                height: nil,
                observations: [],
                error: "缺少图片路径或关键词。"
            )
        )
    }
    do {
        return encodedCString(
            try recognize(
                path: String(cString: pathPointer),
                keyword: String(cString: keywordPointer)
            )
        )
    } catch {
        return encodedCString(
            BridgeResponse(
                ok: false,
                width: nil,
                height: nil,
                observations: [],
                error: error.localizedDescription
            )
        )
    }
}

@_cdecl("XUQuickCutFreeString")
public func quickCutFreeString(_ pointer: UnsafeMutablePointer<CChar>?) {
    free(pointer)
}
