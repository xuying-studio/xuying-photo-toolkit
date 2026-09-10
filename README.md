# 旭影工具箱 QML 跨平台版

这是“旭影工具箱”的下一代重构项目。阶段 1–7 的 Mac 工程与候选包已通过本机验收，阶段 8 的 Mac 内部候选版完整性和真实素材回归也已通过；当前以 GitHub Pre-release 形式提供 `v2.0.0-rc.1` 测试包，Developer ID 公证、Windows 实机验收和正式稳定版发布尚未完成。

## 已确定的技术方向

- 共享业务核心：Python 3.12
- 跨平台界面：PySide6 + Qt Quick/QML
- macOS：完整动画、转场和原生磨砂材质
- Windows：保持相同功能与布局，默认减少动画并使用稳定的实体背景
- 当前版本只作为功能基线，不在原目录上直接重写

## 参考基线

- 现有源码：本地只读的 v1.4.0 参考副本（不纳入本仓库）
- GitHub 基线：`xuying-studio/xuying-photo-toolkit`
- 基线版本：`v1.4.0 / build 23`
- 基线提交：`4a287ff57f43b2632861d86607ea0c088793743f`

参考项目在整个重构过程中只允许读取和对照，不允许由本项目 Agent 修改。

## 开始前必须阅读

1. [AGENTS.md](AGENTS.md)
2. [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

## 在新窗口中建议发送的第一句话

> 请完整阅读 AGENTS.md 和 DEVELOPMENT_PLAN.md。先执行阶段 0：只读审计现有 v1.4.0 功能与数据格式，建立功能等价清单和测试迁移清单，不要立刻开发界面。完成审计后向我汇报，等我确认再进入阶段 1。

## 当前状态

- [x] 新项目目录
- [x] 完整开发计划
- [x] Agent 行为约束
- [x] 现有功能基线审计（见 [阶段 0 审计总览](docs/stage0/README.md)）
- [x] 阶段 0 Mac 技术验证与用户确认
- [ ] 阶段 0 Windows OCR/打包实机验证
- [x] 阶段 1 Mac 工程脚手架（见 [阶段 1 验收](docs/stage1/README.md)）
- [ ] 阶段 1 Windows 空壳、测试与试验包实机验收
- [x] 最小 QML Shell 与四个占位页
- [x] 阶段 2 Mac 共享核心迁移（见 [阶段 2 验收](docs/stage2/README.md)）
- [x] 阶段 3 Mac 设计系统与主框架（见 [阶段 3 验收](docs/stage3/README.md)）
- [x] 阶段 4 Mac 时间重命名、配对清理和 XMP 同步（见 [阶段 4 验收](docs/stage4/README.md)）
- [ ] Windows 平台适配与共享核心实机合同
- [x] 阶段 5 Mac 关键词快切与 OCR 接入（见 [阶段 5 Mac 验收](docs/stage5/README.md)）
- [ ] 阶段 5 Windows 离线 OCR、编辑与导出实机验收
- [x] 阶段 6 Mac 原生视觉与动效（见 [阶段 6 Mac 验收](docs/stage6/README.md)）
- [ ] 阶段 6 Windows Reduced Motion、高 DPI 与路径专项验收
- [x] 阶段 7 Mac 数据迁移与 App/ZIP/DMG（见 [阶段 7 Mac 验收](docs/stage7/README.md)）
- [ ] 阶段 7 Windows 安装包、双平台干净环境验收
- [x] 阶段 8 Mac 内部候选版完整性与真实素材回归（见 [阶段 8 Mac 验收](docs/stage8/README.md)）
- [ ] Mac Developer ID 签名与 Apple 公证
- [ ] Windows 正式打包
- [x] v2.0.0-rc.1 GitHub Pre-release
- [ ] v2.0 正式稳定版发布

## Mac 开发启动

```bash
uv sync --locked --group dev
./scripts/run-macos.sh
```

运行测试：

```bash
./scripts/test.sh
```

生成 Mac 内部候选包：

```bash
./scripts/package-macos-release.sh
```

发布产物统一写入项目内的 `artifacts/releases/<版本>/`，不再默认写到桌面。
