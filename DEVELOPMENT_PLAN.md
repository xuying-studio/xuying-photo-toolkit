# 旭影工具箱 QML 跨平台版完整开发计划

## 1. 项目目标

在不修改现有 v1.4.0 项目的前提下，使用 Python 共享业务核心与 PySide6/Qt Quick QML 重新开发“旭影工具箱”。

目标不是简单换一层皮肤，而是建立可长期扩展的跨平台架构：

- macOS 版本提供接近现代原生应用的材质、动画、手势和转场。
- Windows 版本使用相同功能和布局，减少高成本动画与透明效果。
- 四个现有工具、七套皮肤和全部文件安全机制保持功能等价。
- 后续独立开发的新功能可以作为模块直接加入工具箱。

## 2. 项目边界

### 必须完成

1. 时间重命名。
2. RAW/JPG 配对清理与恢复。
3. Adobe XMP 星标和颜色标签双向同步。
4. 关键词 OCR 对齐与 PNG/逐帧 PNG/MP4 导出。
5. 七套皮肤。
6. macOS 与 Windows 安装包。
7. 旧配置、撤回记录和数据格式迁移。
8. 自动测试、实机验收和发布文档。

### 第一阶段不新增

- 云端 OCR、账号系统或网络同步。
- 移动端、网页端或 Linux 正式版。
- AI 自动修图、照片管理数据库或图库功能。
- Intel Mac 正式支持。
- 自动更新器。

在功能等价版本完成前，不接受与现有四个工具无关的大功能扩展。

## 3. 技术选型

| 领域 | 选型 | 说明 |
| --- | --- | --- |
| 语言 | Python 3.12 | 共享核心、平台适配和 ViewModel |
| GUI | PySide6 | Qt 官方 Python 绑定 |
| 界面 | Qt Quick/QML | 动画、状态、布局与 GPU 渲染 |
| 包管理 | `pyproject.toml` + `uv` | 锁定依赖，提升 macOS/Windows 一致性 |
| 测试 | pytest + pytest-qt + Qt Test | 核心、ViewModel 和 QML 测试 |
| 列表模型 | QAbstractListModel | 支持大批量照片列表虚拟化 |
| 后台任务 | QThreadPool/QRunnable | 防止扫描、OCR 和导出阻塞界面 |
| 图片处理 | Pillow + 平台解码适配 | 保留方向、色彩空间和尺寸信息 |
| 视频导出 | FFmpeg Adapter | 两个平台输出一致的无声 MP4 |
| macOS OCR | Apple Vision Service Bridge | 复用系统离线 OCR 能力 |
| Windows OCR | 方案验证后锁定 | 优先比较 Windows.Media.Ocr 与 RapidOCR/ONNX |
| macOS 材质 | NSVisualEffectView Bridge | 位于 QQuickWindow 背后，不侵入业务层 |
| 打包 | pyside6-deploy/Nuitka | QML 与 Qt 插件统一收集；阶段 0 做打包验证 |
| Windows 安装 | Inno Setup | 保留安装版和便携版 |

### 需要在阶段 0 锁定的两项技术决策

1. Windows OCR：用同一组中文截图比较识别率、中文模型体积、启动速度和离线可用性。
2. 打包工具：用最小 QML 程序分别验证 `pyside6-deploy` 和当前 PyInstaller 流程，默认优先 Qt 官方部署方式。

未经验证，不在业务代码中绑定具体 OCR 或打包实现。

## 4. 目标目录结构

```text
旭影工具箱-QML跨平台版/
├── AGENTS.md
├── DEVELOPMENT_PLAN.md
├── README.md
├── pyproject.toml
├── uv.lock
├── src/
│   └── xuying_toolbox/
│       ├── domain/
│       │   ├── models/
│       │   ├── services/
│       │   ├── ports/
│       │   └── errors.py
│       ├── application/
│       │   ├── rename/
│       │   ├── cleanup/
│       │   ├── xmp_sync/
│       │   ├── quickcut/
│       │   └── tasking/
│       ├── infrastructure/
│       │   ├── filesystem/
│       │   ├── metadata/
│       │   ├── imaging/
│       │   ├── ocr/
│       │   ├── video/
│       │   └── persistence/
│       ├── platform/
│       │   ├── macos/
│       │   ├── windows/
│       │   └── detection.py
│       ├── presentation/
│       │   ├── models/
│       │   ├── viewmodels/
│       │   └── qml_registry.py
│       ├── bootstrap.py
│       └── __main__.py
├── qml/
│   ├── App.qml
│   ├── Shell/
│   ├── Components/
│   ├── Pages/
│   │   ├── RenamePage.qml
│   │   ├── CleanupPage.qml
│   │   ├── XmpSyncPage.qml
│   │   └── QuickCutPage.qml
│   ├── Dialogs/
│   ├── Themes/
│   ├── Motion/
│   └── Assets/
├── native/
│   ├── macos/
│   │   ├── vision_ocr/
│   │   └── visual_effect/
│   └── windows/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── qml/
│   ├── packaging/
│   └── fixtures/
├── packaging/
│   ├── macos/
│   └── windows/
├── scripts/
└── docs/
```

