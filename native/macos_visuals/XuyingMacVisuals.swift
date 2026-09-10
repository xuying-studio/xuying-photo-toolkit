import AppKit
import Foundation

// 原生材质层永远不接收鼠标事件，所有交互继续交给 QML。
private final class PassthroughVisualEffectView: NSVisualEffectView {
    override func hitTest(_ point: NSPoint) -> NSView? {
        nil
    }
}

// 找到包含指定视图、且直接属于目标容器的那一层子视图。
private func directChild(of ancestor: NSView, containing descendant: NSView) -> NSView? {
    var current: NSView? = descendant
    while let candidate = current {
        if candidate.superview === ancestor {
            return candidate
        }
        current = candidate.superview
    }
    return nil
}

private final class VisualEffectHandle {
    let view: PassthroughVisualEffectView
    weak var parent: NSView?
    weak var window: NSWindow?
    private var originalStyleMask: NSWindow.StyleMask?
    private var originalTitleVisibility: NSWindow.TitleVisibility?
    private var originalTitlebarAppearsTransparent: Bool?
    private var originalMovableByBackground: Bool?

    init(parent: NSView) {
        self.parent = parent
        window = parent.window
        // Qt 的 QML 内容绘制在 parent 自己的图层中。若把材质作为它的子视图，
        // AppKit 会把子视图合成到 QML 上方；因此必须放到同级并明确置于 Qt 视图下方。
        let host = parent.superview ?? parent
        let frame = parent.superview == nil ? parent.bounds : parent.frame
        view = PassthroughVisualEffectView(frame: frame)
        view.autoresizingMask = [.width, .height]
        view.blendingMode = .behindWindow
        view.material = .hudWindow
        view.state = .active
        host.addSubview(
            view,
            positioned: .below,
            relativeTo: parent.superview == nil ? nil : parent
        )
        parent.window?.isOpaque = false
        parent.window?.backgroundColor = .clear

        // 保留系统红黄绿按钮，让 QML 顶栏延伸到标题栏下方。
        if let window {
            originalStyleMask = window.styleMask
            originalTitleVisibility = window.titleVisibility
            originalTitlebarAppearsTransparent = window.titlebarAppearsTransparent
            originalMovableByBackground = window.isMovableByWindowBackground
            window.styleMask.formUnion([
                .titled,
                .closable,
                .miniaturizable,
                .resizable,
                .fullSizeContentView,
            ])
            window.titleVisibility = .hidden
            window.titlebarAppearsTransparent = true
            window.isMovableByWindowBackground = false
            let trafficLights = [
                window.standardWindowButton(.closeButton),
                window.standardWindowButton(.miniaturizeButton),
                window.standardWindowButton(.zoomButton),
            ]
            trafficLights.forEach { button in
                button?.isHidden = false
                button?.alphaValue = 1
                button?.superview?.isHidden = false
                button?.superview?.alphaValue = 1
                button?.superview?.superview?.isHidden = false
                button?.superview?.superview?.alphaValue = 1
            }
            if let titlebarContainer = trafficLights[0]?.superview?.superview,
               let titlebarHost = titlebarContainer.superview,
               let contentContainer = directChild(of: titlebarHost, containing: parent) {
                // Qt 的全尺寸内容会盖住标题栏容器，将系统按钮恢复到内容上方。
                titlebarHost.addSubview(
                    titlebarContainer,
                    positioned: .above,
                    relativeTo: contentContainer
                )
            }
        }
    }

    var isBehindContent: Bool {
        guard let parent,
              let host = parent.superview,
              view.superview === host,
              let materialIndex = host.subviews.firstIndex(of: view),
              let contentIndex = host.subviews.firstIndex(of: parent)
        else { return false }
        return materialIndex < contentIndex
    }

    var usesIntegratedTitleBar: Bool {
        guard let window else { return false }
        return window.styleMask.contains(.fullSizeContentView)
            && window.titleVisibility == .hidden
            && window.titlebarAppearsTransparent
    }

