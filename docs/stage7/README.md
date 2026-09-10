# 阶段 7 · Mac 数据迁移与打包验收

日期：2026-09-06
版本：`2.0.0-rc.1`
目标：macOS 13+ / Apple Silicon arm64

## 结论

**阶段 7 的 Mac 开发部分已完成。** 已实现 v1 → v2 只读设置迁移、安全恢复记录迁移、独立 v2 数据目录、精简 LGPL FFmpeg、第三方许可证、App/ZIP/DMG 构建和最终产物启动验证。

阶段 7 的双平台总门禁尚未完成：Windows x64 安装版/便携版与真实 Windows 干净用户验收仍待后续；本机没有 Developer ID 证书，因此当前 Mac 包是 ad-hoc 签名的内部候选包，不是已公证正式版。

## 数据迁移

| 数据 | 结果 | 安全边界 |
| --- | --- | --- |
| 七套界面皮肤 | 自动迁移到 `application_settings.json` | 旧文件只读，记录来源、旧版本和迁移时间 |
| 关键词快切参数 | 自动迁移到 `quickcut_settings.json` | 新文件写入 Schema 2 和 UserDefaults 来源 |
| 清理恢复记录 | 仅在原文件已离开、每个恢复副本仍存在时复制 | 旧 `cleanup_undo.json` 字节不变 |
| 重命名撤回记录 | 不自动迁移 | 旧记录缺少执行后文件指纹，提示继续用旧版撤回 |
| XMP 撤回记录 | 不自动迁移 | 旧记录缺少执行后文件指纹，提示继续用旧版撤回 |

迁移以 `migration_report.json` 为幂等边界：首次完成后不重复导入，也不删除、覆盖或修改任何 v1 文件。

## 打包与依赖

- App Bundle ID：`com.xuying.toolbox.v2`
- 最低系统：macOS 13.0
- 架构：arm64
- App 体积：约 162 MB
- 内置 FFmpeg：9.0.1，约 2.9 MB
- FFmpeg 许可证：LGPL-2.1-or-later
- FFmpeg 仅启用 PNG、MP4 和 `h264_videotoolbox` 所需能力；网络、GPL、nonfree 和 libx264 均未启用。
- 已检查 295 个 Mach-O 文件，没有 `/opt/homebrew` 或 `/usr/local` 运行依赖。
- App 内和发布目录均附许可证原文；FFmpeg 完整源码、官方签名文件和构建参数随包提供。

## 最终产物

目录：`artifacts/releases/2.0.0-rc.1/macos-arm64/`

| 产物 | 大小 | SHA-256 |
| --- | ---: | --- |
| `Xuying-Toolbox-2.0.0-rc.1-macos-arm64.zip` | 55,527,074 B | `207dfc85452d237393dad0f5e41dcecc4282fb43be781bfe237aa9244692a674` |
| `Xuying-Toolbox-2.0.0-rc.1-macos-arm64.dmg` | 62,347,253 B | `71d8ab15c585754ebbbfadc85020fcfc04515080713ada9fb295b3b498123dd6` |
| `sources/ffmpeg-9.0.1.tar.xz` | 12,036,420 B | `cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635` |

完整逐文件校验见发布目录内的 `SHA256SUMS` 和 `release-manifest.json`。

## 验收记录

| 检查 | 结果 |
| --- | --- |
| 完整 pytest | 146 passed |
| Ruff / Python 编译 / Shell 语法 / diff check | 通过 |
| QML 打包版可见启动 | 通过，四个导航页和迁移状态可访问 |
| App 深度签名完整性 | 通过，ad-hoc |
| Gatekeeper | 未接受；没有 Developer ID 与公证票据，符合当前内部包预期 |
| 隔离 HOME 首次启动 | 通过 |
| 旧皮肤设置迁移且旧文件哈希不变 | 通过 |
| 安全清理恢复记录迁移且旧文件哈希不变 | 通过 |
| 内置 FFmpeg 真实编码两帧 MP4 | 通过 |
| ZIP 完整性 | 通过 |
| DMG 校验、只读挂载并从镜像内启动 | 通过 |
| v1 参考仓库 HEAD | 仍为 `4a287ff57f43b2632861d86607ea0c088793743f` |

## 尚未完成

1. 使用 Developer ID Application 正式签名、Apple 公证并装订 App/DMG。
2. 在另一台全新 macOS 13+ Apple Silicon 设备做完整人工流程。
3. Windows x64 OCR、界面、回收站、安装程序、便携 ZIP、SmartScreen 和干净用户验收。
4. 当前环境没有 GnuPG；FFmpeg 官方 `.asc` 已随包保留，但发布前仍需用官方发布密钥完成 PGP 验签。

因此可以进入阶段 8 的 Mac 候选包人工验收准备，但不能宣称 v2.0 正式发布或跨平台完成。
