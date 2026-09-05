import AppKit
import SwiftUI
import KeywordAlignerUI

/// 给 Tk/PyObjC 使用的原生视图容器。
@MainActor
final class KeywordAlignerHost {
    let store: ProjectStore
    let hostingView: NSHostingView<ContentView>

    init() {
        store = ProjectStore()
        hostingView = NSHostingView(rootView: ContentView(store: store))
        hostingView.autoresizingMask = [.width, .height]
    }

    func setFrameFromTk(_ frame: CGRect) {
        let height = hostingView.superview?.bounds.height ?? 0
        hostingView.frame = CGRect(x: frame.minX, y: height - frame.minY - frame.height, width: frame.width, height: frame.height)
    }
    func setVisible(_ visible: Bool) { hostingView.isHidden = !visible }
    func cancel() { store.cancelCurrentOperation() }
    func setTheme(_ id: String) {
        AppPalette.setTheme(id)
        store.objectWillChange.send()
    }
}

private func onMain(_ action: @escaping @MainActor () -> Void) {
    if Thread.isMainThread { Task { @MainActor in action() } }
    else { DispatchQueue.main.async { Task { @MainActor in action() } } }
}

private func syncMain<T>(_ action: @escaping @MainActor () -> T) -> T {
    if Thread.isMainThread { return unsafeBitCast(action, to: (() -> T).self)() }
    return DispatchQueue.main.sync { unsafeBitCast(action, to: (() -> T).self)() }
}

@_cdecl("XUKeywordAlignerCreate")
@MainActor
public func XUKeywordAlignerCreate(_ windowTitle: UnsafePointer<CChar>?, _ x: Double, _ y: Double, _ width: Double, _ height: Double) -> UnsafeMutableRawPointer? {
    var result: UnsafeMutableRawPointer?
    let create: @MainActor () -> Void = {
        guard let titlePointer = windowTitle,
              let title = String(validatingUTF8: titlePointer),
              let window = NSApp?.windows.first(where: { $0.title == title }),
              let contentView = window.contentView else { return }
        let host = KeywordAlignerHost()
        contentView.addSubview(host.hostingView)
        let appKitY = contentView.bounds.height - y - height
        host.hostingView.frame = CGRect(x: x, y: appKitY, width: width, height: height)
        result = Unmanaged.passRetained(host).toOpaque()
    }
    if Thread.isMainThread { create() } else { DispatchQueue.main.sync(execute: create) }
    return result
}

@_cdecl("XUKeywordAlignerSetFrame")
public func XUKeywordAlignerSetFrame(_ handle: UnsafeMutableRawPointer?, _ x: Double, _ y: Double, _ width: Double, _ height: Double) {
    guard let handle else { return }
    syncMain { Unmanaged<KeywordAlignerHost>.fromOpaque(handle).takeUnretainedValue().setFrameFromTk(CGRect(x: x, y: y, width: width, height: height)) }
}

@_cdecl("XUKeywordAlignerSetVisible")
public func XUKeywordAlignerSetVisible(_ handle: UnsafeMutableRawPointer?, _ visible: Int32) {
    guard let handle else { return }
    syncMain { Unmanaged<KeywordAlignerHost>.fromOpaque(handle).takeUnretainedValue().setVisible(visible != 0) }
}

@_cdecl("XUKeywordAlignerIsBusy")
public func XUKeywordAlignerIsBusy(_ handle: UnsafeMutableRawPointer?) -> Int32 {
    guard let handle else { return 0 }
    return syncMain { Unmanaged<KeywordAlignerHost>.fromOpaque(handle).takeUnretainedValue().store.isBusy ? 1 : 0 }
}

@_cdecl("XUKeywordAlignerCancel")
public func XUKeywordAlignerCancel(_ handle: UnsafeMutableRawPointer?) {
    guard let handle else { return }
    syncMain { Unmanaged<KeywordAlignerHost>.fromOpaque(handle).takeUnretainedValue().cancel() }
}

@_cdecl("XUKeywordAlignerSetTheme")
public func XUKeywordAlignerSetTheme(_ handle: UnsafeMutableRawPointer?, _ themeID: UnsafePointer<CChar>?) {
    guard let handle, let themeID, let value = String(validatingUTF8: themeID) else { return }
    syncMain { Unmanaged<KeywordAlignerHost>.fromOpaque(handle).takeUnretainedValue().setTheme(value) }
}

@_cdecl("XUKeywordAlignerDestroy")
public func XUKeywordAlignerDestroy(_ handle: UnsafeMutableRawPointer?) {
    guard let handle else { return }
    syncMain { Unmanaged<KeywordAlignerHost>.fromOpaque(handle).takeUnretainedValue().hostingView.removeFromSuperview() }
    syncMain { Unmanaged<KeywordAlignerHost>.fromOpaque(handle).release() }
}