## 5. 核心架构

### 5.1 Domain

纯 Python 业务规则，不依赖 Qt 和平台实现。包含：

- 图片、侧车、配对、XMP 属性等实体。
- 重命名计划、冲突检测和两阶段事务。
- 清理计划和恢复记录结构。
- XMP 解析、写入计划、备份与回滚规则。
- OCRCandidate、NormalizedRect、AlignmentGeometry、Timeline 等关键词模型。
- 文件名、扩展名大小写和同目录配对规则。

### 5.2 Application

每项功能通过 Use Case 对外提供：

- `scan()`：只读扫描并返回预览。
- `execute()`：确认后执行事务。
- `undo()`：撤回最近一次操作。
- `cancel()`：请求取消。
- `progress`：统一的完成数、总数、阶段和消息。

用例只依赖 Port，不知道具体平台和 QML 控件。

### 5.3 Infrastructure 与 Platform Adapter

通过 Protocol 定义：

- `MetadataReader`
- `TrashService`
- `RecoveryService`
- `OCRProvider`
- `ImageRenderer`
- `VideoEncoder`
- `SettingsStore`
- `OperationJournal`

macOS 和 Windows 各自实现平台能力，合同测试保证返回结构和错误语义一致。

### 5.4 Presentation

QML 不直接调用业务函数。每页对应一个 ViewModel：

- 暴露 Property：当前路径、状态、统计、选择项、是否忙碌。
- 暴露 Signal：进度、完成、失败、确认请求。
- 暴露 Slot：扫描、执行、撤回、取消、切换选择。
- 列表数据使用 QAbstractListModel。
- ViewModel 在应用生命周期内保留，页面切换不会丢失项目状态。

## 6. 平台视觉策略

### 6.1 统一设计 Token

每套皮肤必须提供：

- 背景、面板、浮层、边框、文字、强调色和状态色。
- 面板和控件圆角。
- 阴影等级。
- 字体和字号。
- 间距密度。
- 动画时长和缓动。

七套皮肤只覆盖 Token，不复制业务页面。

### 6.2 MotionPolicy

定义三档：

- `Full`：macOS 默认，使用页面转场、弹簧反馈、列表重排和材质变化。
- `Reduced`：Windows 默认，保留 120–180ms 的必要状态反馈。
- `None`：系统开启减少动态效果时使用。

动画不得延迟文件操作，不得覆盖按钮，不得让列表失去滚动和点击。

### 6.3 EffectPolicy

- macOS：允许 NSVisualEffectView、透明 QQuickWindow 背景和主题材质。
- Windows：第一版使用实体背景和轻量阴影；Mica/Acrylic 作为后续可选增强。
- 编辑部极简和柔软三维使用浅色系统控件。
- 图片/视频画布固定中性背景。

## 7. 功能迁移策略

### 7.1 先建立 Characterization Tests

迁移现有逻辑前，先针对 v1.4.0 输出建立黑盒样本：

- 同一输入文件集合产生相同重命名计划。
- 配对数量、待清理列表和冲突结果一致。
- XMP 解析、写入和撤回结果一致。
- 关键词对齐矩阵、时间线和导出帧数一致。

不得先复制代码再补测试。

### 7.2 分步迁移

1. 复制纯 Python 核心并去除 GUI 依赖。
2. 将操作系统调用替换为 Port。
3. 建立 ViewModel，不连接正式 QML。
4. 用测试驱动每页接入。
5. 最后加入动效、材质和主题差异。

