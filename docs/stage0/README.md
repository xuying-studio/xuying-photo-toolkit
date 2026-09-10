# 阶段 0 审计总览

审计日期：2026-09-05

## 结论

阶段 0 已执行到当前 Mac 能验证的边界，但**尚未关闭阶段门禁**。旧版功能与数据格式已经完成只读审计，旧版 Python/Core Swift 测试在仓库外副本中通过，21 张真实截图的 Apple Vision 与 RapidOCR Mac 基线已完成，最小 PySide6/QML 程序、PyInstaller 与 `pyside6-deploy` macOS 包均已实际启动。Windows OCR、Windows 打包，以及发布级 macOS 签名与公证仍需补测。

原跨平台门禁要求这些项目补齐后再整体进入阶段 1；下述“Mac 优先决策”只放行 Mac 工程空壳，Windows 路线和正式业务仍受门禁约束。

## Mac 优先决策

2026-09-05，用户明确确认先做 Mac，并授权在 Mac 阶段 0 已准备好的前提下进入阶段 1。Windows OCR/打包结果继续保留为待补项；该决策只放行 Mac 路线，不代表跨平台阶段 0 已关闭。

## 基线完整性

- 参考仓库：开发者本地只读的 v1.4.0 副本（不纳入本仓库）
- 审计提交：`4a287ff57f43b2632861d86607ea0c088793743f`
- 分支：`codex/xuying-toolbox-v1.4.0`
- 提交与 `origin/main`、`origin/codex/xuying-toolbox-v1.4.0` 一致。
- 参考工作区存在用户的未跟踪文件；审计只读取上述提交的 tracked 文件，没有修改参考目录，也没有在其中生成测试、缓存或构建输出。

## 已完成

- [x] 四个工具与七套皮肤的功能等价矩阵。
- [x] 输入、输出、设置、备份、撤回和快切工程数据 Schema。
- [x] Characterization Test 迁移清单。
- [x] 已建立合成、脱敏 OCR 夹具和两个候选后端的统一计时脚本；当前仅完成 RapidOCR 的 macOS 首轮实测。
- [x] 旧版 Python 测试：`70 passed, 2 skipped`。
- [x] 完整 Xcode 26.6 已可用；仓库外最小 Package 中的 7 个 KeywordAlignerCore 原测试全部通过。
- [x] 用户授权的 21 张真实截图完成哈希/尺寸检查；Apple Vision 与 RapidOCR 均命中 21/21 个“AGI”。
- [x] 最小 PySide6 6.11.2/QML 源程序在 macOS arm64 启动，退出码 0。
- [x] PyInstaller 6.22.2 生成 macOS arm64 App；打包产物实际启动，退出码 0。
- [x] `pyside6-deploy` + Nuitka 4.1.2 生成 macOS arm64 最小验证 App；offscreen 与正常窗口启动退出码均为 0，但深度签名结构校验未通过。
- [x] RapidOCR 3.9.2 在 6 张合成图上的首轮链路实测。
- [x] Windows 一键测试包源码已建立，真实截图和结果目录均受 Git 忽略规则保护。
- [x] 风险登记表。

## 尚未完成

- [ ] 在 Windows 10/11 x64 上运行两种 OCR 后端的同夹具对比。
- [ ] 把 21 张真实截图复制到 Windows，取得两种后端的同机识别、框位置与连续处理耗时。
- [ ] 在 Windows 上验证 QML 源程序、PyInstaller 与 `pyside6-deploy` 产物启动。
- [ ] 发布前修复旧完整 Swift Package 在 Swift 6.3/Vision 新 SDK 下的 UI 编译兼容；Core 原测试已独立通过。
- [ ] 七套皮肤的跨平台截图、对比度、缩放与 Reduced Motion 实机矩阵。

## 建议技术选择

### Windows OCR

建议 v2 第一版以 **RapidOCR + ONNX Runtime** 作为 Windows 默认后端，同时保留 `OCRProvider` 接口，暂不把 `Windows.Media.Ocr` 作为唯一后端。根据当前引用的微软文档，系统 OCR 的桌面发布形态涉及 MSIX 包身份，而当前计划是 Inno Setup 安装版与便携 ZIP；该约束仍需在目标 Windows 版本和最终发布形态中实测确认。系统原生 OCR 还依赖用户已安装对应语言包。

这是一项**有条件的推荐**：RapidOCR 已通过当前合成夹具，但 Windows 与真实截图成绩尚未拿到。若后续改用 MSIX，可重新评估系统原生 OCR。

### 打包工具

根据当前 macOS 实测，建议把 **PyInstaller onedir 作为阶段 1 的候选主路径，`pyside6-deploy` / Nuitka 作为保留验证路径**。两者均能启动，但 PyInstaller 包约 408.73 MiB 且深度签名结构校验通过；Nuitka 包约 422.83 MiB、仍收集未用模块，并在 `Main.qml` 子组件上未通过深度签名校验。

这不是发布级锁定：两个最小包都远超体积目标，且 Windows 结果尚未取得。最终选择仍需用户确认和 Windows 同条件验证。

## 交付物

- [功能等价矩阵](functional-equivalence-matrix.md)
- [数据 Schema](data-schemas.md)
- [Characterization Test 与夹具清单](characterization-tests.md)
- [Windows OCR 对比](windows-ocr-comparison.md)
- [QML 打包验证](packaging-validation.md)
- [风险登记表](risk-register.md)
- [最小 QML 验证程序](../../experiments/stage0_qml_packaging/README.md)
- [OCR 对比实验](../../experiments/stage0_ocr/README.md)
- [Windows 测试包交接](windows-handoff.md)
