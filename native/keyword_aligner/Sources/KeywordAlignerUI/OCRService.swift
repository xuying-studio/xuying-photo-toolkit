import Foundation
import Vision
import KeywordAlignerCore

enum OCRServiceError: LocalizedError {
    case cannotReadImage

    var errorDescription: String? {
        switch self {
        case .cannotReadImage:
            return "无法读取图片。"
        }
    }
}

enum OCRService {
    static func recognize(url: URL, keyword: String) throws -> [OCRCandidate] {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        request.recognitionLanguages = ["zh-Hans", "en-US"]
        request.minimumTextHeight = 0.008

        let handler = VNImageRequestHandler(url: url, options: [:])
        try handler.perform([request])
        guard let observations = request.results else { return [] }

        var exact: [OCRCandidate] = []
        var fuzzy: [OCRCandidate] = []
        let normalizedKeyword = normalizedCharacters(keyword)

        for observation in observations {
            for recognized in observation.topCandidates(3) {
                let text = recognized.string

                if let range = normalizedMatchRange(in: text, keyword: keyword),
                   let rectangle = try? recognized.boundingBox(for: range) {
                    exact.append(
                        OCRCandidate(
                            text: String(text[range]),
                            box: topLeftRect(from: rectangle.boundingBox),
                            confidence: recognized.confidence,
                            isExactMatch: true,
                            similarity: 1
                        )
                    )
                    continue
                }

                guard !normalizedKeyword.isEmpty,
                      let fuzzyMatch = bestFuzzyMatch(in: text, keyword: keyword),
                      fuzzyMatch.similarity >= 0.70 else { continue }

                let rectangle = (try? recognized.boundingBox(for: fuzzyMatch.range))?.boundingBox ?? observation.boundingBox
                fuzzy.append(
                    OCRCandidate(
                        text: String(text[fuzzyMatch.range]),
                        box: topLeftRect(from: rectangle),
                        confidence: recognized.confidence,
                        isExactMatch: false,
                        similarity: fuzzyMatch.similarity
                    )
                )
            }
        }

        if !exact.isEmpty {
            return deduplicated(exact).sorted { centerDistance($0.box) < centerDistance($1.box) }
        }

        return deduplicated(fuzzy).sorted {
            if abs($0.similarity - $1.similarity) > 0.001 {
                return $0.similarity > $1.similarity
            }
            return centerDistance($0.box) < centerDistance($1.box)
        }
    }

    private static func deduplicated(_ candidates: [OCRCandidate]) -> [OCRCandidate] {
        var seen = Set<String>()
        return candidates.filter { candidate in
            let key = String(
                format: "%.3f|%.3f|%.3f|%.3f|%@",
                candidate.box.x,
                candidate.box.y,
                candidate.box.width,
                candidate.box.height,
                candidate.text
            )
            return seen.insert(key).inserted
        }
    }

    private static func topLeftRect(from visionRect: CGRect) -> NormalizedRect {
        NormalizedRect(
            x: visionRect.minX,
            y: 1 - visionRect.maxY,
            width: visionRect.width,
            height: visionRect.height
        ).clamped()
    }

    private static func centerDistance(_ rect: NormalizedRect) -> Double {
        hypot(rect.centerX - 0.5, rect.centerY - 0.5)
    }

    private struct IndexedCharacter {
        let character: Character
        let lowerBound: String.Index
        let upperBound: String.Index
    }

    private static func indexedCharacters(_ text: String) -> [IndexedCharacter] {
        var result: [IndexedCharacter] = []
        var index = text.startIndex
        while index < text.endIndex {
            let next = text.index(after: index)
            let character = text[index]
            if character.unicodeScalars.contains(where: { CharacterSet.alphanumerics.contains($0) }) {
                let lowered = String(character).lowercased()
                for loweredCharacter in lowered {
                    result.append(IndexedCharacter(character: loweredCharacter, lowerBound: index, upperBound: next))
                }
            }
            index = next
        }
        return result
    }

    private static func normalizedCharacters(_ text: String) -> [Character] {
        indexedCharacters(text).map(\.character)
    }

    private static func normalizedMatchRange(in text: String, keyword: String) -> Range<String.Index>? {
        let source = indexedCharacters(text)
        let target = normalizedCharacters(keyword)
        guard !source.isEmpty, !target.isEmpty, source.count >= target.count else { return nil }

        for start in 0...(source.count - target.count) {
            let slice = source[start..<(start + target.count)].map(\.character)
            if slice == target {
                return source[start].lowerBound..<source[start + target.count - 1].upperBound
            }
        }
        return nil
    }

    private static func bestFuzzyMatch(in text: String, keyword: String) -> (range: Range<String.Index>, similarity: Double)? {
        let source = indexedCharacters(text)
        let target = normalizedCharacters(keyword)
        guard !source.isEmpty, !target.isEmpty else { return nil }

        var best: (range: Range<String.Index>, similarity: Double)?
        let minimumLength = max(1, target.count - 2)
        let maximumLength = min(source.count, target.count + 2)
        guard minimumLength <= maximumLength else { return nil }

        for length in minimumLength...maximumLength {
            guard source.count >= length else { continue }
            for start in 0...(source.count - length) {
                let candidate = Array(source[start..<(start + length)].map(\.character))
                let distance = levenshtein(candidate, target)
                let similarity = 1 - Double(distance) / Double(max(candidate.count, target.count))
                if best == nil || similarity > best!.similarity {
                    best = (
                        source[start].lowerBound..<source[start + length - 1].upperBound,
                        similarity
                    )
                }
            }
        }
        return best
    }

    private static func levenshtein(_ lhs: [Character], _ rhs: [Character]) -> Int {
        if lhs.isEmpty { return rhs.count }
        if rhs.isEmpty { return lhs.count }

        var previous = Array(0...rhs.count)
        for (leftIndex, leftCharacter) in lhs.enumerated() {
            var current = Array(repeating: 0, count: rhs.count + 1)
            current[0] = leftIndex + 1
            for (rightIndex, rightCharacter) in rhs.enumerated() {
                current[rightIndex + 1] = min(
                    current[rightIndex] + 1,
                    previous[rightIndex + 1] + 1,
                    previous[rightIndex] + (leftCharacter == rightCharacter ? 0 : 1)
                )
            }
            previous = current
        }
        return previous[rhs.count]
    }
}
