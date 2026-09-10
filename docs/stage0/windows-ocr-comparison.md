# Windows OCR 候选对比

状态：**有条件推荐，Windows 实机数据待补齐**。

## 候选结论

v2 第一版建议使用 **RapidOCR 3.9.x + ONNX Runtime** 作为 Windows 默认 OCR 后端，同时保留 `OCRProvider` 接口。暂不采用 `Windows.Media.Ocr` 作为唯一后端：根据当前引用的微软文档，该 WinRT OCR API 在桌面发布形态上涉及 MSIX 包身份，而当前目标是 Inno Setup 安装版与便携 ZIP。包身份要求仍需在目标 Windows 版本和最终发布形态中实测确认。

若未来 Windows 发布形态改为 MSIX，可重新比较系统原生 OCR；当前不能把“系统内置、无需随包模型”当成可直接用于便携版的事实。

## 对比表

| 维度 | Windows.Media.Ocr | RapidOCR + ONNX Runtime |
| --- | --- | --- |
| 离线 | 是 | 是 |
| 中文来源 | 依赖设备安装的中文 OCR 语言包 | wheel 内含默认 PP-OCRv6 small 模型 |
| Python 接入 | 需要社区维护的 PyWinRT 投影或独立原生桥 | 直接 Python API |
| 返回结构 | 行、词、文字和位置 | 文字、四点框、置信度等 |
| 发布兼容 | 当前官方文档描述了桌面应用的 MSIX 包身份要求，仍待目标环境核对 | 目标上可随 Inno Setup 与便携 ZIP 打包，仍需 Windows 实际构建、启动与离线验证 |
| 用户前置条件 | 对应语言包；可能还需包身份 | 无系统语言包要求，但应用体积更大 |
| 模型/运行库体积 | 应用包内可接近 0，系统语言包另计 | 当前环境：RapidOCR 30.89 MiB、ONNX Runtime 74.71 MiB；OpenCV 119.33 MiB，其他依赖另计 |
| 合成夹具准确率 | 待 Windows 实测 | 6/6，规范化字符串相似度 1.0 |
| 初始化耗时 | 待 Windows 实测 | 当前 Mac arm64：1053.34 ms |
| 单图耗时 | 待 Windows 实测 | 当前 Mac arm64：平均 384.72 ms |
| 风险 | MSIX 身份、语言包、PyWinRT 社区维护 | 体积、OpenCV/ONNX 收集、真实截图泛化 |

## 已完成实测

环境：macOS 26.5.2 arm64、Python 3.12.1、RapidOCR 3.9.2、ONNX Runtime 1.29.0。

| 夹具 | 预期 | 识别 | 耗时 |
| --- | --- | --- | ---: |
| `01_chinese.png` | 婚礼跟拍 | 婚礼跟拍 | 440.60 ms |
| `02_chinese_spaces.png` | 新娘 准备 | 新娘 / 准备 | 360.67 ms |
| `03_mixed.png` | Wedding 2026 | Wedding 2026 | 354.43 ms |
| `04_time.png` | 戒指交换 18:30 | 戒指交换 / 18:30 | 421.63 ms |
| `05_low_contrast.png` | 今日关键词 拥抱 | 今日关键词 / 拥抱 | 395.66 ms |
| `06_rotated.png` | 幸福定格 | 幸福定格 | 335.33 ms |

本轮 import 约 567.40 ms，初始化约 1053.34 ms，单图平均约 384.72 ms。该结果只验证链路和基本识别能力，不能代表 Windows 性能，也不能替代真实截图测试。

完整结果：`experiments/stage0_ocr/results/rapidocr-macos-arm64.json`。

## 21 张真实截图的 Mac 基线

用户授权目录中共有 21 张 JPG，全部哈希不同、没有重复图片；`.DS_Store` 已排除。根据图片中反复出现的内容，本次默认关键词推定为 `AGI`，Windows 测试包中可以修改 `keyword.txt`。

| 后端 | 命中图片 | 候选总数 | 平均单图耗时 | 关键词框 |
| --- | ---: | ---: | ---: | --- |
| Apple Vision accurate | 21/21 | 93 | 281.58 ms | Vision 原生子字符串框 |
| RapidOCR 3.9.2 | 21/21 | 100 | 617.67 ms | 整行框按字符比例估算 |

两者都找到全部图片中的 `AGI`。RapidOCR 比 Vision 多找到 7 个精确候选；人工检查两个最大位置差异样本时，RapidOCR 识别到了更靠近画面中心、而 Vision 漏掉的 `AGI`。RapidOCR 的子框是估算值，因此本轮框 IoU 只作提示，不能当成精确几何结论。

汇总结果：`experiments/stage0_ocr/results/real-21-macos-summary.json`。包含完整识别文本的原始 JSON 不进入 Git，只随私有 Windows 测试包交付。

## 仍需在 Windows 执行

1. 安装简体中文 OCR 语言包。
2. 在同一台 Windows 10/11 x64 机器、同一电源策略下分别运行两个脚本。
3. 冷启动至少 5 次，剔除第一次下载/缓存影响后同时保留冷、热数据。
4. 跑私有测试包内的 21 张用户授权真实截图，并与随包 Mac 基线按 SHA-256 对齐。
5. 除文字相似度外，增加候选框 IoU、完全匹配率、漏检率与误选率。
6. 分别在开发环境、Inno Setup 安装版和便携 ZIP 中验证。

## 选择门槛

RapidOCR 满足以下条件才正式锁定：

- 21 张真实截图完全匹配或可接受候选率不低于 macOS Vision 的约定基线。
- 结果能转换为统一 `OCRResult`，框坐标与方向一致。
- 连续 21 张处理时界面可取消、主线程保持响应。
- 打包后模型和运行库完整，离线首次启动不下载文件。
- 最终安装包体积经过用户确认。

## 官方与项目资料

- Microsoft `Windows.Media.Ocr` 命名空间说明：<https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr>
- Microsoft `OcrEngine`：<https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine>
- Microsoft OCR 语言列表：<https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine.availablerecognizerlanguages>
- PyWinRT：<https://github.com/pywinrt/pywinrt>
- RapidOCR 安装与默认模型：<https://github.com/RapidAI/RapidOCRDocs/blob/main/docs/install_usage/rapidocr/install.md>
- RapidOCR 模型列表：<https://github.com/RapidAI/RapidOCRDocs/blob/main/docs/model_list.md>
