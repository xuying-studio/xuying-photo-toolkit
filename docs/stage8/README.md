# 阶段 8 · Mac 发布候选版验收

日期：2026-09-06
版本：`2.0.0-rc.1`
目标：macOS 13+ / Apple Silicon arm64

## 结论

**阶段 8 中不依赖开发者证书的 Mac 验收已完成。** 候选 App、ZIP、DMG 和 FFmpeg 源码包的大小与 SHA-256 均一致；四个核心工作流已用真实素材副本回归通过。

当前状态是 **Mac GitHub Pre-release 候选包**，不是已公证正式版。本机没有 Developer ID Application 证书，候选包是 ad-hoc 签名，Gatekeeper 不会接受；Windows 实机与发布包也未完成。用户已明确授权发布 `v2.0.0-rc.1` 预发布版，但这些未关闭门禁仍阻止创建 `2.0.0` 正式稳定版。

## 真实素材工作流

测试程序只读原始素材，操作全部发生在项目 `build/stage8-macos-rc/` 中的实体副本上。测试前后对所用原文件做 SHA-256 比对，结果一致。

| 工作流 | 真实执行 | 结果 |
| --- | --- | --- |
| 时间重命名 | 1 组 RAW/JPG，扫描 → 执行 → 撤回 | 2 条操作，文件名和内容完整恢复 |
| 配对清理 | 1 组配对 + 1 张孤立 JPG，扫描 → 模拟废纸篓 → 恢复 | 只命中孤立 JPG，恢复后内容一致 |
| XMP 同步 | 真实 JPG 写入 5 星/`Select`，JPG → RAW → 撤回 | RAW 本体字节未改，侧车创建后可完整撤回 |
| 关键词快切 | 2 张真实截图，候选 App 内 Vision OCR + FFmpeg | `AGI` 2/2 精确命中；2 张 PNG、4 张帧、4 帧无声 MP4 导出通过 |

完整机器可读结果见 [macos-validation-report.json](macos-validation-report.json)。验证器见 [`scripts/validate-macos-rc-workflows.py`](../../scripts/validate-macos-rc-workflows.py)。

## 候选包门禁

| 检查 | 结果 |
| --- | --- |
| App 显示名 / Bundle ID / arm64 / macOS 13 | 通过 |
| `2.0.0rc1` / `2.0.0-rc.1` / App `2.0.0 (1)` 版本策略 | 通过 |
| App 代码结构签名完整性 | 通过，ad-hoc |
| DMG / ZIP / FFmpeg 源码包大小、manifest 和 `SHA256SUMS` | 通过 |
| Developer ID Application | 未通过，本机无有效身份 |
| Apple 公证与 staple | 未通过 |
| Gatekeeper | 未通过，符合 ad-hoc 内部包预期 |
| 干净发布提交与 `v2.0.0-rc.1` tag | 本次预发布流程创建并核验 |
| GitHub Release 资产与直连下载 | 本次以 Pre-release 创建并核验 |
| Windows x64 产物与实机 | 未完成 |

## 版本表达策略

- Python 包使用 PEP 440：`2.0.0rc1`。
- 候选包文件名、文档和应用内显示使用：`2.0.0-rc.1`。
- macOS `CFBundleShortVersionString` 只放三段数字：`2.0.0`；`CFBundleVersion` 使用：`1`。

这三种写法不是版本冲突，而是 Python、产物名和 macOS Bundle 的格式差异。

## 可重复执行

```bash
uv run python scripts/validate-macos-rc-workflows.py \
  --photo-fixtures "/path/to/photo-fixtures" \
  --quickcut-fixtures "/path/to/quickcut-fixtures"
```

执行会重建项目内的 `build/stage8-macos-rc/`，不会写入传入的原始素材目录。

## 正式发布前剩余项

1. 获得 Developer ID Application 证书后重新签名 App 和 DMG，开启 hardened runtime 和 timestamp。
2. 提交 Apple notarization，对 App/DMG 装订票据，重新验证 Gatekeeper。
3. 在另一台干净 macOS 13+ Apple Silicon 机器上完成首次启动、迁移和四工具人工验收。
4. 完成 Windows x64 包和真机验收。
5. 用官方发布密钥完成 FFmpeg `.asc` PGP 验签。
6. 后续候选版继续执行隐私扫描、完整测试、产物校验与 GitHub 下载验证。
