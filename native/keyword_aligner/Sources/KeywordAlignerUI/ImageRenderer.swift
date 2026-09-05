import AppKit
import Foundation
import KeywordAlignerCore

enum ImageRendererError: LocalizedError {
    case cannotReadImage(URL)
    case cannotCreateBitmap
    case cannotEncodePNG

    var errorDescription: String? {
        switch self {
        case .cannotReadImage(let url):
            return "无法读取图片：\(url.lastPathComponent)"
        case .cannotCreateBitmap:
            return "无法创建输出画布。"
        case .cannotEncodePNG:
            return "无法编码 PNG。"
        }
    }
}

enum ImageRenderer {
    static func loadImage(_ url: URL) throws -> NSImage {
        guard let image = NSImage(contentsOf: url), image.isValid else {
            throw ImageRendererError.cannotReadImage(url)
        }
        return image
    }

    static func pixelSize(of image: NSImage) -> CGSize {
        if let representation = image.representations.max(by: {
            ($0.pixelsWide * $0.pixelsHigh) < ($1.pixelsWide * $1.pixelsHigh)
        }), representation.pixelsWide > 0, representation.pixelsHigh > 0 {
            return CGSize(width: representation.pixelsWide, height: representation.pixelsHigh)
        }
        return image.size
    }

    static func render(
        url: URL,
        selectedBox: NormalizedRect?,
        settings: ProjectSettings
    ) throws -> CGImage {
        let image = try loadImage(url)
        let inputSize = pixelSize(of: image)
        let outputWidth = settings.width
        let outputHeight = settings.height
        guard outputWidth > 0, outputHeight > 0,
              let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
              let bitmapContext = CGContext(
                data: nil,
                width: outputWidth,
                height: outputHeight,
                bitsPerComponent: 8,
                bytesPerRow: 0,
                space: colorSpace,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
              ) else {
            throw ImageRendererError.cannotCreateBitmap
        }
        let graphicsContext = NSGraphicsContext(cgContext: bitmapContext, flipped: false)

        let geometry = AlignmentMath.geometry(
            inputWidth: inputSize.width,
            inputHeight: inputSize.height,
            outputWidth: Double(outputWidth),
            outputHeight: Double(outputHeight),
            selectedBox: selectedBox,
            targetBox: settings.targetRect
        )

        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = graphicsContext
        graphicsContext.imageInterpolation = NSImageInterpolation.high
        bitmapContext.setFillColor(NSColor.white.cgColor)
        bitmapContext.fill(CGRect(x: 0, y: 0, width: outputWidth, height: outputHeight))

        // 几何计算使用左上角坐标，这里换算成 AppKit 的左下角坐标。
        let drawRect = NSRect(
            x: geometry.originX,
            y: Double(outputHeight) - geometry.originY - geometry.drawnHeight,
            width: geometry.drawnWidth,
            height: geometry.drawnHeight
        )
        image.draw(
            in: drawRect,
            from: .zero,
            operation: .sourceOver,
            fraction: 1,
            respectFlipped: true,
            hints: [.interpolation: NSImageInterpolation.high]
        )
        graphicsContext.flushGraphics()
        NSGraphicsContext.restoreGraphicsState()

        guard let output = bitmapContext.makeImage() else {
            throw ImageRendererError.cannotCreateBitmap
        }
        return output
    }

    static func pngData(from image: CGImage) throws -> Data {
        let representation = NSBitmapImageRep(cgImage: image)
        guard let data = representation.representation(using: .png, properties: [:]) else {
            throw ImageRendererError.cannotEncodePNG
        }
        return data
    }
}
