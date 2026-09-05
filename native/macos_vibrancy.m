#import <Cocoa/Cocoa.h>
#import <objc/runtime.h>

static const void *XUVibrancyViewKey = &XUVibrancyViewKey;

static NSWindow *XUFindWindow(NSString *targetTitle) {
    for (NSWindow *window in NSApp.windows) {
        if (targetTitle.length > 0 && [window.title isEqualToString:targetTitle]) {
            return window;
        }
    }
    return NSApp.keyWindow ?: NSApp.mainWindow;
}

// 在 Tk 的原生 NSWindow 内容层底部安装系统磨砂材质。
void XUApplyVibrancy(const char *windowTitle, int materialValue) {
    NSString *targetTitle = windowTitle == NULL
        ? @""
        : [NSString stringWithUTF8String:windowTitle];
    void (^applyBlock)(void) = ^{
        NSWindow *window = XUFindWindow(targetTitle);
        NSView *contentView = window.contentView;
        if (window == nil || contentView == nil) {
            return;
        }

        window.opaque = NO;
        window.backgroundColor = NSColor.clearColor;
        window.appearance = [NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];

        NSVisualEffectView *effectView = objc_getAssociatedObject(window, XUVibrancyViewKey);
        if (effectView == nil) {
            NSView *hostView = contentView.superview;
            if (hostView == nil) {
                return;
            }
            effectView = [[NSVisualEffectView alloc] initWithFrame:contentView.frame];
            effectView.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
            effectView.blendingMode = NSVisualEffectBlendingModeBehindWindow;
            effectView.state = NSVisualEffectStateActive;
            [hostView addSubview:effectView positioned:NSWindowBelow relativeTo:contentView];
            objc_setAssociatedObject(
                window,
                XUVibrancyViewKey,
                effectView,
                OBJC_ASSOCIATION_RETAIN_NONATOMIC
            );
        }
        effectView.material = (NSVisualEffectMaterial)materialValue;
        effectView.frame = contentView.frame;
    };

    if (NSThread.isMainThread) {
        applyBlock();
    } else {
        dispatch_async(dispatch_get_main_queue(), applyBlock);
    }
}

// 切回普通皮肤时移除原生材质，并恢复标准窗口背景。
void XURemoveVibrancy(const char *windowTitle) {
    NSString *targetTitle = windowTitle == NULL
        ? @""
        : [NSString stringWithUTF8String:windowTitle];
    void (^removeBlock)(void) = ^{
        NSWindow *window = XUFindWindow(targetTitle);
        if (window == nil) {
            return;
        }
        NSVisualEffectView *effectView = objc_getAssociatedObject(window, XUVibrancyViewKey);
        [effectView removeFromSuperview];
        objc_setAssociatedObject(
            window,
            XUVibrancyViewKey,
            nil,
            OBJC_ASSOCIATION_RETAIN_NONATOMIC
        );
        window.opaque = YES;
        window.backgroundColor = NSColor.windowBackgroundColor;
        window.appearance = nil;
    };

    if (NSThread.isMainThread) {
        removeBlock();
    } else {
        dispatch_async(dispatch_get_main_queue(), removeBlock);
    }
}
