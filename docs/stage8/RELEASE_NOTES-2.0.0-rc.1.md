# 旭影工具箱 2.0.0-rc.1 候选版说明

## 当前定位

这是面向 macOS 13+ Apple Silicon 的 GitHub 预发布测试候选版，用于完成最后的实机验收。当前未用 Developer ID 正式签名、未完成 Apple 公证，不建议作为正式稳定版分发。

## 主要更新

- 使用 PySide6 + Qt Quick/QML 重建主界面，共享 Python 业务核心。
- 完成时间重命名、RAW/JPG 配对清理与恢复、Adobe XMP 双向同步与撤回。
- 完成关键词快切：Apple Vision 离线 OCR、候选框选择、目标位置和 PNG/逐帧 PNG/无声 MP4 导出。
- 完成七套皮肤、macOS 原生磨砂背景、页面转场和减少动效支持。
- 统一主次按钮、导航、空状态、进度、弹层和提示反馈的视觉层级，提升整体产品质感。
- 首次启动可以只读迁移旧版设置与安全的清理恢复记录，不改动旧版数据。
- 提供 arm64 App、ZIP 和 DMG，内置精简 LGPL FFmpeg，附第三方许可证、源码和 SHA-256 清单。

## 已验证

- 四个核心工作流均使用真实素材副本执行，重命名、清理和 XMP 撤回/恢复通过。
- Apple Vision 在 2 张真实截图中均精确命中 `AGI`。
- 处理后 PNG、连续 PNG 帧和 4 帧无声 MP4 均实际生成并通过检查。
- 候选包的 DMG、ZIP 和 FFmpeg 源码包与发布清单的大小、SHA-256 一致。

## 已知限制

- 当前 Mac 包仅为 ad-hoc 签名，没有 Apple 公证票据，Gatekeeper 不会直接接受。
- Windows x64 OCR、回收站、界面、安装包和便携包尚未完成真机验收。
- 自动更新、云端 OCR、账号与网络同步不在 2.0 范围内。

## 候选产物

- `Xuying-Toolbox-2.0.0-rc.1-macos-arm64.dmg`
- `Xuying-Toolbox-2.0.0-rc.1-macos-arm64.zip`
- `SHA256SUMS`
- `release-manifest.json`
- `licenses/`
- `sources/`

此版本按 GitHub Pre-release 发布；在 Developer ID 公证和 Windows 实机门禁关闭前，不标记为正式稳定版。
