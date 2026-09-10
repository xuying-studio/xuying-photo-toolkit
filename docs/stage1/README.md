# 阶段 1 · Mac 优先验收

日期：2026-09-05

## 状态

**阶段 1 的 Mac 路线已完成，完整跨平台阶段 1 尚未完成。**

用户已确认先推进 Mac，Windows 阶段 0/1 实机验证延期。当前只确认阶段 1 Mac 空壳完成，不自动放行阶段 2 正式业务迁移；进入阶段 2 前仍需用户基于本报告再次确认，并继续保持“先等价测试、后迁移核心”的门禁。

## 已交付

- `pyproject.toml` 与 `uv.lock`。
- `src/xuying_toolbox/` 分层目录。
- 应用入口、QML 资源定位、日志、结构化错误、平台检测。
- macOS Full Motion/native effect 与 Windows Reduced Motion/solid effect 的初始平台策略值。
- pytest、pytest-qt、QML 冒烟与打包输入测试。
- macOS/Windows GitHub Actions 测试矩阵；目前只完成静态校验，未推送运行。
- 最小 QML Shell、四个占位页和可切换侧栏。
- PyInstaller macOS arm64 试验包配置。

阶段 1 没有迁移时间重命名、配对清理、XMP 或关键词快切业务，也没有加入七主题、磨砂或正式动画。

## 本机验证

环境：macOS 26.5.2 arm64、Python 3.12.1、PySide6 6.11.2。

| 验证项 | 结果 |
| --- | --- |
| `uv lock --check` | 通过，21 个锁定包 |
| Python/Ruff | 通过 |
| QML lint | 通过，零警告 |
| pytest | 10 passed |
| 源码正常窗口启动 | 退出码 0 |
| PyInstaller 构建 | 通过 |
| 打包 App 架构 | Mach-O arm64 |
| 包内 offscreen 启动 | 退出码 0 |
| 包内正常窗口启动 | 退出码 0 |
| `codesign --verify --deep --strict` | 退出码 0 |
| ZIP 完整性 | 通过 |
| 解压后 App 启动 | 退出码 0 |
| 解压后签名结构 | 退出码 0 |

## Mac 试验包

- 路径：`~/Desktop/旭影工具箱-2.0.0-alpha.1-stage1-mac-arm64.zip`
- ZIP 大小：146,834,636 bytes，约 140.03 MiB
- 解压后 App：420,224 KiB，约 410.38 MiB
- SHA-256：`cf75e6eadeedf5e1132cc17fc6c889a3d04c71b1ddf48ac29403284fb711ea96`

这是 ad-hoc 的空壳技术包，没有 Developer ID 签名、公证和正式功能，不能发布给普通用户。

## 已知限制

- PyInstaller 仍过量收集 QML/Qt 模块，包体积不合格。
- 构建日志仍提示未使用的 `qmlassetdownloaderprivateplugin` 文件缺失，当前空壳启动不受影响。
- Windows CI 只是配置文件，尚未在 GitHub runner 或实机运行。
- Windows OCR 与打包结果仍待用户返回。
- 当前 QML 只覆盖结构、四个导航项和页面索引切换；键盘焦点、禁用态、鼠标点击、窗口缩放和平台策略实际绑定尚未覆盖。
- 仓库内打包测试只检查输入配置；App 架构、QML 资源、启动与签名证据来自本机验收，CI 尚未复现。
- 七主题、Reduced Motion 联动、原生磨砂和正式页面属于后续阶段。

## 下一阶段边界

用户已于 2026-09-06 确认进入 Mac 阶段 2。共享核心按文件扫描与格式识别 → 时间重命名 → 配对清理 → XMP → 事务/撤回的顺序完成，且未接正式 QML 页面。Windows 阶段 0/1 未验收前，仍不得宣称完整阶段 1 或跨平台完成。
