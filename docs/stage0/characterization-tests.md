# Characterization Test 与脱敏夹具清单

目标不是证明旧实现完美，而是先固定 v1.4.0 的可观察行为，避免迁移时无意改变安全语义。

## 旧版测试实测

使用 `git archive` 从提交 `4a287ff57f43b2632861d86607ea0c088793743f` 创建仓库外副本 `/tmp/xuying-v140-audit-copy.2iq88c`，并在该副本中运行。参考目录没有生成缓存或测试输出。

环境：Python 3.12.1、pytest 9.1.1、ExifRead 3.5.1、Send2Trash 1.8.2。

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/tmp/xuying-v140-audit-copy.2iq88c/tmp \
  uv run --no-project --with pytest --with 'exifread>=3,<4' \
  --with 'Send2Trash>=1.8,<2' python -m pytest -p no:cacheprovider -q -rs
```

当前执行结果：

```text
70 passed, 2 skipped in 12.67s
```

跳过项：

- `tests/test_keyword_bridge_integration.py:20`：尚未构建关键词快切动态库。
- `tests/test_windows_integration.py:18`：仅在 Windows 执行。

核心逻辑专项结果：`tests/test_core.py` 共 30 项全部通过。

完整 Xcode 26.6（Build 17F113）已经可用。旧 Package 整体构建仍会被 Swift 6.3/Vision 新 SDK 的 UI 编译冲突阻止：`OCRService.swift` 的 `NormalizedRect` 与 `Vision.NormalizedRect` 名称冲突，另有 `sorted` 闭包推断问题。为区分 UI 兼容问题和核心算法结果，本次在仓库外建立只含原 `KeywordAlignerCore` 源码及原测试的最小 Package，7 个 Core 测试全部通过、0 失败。旧完整包不能记为通过，相关冲突进入迁移风险。

## 脱敏夹具规则

- 一律使用随机临时目录或仓库内 `tests/fixtures`，不引用真实用户照片路径。
- RAW 使用固定假字节，例如 `b"raw-fixture"`；不提交真实 RAW。
- JPG 使用最小合法 JPEG 或程序生成的小尺寸色块图。
- XMP 只保留虚构 Rating/Label，不含 GPS、机身序列号、作者、客户姓名。
- OCR 图片使用合成文字或经过人工确认的脱敏截图。
- 报告中仅记录相对路径、basename、哈希和结构化字段。
- 测试废纸篓必须使用专用临时文件，禁止操作用户真实目录。

已建立的 OCR 合成夹具位于 `experiments/stage0_ocr/fixtures/`，包含中文、空格、中英混排、时间、低对比度和轻微旋转六种情况。

## 时间重命名

| ID | 输入 | 必须锁定的输出 |
| --- | --- | --- |
| RN-T01 | 同组 RAW/JPG，扩展名大小写混合 | 同一编号，扩展名大小写保留 |
| RN-T02 | EXIF 有效、缺失、损坏 | 有效走 EXIF，其余走 mtime |
| RN-T03 | `.xmp`、`.RAW.xmp` 分别与同时存在 | 侧车全部进入计划且风格保留 |
| RN-T04 | 已存在同日编号文件 | 从当天最大编号继续 |
| RN-T05 | 文件名没有数字 | 跳过并产生 warning |
| RN-T06 | 目标路径已存在 | 冲突阻止整个执行 |
| RN-T07 | 两个源映射同一目标 | 冲突阻止整个执行 |
| RN-T08 | 第二阶段改名故障注入 | 源文件恢复，无临时名残留 |
| RN-T09 | 改名后新增 RAW 侧车再撤回 | 新侧车按旧版规则返回原名 |
| RN-T10 | 撤回目标已有同名文件 | 不覆盖并给出可操作错误 |
| RN-T11 | 网络盘、移动盘、符号链接 | 明确支持/拒绝策略且不丢文件 |

## RAW/JPG 配对清理

| ID | 输入 | 必须锁定的输出 |
| --- | --- | --- |
| CL-T01 | `A001.JPG` + `a001.ARW` | 大小写不敏感配对 |
| CL-T02 | 同名但位于不同子目录 | 不跨目录配对 |
| CL-T03 | JPG/JPEG 混合 | 两种扩展名均按 JPG 处理 |
| CL-T04 | 隐藏文件、隐藏恢复目录 | 不进入扫描结果 |
| CL-T05 | 清理孤立 JPG 与孤立 RAW | 两个方向目标集合正确 |
| CL-T06 | macOS 硬链接成功/失败 | 成功用硬链接，失败回退完整复制 |
| CL-T07 | 多文件中途失败 | 清单只含已成功移动项，错误可见 |
| CL-T08 | 原位置已有同名文件 | 恢复不覆盖，记录保留 |
| CL-T09 | 安全副本、废纸篓直读、Finder/Windows 回退 | 三条恢复路径分别验证 |
| CL-T10 | 部分恢复后再次恢复 | 已成功项不再处理 |
| CL-T11 | 回收站已清空或手工改名 | 明确失败，不猜测同名文件 |

## Adobe XMP

| ID | 输入 | 必须锁定的输出 |
| --- | --- | --- |
| XM-T01 | `xmp:` 与 `xap:` | 两种前缀都可读取/更新 |
| XM-T02 | 属性、元素、单双引号 | 形式兼容，其他字段保持 |
| XM-T03 | UTF-8 与 UTF-16 RAW 侧车 | 读取正确；写后可再次解析 |
| XM-T04 | JPEG 无 XMP、已有标准 XMP、同时含 EXIF APP1 | 插入/替换正确，不破坏 EXIF |
| XM-T05 | Rating 0、1–5、`2.0`、非法值 | 只同步合法非零星标 |
| XM-T06 | 空/非空 Label | 只同步非空标签 |
| XM-T07 | RAW 无侧车 | 创建侧车；撤回后删除 |
| XM-T08 | JPG 完整备份 | 撤回后字节哈希与执行前相同 |
| XM-T09 | 第二个目标写入失败 | 第一目标自动回滚 |
| XM-T10 | Extended XMP、多个 XMP APP1、畸形 XML | 明确兼容、拒绝或风险提示 |
| XM-T11 | `.xmp` 与 `.RAW.xmp` 同时存在 | 侧车选择策略与 Bridge 行为核对 |

## 关键词快切

| ID | 输入/操作 | 必须锁定的输出 |
| --- | --- | --- |
| QC-T01 | PNG/JPG/JPEG/HEIC 与文件夹导入 | 隐藏项过滤、去重、稳定排序 |
| QC-T02 | 简中、英文、中英混排、空格与标点 | 文字、候选框、置信度结构 |
| QC-T03 | 完全匹配与相似度 0.69/0.70 | 阈值边界和候选排序 |
| QC-T04 | 同一文本多个候选 | 默认选择与手动切换 |
| QC-T05 | 无文字/无关键词 | `notFound` 且按原图居中 |
| QC-T06 | OCR 过程中取消 | 当前项不永久停留在 `recognizing` |
| QC-T07 | 队列点击、滚动、删除、拖动排序 | 顺序、选择与焦点一致 |
| QC-T08 | 目标框移动/缩放越界 | 坐标钳制且画面可继续操作 |
| QC-T09 | 切换工具后返回 | 队列、候选、选择、目标框、参数保留 |
| QC-T10 | 六种比例与自定义尺寸 | 输出尺寸、裁切几何一致 |
| QC-T11 | 处理后 PNG | 文件数、尺寸、命名与像素基线 |
| QC-T12 | 逐帧 PNG | 文件数=`图片数 × framesPerImage`，序号连续 |
| QC-T13 | MP4 小数帧率 | `ffprobe` 核对帧数、时长、帧率、无音轨 |
| QC-T14 | 三种模式导出中取消 | 不把半成品误报为成功；残留策略明确 |
| QC-T15 | 非法文件名字符与同秒二次导出 | 安全名称且不覆盖旧目录 |
| QC-T16 | 图片同路径替换但 mtime 边界相同 | OCR 缓存不会误命中旧内容 |

## 平台、迁移与界面

| ID | 验收项 |
| --- | --- |
| PF-T01 | macOS 废纸篓/恢复副本与 Windows 回收站合同一致 |
| PF-T02 | 中文路径、空格、长路径、移动盘、网络盘、只读目录 |
| PF-T03 | 100%、125%、150%、200% DPI 与窗口缩放 |
| PF-T04 | Full、Reduced、None 三档动效不影响点击和取消 |
| PF-T05 | 1000 行列表与 21 张 OCR 长任务不阻塞主线程 |
| UI-T01 | 七主题覆盖四页、弹窗、Toast、禁用、错误、空状态 |
| UI-T02 | 文字对比度、键盘焦点、点击目标与滚动区域 |
| UI-T03 | 图片预览层不拦截侧栏、队列与工具栏 |
| MG-T01 | 无 v2 配置时只读导入旧设置，旧目录字节不变 |
| MG-T02 | 旧 JSON 缺字段、未知字段、损坏、编码异常 |
| MG-T03 | 撤回记录可安全迁移与不可迁移两条路径 |
| PK-T01 | macOS arm64 App/ZIP/DMG 在干净账户启动 |
| PK-T02 | Windows x64 安装版/便携 ZIP 在干净账户启动 |
| PK-T03 | QML 插件、平台插件、图片格式、字体、OCR 模型、FFmpeg 收集完整 |

## 阶段门禁

进入阶段 2 前，RN、CL、XM 的纯 Python Characterization Test 必须先在旧实现上固定预期，再在新 Shared Core 上复用同一预期。不得先迁移代码再补断言。