### 7.3 关键词快切重构

当前 SwiftUI 界面不会继续嵌入新 QML 软件，但其算法和能力作为参考：

- 将对齐算法与时间线公式迁移为共享 Python Domain。
- macOS Vision OCR 拆成无界面的原生服务动态库。
- Windows OCR 适配到统一 OCRResult。
- 图片渲染和视频编码只通过共享接口调用。
- QML 重新实现队列、候选框、目标框和参数面板。
- 增加输入事件回归，防止图片层截获侧栏和工具栏点击。

## 8. 数据与配置迁移

### 8.1 只读迁移来源

- `~/Library/Application Support/旭影工具箱/`
- `~/Library/Application Support/旭影的摄影工具集-关键词内嵌版/`
- `~/Library/Application Support/摄影文件后期处理助手/`
- Windows 对应 `%APPDATA%` 目录。
- 关键词对齐器旧 UserDefaults 域。

### 8.2 新数据目录

新版本写入独立的 v2 配置目录和版本化 Schema。首次启动：

1. 查找新配置。
2. 没有新配置时读取旧配置。
3. 转换并写入新目录。
4. 不修改、不删除旧目录。
5. 写入迁移版本和来源记录。

撤回记录只有在格式兼容并通过验证时迁移；否则旧版继续负责旧操作的撤回，新版显示清晰说明。

## 9. 实施阶段

### 阶段 0：基线审计与技术验证

交付物：

- v1.4.0 功能等价矩阵。
- 输入/输出和撤回数据 Schema。
- Characterization Test 清单与脱敏夹具。
- Windows OCR 对比报告。
- PySide6/QML 最小程序在 macOS/Windows 的打包验证。
- 风险登记表。

完成门槛：用户确认审计结果和最终 OCR/打包选择。

### 阶段 1：工程脚手架

交付物：

- `pyproject.toml`、依赖锁和目录结构。
- 应用启动器、日志、错误模型和平台检测。
- pytest/pytest-qt/QML 测试入口。
- macOS 与 Windows CI 基础流程。
- 最小 QML Shell 和占位页面。

完成门槛：两个平台能启动空壳、运行测试并生成试验包。

### 阶段 2：共享核心迁移

顺序：

1. 文件扫描和格式识别。
2. 时间重命名。
3. RAW/JPG 配对清理。
4. XMP 读取、写入和同步。
5. 事务日志、备份、回滚和撤回。

完成门槛：不启动 GUI 即可通过全部等价测试。

### 阶段 3：QML 设计系统和主框架

交付物：

- 主窗口、侧栏、标题栏、状态栏和页面路由。
- 七套主题 Token。
- Button、Field、Select、Table、Dialog、Toast、Progress 等组件。
- Full/Reduced/None 动效策略。
- 键盘导航、焦点环和高 DPI 规则。

完成门槛：四个占位页面在七套皮肤和三个动效档位下无裁切。

### 阶段 4：前三个照片工具接入

每个页面都按以下顺序：

1. ViewModel。
2. 只读扫描和预览。
3. 确认与执行。
4. 进度和取消。
5. 撤回。
6. 空状态、错误状态和大列表。
7. 平台实机验收。

完成门槛：时间重命名、配对清理和 XMP 同步在两个平台功能等价。

### 阶段 5：关键词快切接入

交付物：

- macOS Vision OCR Adapter。
- Windows 离线 OCR Adapter。
- 图片队列和虚拟化缩略图模型。
- 候选选择、目标框移动/缩放和拖动排序。
- PNG、帧序列和 MP4 导出。
- 项目状态保留、取消和错误恢复。

完成门槛：两个平台完成 21 张截图 OCR、编辑和三种格式导出验收。

### 阶段 6：平台视觉增强

macOS：

- 原生磨砂背景。
- 页面转场、弹簧按钮、列表重排和面板展开动画。
- 系统 Reduced Motion 联动。

Windows：

- Reduced Motion 默认值。
- 高 DPI、窗口缩放和实体背景。
- 回收站与中文路径专项测试。

完成门槛：动画不影响点击、滚动、拖拽和后台任务。

### 阶段 7：数据迁移与打包

交付物：

- v1 → v2 设置迁移器。
- macOS arm64 App、ZIP、DMG。
- Windows x64 安装程序和便携 ZIP。
- 第三方许可证与 FFmpeg/PySide6 合规说明。
- 签名、公证和 SmartScreen 文档。