    var allowsBackgroundWindowDrag: Bool {
        window?.isMovableByWindowBackground ?? false
    }

    func restoreWindowChrome() {
        guard let window else { return }
        if let originalStyleMask {
            window.styleMask = originalStyleMask
        }
        if let originalTitleVisibility {
            window.titleVisibility = originalTitleVisibility
        }
        if let originalTitlebarAppearsTransparent {
            window.titlebarAppearsTransparent = originalTitlebarAppearsTransparent
        }
        if let originalMovableByBackground {
            window.isMovableByWindowBackground = originalMovableByBackground
        }
    }
}

@_cdecl("XUMacVisualsInstall")
public func macVisualsInstall(
    _ parentPointer: UnsafeMutableRawPointer?
) -> UnsafeMutableRawPointer? {
    guard Thread.isMainThread, let parentPointer else { return nil }
    let parent = Unmanaged<NSView>.fromOpaque(parentPointer).takeUnretainedValue()
    let handle = VisualEffectHandle(parent: parent)
    return Unmanaged.passRetained(handle).toOpaque()
}

@_cdecl("XUMacVisualsSetActive")
public func macVisualsSetActive(
    _ handlePointer: UnsafeMutableRawPointer?,
    _ active: Bool
) {
    guard Thread.isMainThread, let handlePointer else { return }
    let handle = Unmanaged<VisualEffectHandle>
        .fromOpaque(handlePointer)
        .takeUnretainedValue()
    handle.view.state = active ? .active : .inactive
}

@_cdecl("XUMacVisualsDestroy")
public func macVisualsDestroy(_ handlePointer: UnsafeMutableRawPointer?) {
    guard Thread.isMainThread, let handlePointer else { return }
    let handle = Unmanaged<VisualEffectHandle>
        .fromOpaque(handlePointer)
        .takeRetainedValue()
    handle.restoreWindowChrome()
    handle.view.removeFromSuperview()
}

@_cdecl("XUMacVisualsPassesHitTest")
public func macVisualsPassesHitTest(
    _ handlePointer: UnsafeMutableRawPointer?
) -> Bool {
    guard Thread.isMainThread, let handlePointer else { return false }
    let handle = Unmanaged<VisualEffectHandle>
        .fromOpaque(handlePointer)
        .takeUnretainedValue()
    return handle.view.hitTest(
        NSPoint(x: handle.view.bounds.midX, y: handle.view.bounds.midY)
    ) == nil
}

@_cdecl("XUMacVisualsIsBehindContent")
public func macVisualsIsBehindContent(
    _ handlePointer: UnsafeMutableRawPointer?
) -> Bool {
    guard Thread.isMainThread, let handlePointer else { return false }
    let handle = Unmanaged<VisualEffectHandle>
        .fromOpaque(handlePointer)
        .takeUnretainedValue()
    return handle.isBehindContent
}

@_cdecl("XUMacVisualsUsesIntegratedTitleBar")
public func macVisualsUsesIntegratedTitleBar(
    _ handlePointer: UnsafeMutableRawPointer?
) -> Bool {
    guard Thread.isMainThread, let handlePointer else { return false }
    let handle = Unmanaged<VisualEffectHandle>
        .fromOpaque(handlePointer)
        .takeUnretainedValue()
    return handle.usesIntegratedTitleBar
}

@_cdecl("XUMacVisualsAllowsBackgroundWindowDrag")
public func macVisualsAllowsBackgroundWindowDrag(
    _ handlePointer: UnsafeMutableRawPointer?
) -> Bool {
    guard Thread.isMainThread, let handlePointer else { return false }
    let handle = Unmanaged<VisualEffectHandle>
        .fromOpaque(handlePointer)
        .takeUnretainedValue()
    return handle.allowsBackgroundWindowDrag
}

@_cdecl("XUMacSystemReduceMotion")
public func macSystemReduceMotion() -> Bool {
    NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
}
