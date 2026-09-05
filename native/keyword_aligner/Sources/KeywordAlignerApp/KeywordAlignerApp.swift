import SwiftUI
import KeywordAlignerUI

@main
struct KeywordAlignerApp: App {
    @StateObject private var store = ProjectStore()

    var body: some Scene {
        WindowGroup("关键词对齐器") {
            ContentView(store: store)
                .frame(minWidth: 1080, minHeight: 720)
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unifiedCompact)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("新建项目") {
                    store.resetProject()
                }
                .keyboardShortcut("n", modifiers: .command)
            }
        }
    }
}