完成门槛：两个平台在干净用户环境首次启动并完成迁移。

### 阶段 8：发布候选与正式发布

版本建议：

- `2.0.0-alpha.1`：共享核心和空壳。
- `2.0.0-beta.1`：四个工具功能完成。
- `2.0.0-rc.1`：打包和迁移完成。
- `2.0.0`：实机验收通过。

发布前必须核对：

- Git tag、版本号和应用显示名。
- 两个平台产物名称、架构、签名和依赖。
- Release 更新说明与 SHA-256。
- GitHub Release 资产真实存在、大小正确、下载链接返回成功。

## 10. 验收矩阵

| 类别 | macOS | Windows |
| --- | --- | --- |
| 启动与窗口 | macOS 13+ arm64 | Windows 10/11 x64 |
| 重命名 | 扫描、冲突、执行、撤回 | 同等功能 |
| 配对清理 | 废纸篓、恢复副本、恢复 | 回收站、恢复 |
| XMP 同步 | 双向、备份、回滚、撤回 | 同等功能 |
| 关键词 OCR | Apple Vision | 离线 Windows Adapter |
| 快切编辑 | 队列、候选、目标框、排序 | 同等功能 |
| 导出 | PNG、逐帧 PNG、MP4 | 同等功能 |
| 皮肤 | 七套完整 | 七套完整 |
| 动画 | Full + Reduced Motion | Reduced + None |
| 缩放 | 1300×760、全屏、高 DPI | 100%、125%、150%、200% DPI |
| 路径 | 中文、空格、外置盘、网络盘 | 中文、空格、长路径、盘符 |

## 11. 性能目标

- 冷启动：目标 3 秒内进入可操作状态。
- 普通页面切换：不超过 150ms 的主线程阻塞。
- 1,000 行列表：滚动无明显卡顿，不一次实例化全部 Delegate。
- 21 张截图 OCR：持续显示进度，可取消，界面保持响应。
- 大型导出：内存有上限，不一次把所有帧保存在内存。
- 扫描 10,000 个文件：后台执行并分批更新模型。

性能目标必须在代表性硬件上记录实测结果，不能只凭主观感受宣布完成。

## 12. 主要风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| QML 打包遗漏插件 | 安装包无法启动 | 阶段 0 先做两个平台最小打包 |
| Windows OCR 与 Vision 结果不同 | 快切候选不一致 | 统一结果结构、容差和人工候选校正 |
| 原生磨砂与 QQuickWindow 冲突 | 闪烁或点击穿透 | 原生层只做背景，交互全部留给 QML |
| Python 后台任务误碰 UI | 崩溃或界面卡死 | 统一 TaskRunner 与主线程 Signal 回传 |
| QML 业务逻辑膨胀 | 难测试、难迁移 | 强制 ViewModel/Use Case 边界 |
| FFmpeg 体积和许可证 | 安装包变大 | 固定构建来源并附第三方许可证 |
| 旧撤回记录不兼容 | 用户无法撤回 | 版本化 Schema，兼容失败时不迁移并明确提示 |
| 七套主题状态不完整 | 部分控件不可读 | Token 合同测试和页面截图矩阵 |

## 13. 推荐开发顺序

严格按以下优先级推进：

```text
安全与等价测试
→ 共享核心
→ 平台 Adapter
→ ViewModel
→ 可操作 QML 页面
→ 七套主题
→ 动画和磨砂
→ 打包与迁移
→ 实机发布
```

不要先制作漂亮空壳，再回头寻找业务逻辑应该放在哪里。

## 14. 最终完成定义

重构只有在以下条件同时满足时完成：

- v1.4.0 四项工具的功能等价矩阵全部通过。
- 两个平台没有永久删除、覆盖 RAW 或无法恢复的静默路径。
- 所有长任务保持界面响应并支持取消。
- 七套皮肤覆盖主窗口、对话框、列表、关键词快切和错误状态。
- macOS 动画完整，Windows Reduced Motion 不影响功能。
- macOS 与 Windows 安装包在干净环境可以启动和完成真实流程。
- 旧设置完成只读迁移，旧项目和旧安装包没有被修改。
- 文档、测试报告、许可证、校验值和 Release 资产全部验证。

