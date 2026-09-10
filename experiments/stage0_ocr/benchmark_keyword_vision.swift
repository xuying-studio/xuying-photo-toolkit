import CryptoKit
import Foundation
import ImageIO
import Vision

// 在真实截图目录上记录与 v1.4.0 参数一致的 Apple Vision 关键词检测结果。

func centerDistance(_ box: CGRect) -> Double {
    let centerX = box.minX + box.width / 2
    let centerY = 1 - box.maxY + box.height / 2
    return hypot(centerX - 0.5, centerY - 0.5)
}

func imageSize(_ url: URL) -> (Int, Int)? {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
          let width = properties[kCGImagePropertyPixelWidth] as? Int,
          let height = properties[kCGImagePropertyPixelHeight] as? Int else {
        return nil
    }
    return (width, height)
}

func sha256(_ url: URL) throws -> String {
    let data = try Data(contentsOf: url)
    return SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

func topLeftBox(_ box: CGRect) -> [String: Double] {
    [
        "x": box.minX,
        "y": 1 - box.maxY,
        "width": box.width,
        "height": box.height,
    ]
}

let arguments = CommandLine.arguments
guard arguments.count >= 3 else {
    FileHandle.standardError.write(Data("用法：swift benchmark_keyword_vision.swift <图片目录> <关键词> [输出 JSON]\n".utf8))
    exit(2)
}

let inputDirectory = URL(fileURLWithPath: arguments[1], isDirectory: true)
let keyword = arguments[2]
let outputURL = arguments.count >= 4 ? URL(fileURLWithPath: arguments[3]) : nil
let allowedExtensions = Set(["jpg", "jpeg", "png", "heic"])
let files = try FileManager.default.contentsOfDirectory(
    at: inputDirectory,
    includingPropertiesForKeys: [.isRegularFileKey],
    options: [.skipsHiddenFiles]
).filter { allowedExtensions.contains($0.pathExtension.lowercased()) }
 .sorted { $0.lastPathComponent < $1.lastPathComponent }

var cases: [[String: Any]] = []
var elapsedValues: [Double] = []

for file in files {
    guard let (width, height) = imageSize(file) else { continue }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.minimumTextHeight = 0.008

    let started = CFAbsoluteTimeGetCurrent()
    let handler = VNImageRequestHandler(url: file, options: [:])
    try handler.perform([request])
    let elapsedMS = (CFAbsoluteTimeGetCurrent() - started) * 1000
    elapsedValues.append(elapsedMS)

    var lines: [[String: Any]] = []
    var candidates: [[String: Any]] = []
    for observation in request.results ?? [] {
        for recognized in observation.topCandidates(3) {
            let text = recognized.string
            lines.append([
                "text": text,
                "confidence": recognized.confidence,
                "box": topLeftBox(observation.boundingBox),
            ])
            guard let range = text.range(of: keyword, options: [.caseInsensitive]),
                  let rectangle = try? recognized.boundingBox(for: range) else { continue }
            let box = rectangle.boundingBox
            candidates.append([
                "text": String(text[range]),
                "source_text": text,
                "confidence": recognized.confidence,
                "box": topLeftBox(box),
                "box_method": "vision-substring-box",
                "center_distance": centerDistance(box),
            ])
        }
    }
    candidates.sort {
        ($0["center_distance"] as? Double ?? .infinity) <
        ($1["center_distance"] as? Double ?? .infinity)
    }
    cases.append([
        "file": file.lastPathComponent,
        "sha256": try sha256(file),
        "width": width,
        "height": height,
        "elapsed_ms": elapsedMS,
        "keyword_found": !candidates.isEmpty,
        "selected_candidate": candidates.first as Any,
        "candidates": candidates,
        "recognized_lines": lines,
    ])
}

let average: Any
if elapsedValues.isEmpty {
    average = NSNull()
} else {
    average = elapsedValues.reduce(0.0) { partial, value in partial + value } /
        Double(elapsedValues.count)
}
let report: [String: Any] = [
    "engine": "Apple Vision",
    "scope": "user-authorized-real-screenshots",
    "platform": ProcessInfo.processInfo.operatingSystemVersionString,
    "keyword": keyword,
    "coordinate_convention": "top-left normalized",
    "source_count": cases.count,
    "found_count": cases.filter { $0["keyword_found"] as? Bool == true }.count,
    "average_image_ms": average,
    "cases": cases,
]

let data = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
if let outputURL {
    try FileManager.default.createDirectory(
        at: outputURL.deletingLastPathComponent(),
        withIntermediateDirectories: true
    )
    try data.write(to: outputURL, options: .atomic)
} else {
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data("\n".utf8))
}
