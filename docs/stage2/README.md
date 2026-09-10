# 阶段 2 · Mac 共享核心验收

日期：2026-09-06

## 状态

**阶段 2 的 Mac 共享核心已完成，Windows 平台适配与实机验收仍延期。**

本阶段只迁移无界面的照片业务核心，没有连接 QML、ViewModel 或真实用户照片。Domain 与 Application 均由自动架构测试约束：Domain 不允许导入 Qt、ExifRead、Send2Trash、Infrastructure 或平台实现；Application 不允许导入 UI、Infrastructure 或 Platform。

## 源码映射

参考基线：开发者本地只读的 v1.4.0 副本，提交 `4a287ff57f43b2632861d86607ea0c088793743f`。

| v1.4.0 范围 | 新位置 |
| --- | --- |
| 文件格式、共享数据结构 | `domain/models/photo.py` |
| 时间重命名规划 | `domain/services/rename.py` |
| 两阶段改名 | `infrastructure/filesystem/rename_transaction.py` |
| 重命名 manifest | `infrastructure/persistence/rename_journal.py` |
| RAW/JPG 配对规则 | `domain/services/cleanup.py` |
| macOS 恢复副本与废纸篓 | `platform/macos/trash.py` |
| XMP 字节解析与更新 | `domain/services/xmp.py` |
| XMP 同步规划 | `domain/services/xmp_sync.py` |
| JPEG/侧车读写 | `infrastructure/metadata/xmp_file.py` |
| XMP 备份、回滚与撤回 | `infrastructure/metadata/xmp_transaction.py` |
| 用例依赖装配 | `infrastructure/composition.py` |

## 已保留的行为

- 23 种 RAW 与 JPG/JPEG，扩展名比较不区分大小写。
- 产品默认只扫描当前文件夹，不递归。
- EXIF 拍摄时间优先，损坏或缺失时回退修改时间。
- RAW/JPG 同编号分组、日期编号续接、扩展名大小写保留。
- `.xmp` 与 `.RAW.xmp` 两种侧车同步改名。
- 冲突阻止、manifest 先落盘、两阶段改名、失败回滚和撤回。
- RAW/JPG 同目录、同主文件名、大小写不敏感配对。
- 清理前安全恢复副本，硬链接失败回退完整复制。
- 只进入系统废纸篓，不提供永久删除路径。
- 恢复不覆盖同名文件，部分恢复只保留未完成记录。
- XMP 支持 `xmp:`/`xap:`、属性/元素、单双引号、UTF-8/UTF-16。
- JPG 标准 APP1 XMP 插入/更新，保留 EXIF 与其他已支持字段。
- RAW 只写侧车，RAW 原文件字节保持不变。
- 执行前完整备份，任一目标失败整批回滚，支持撤回最近一批。

## 新增安全收紧

- 扫描与 Mac 废纸篓适配器都拒绝符号链接，避免操作越出确认目录。
- v2 只写独立 `旭影工具箱/v2` 数据目录，不触碰旧版记录。
- 重命名与清理记录使用临时 JSON 原子替换。
- 重命名失败时保留并标记 `failed` journal；撤回只选择 `completed` 批次，避免回滚异常时丢失恢复线索。
- 清理记录在调用废纸篓前落盘；如果系统移动后才报错，恢复记录与副本仍保留。
- 清理恢复支持记录路径、设备号/inode 定位和 Finder 准确文件名回退。
- 大 JPEG 的 XMP 扫描只读取 metadata 段，不加载压缩像素数据。
- 未知或损坏的 XMP namespace 会停止写入并保持原字节；备份阶段失败会清理未提交会话。
- Application 通过端口编排，具体文件/废纸篓/XMP 写入全部在适配层。

## 验证结果

| 验证 | 结果 |
| --- | --- |
| v1.4.0 原 Python 全套（阶段 2 复跑） | 68 passed，2 个旧 Tk 键盘焦点测试失败，2 个按平台条件跳过 |
| v1.4.0 `test_core.py`（本阶段依据） | 30 passed |
| 阶段 2 新专项测试 | 65 passed |
| 新项目全套测试 | 75 passed |
| 旧/新同夹具重命名计划 | 一致 |
| 旧/新同夹具清理计划 | 一致 |
| 旧/新同夹具 XMP 计划 | 一致 |
| Domain/Application 架构边界 | 通过 |
| Ruff 与格式 | 通过 |
| QML lint | 通过，阶段 2 未改正式页面 |

所有修改操作测试都使用 pytest 临时目录、假 RAW 字节、最小 JPEG 和注入的假废纸篓；没有调用真实废纸篓，也没有读取或修改用户照片。

旧版全套的两个失败分别是清理单选按钮和侧栏在无界面测试中的 Return 键焦点激活；同一套测试在阶段 0 曾 70 项通过。它们不属于共享核心，且 `test_core.py` 本次仍是 30/30 通过，因此不作为阶段 2 核心失败，但保留在证据中等待旧 GUI 环境复核。

## 尚未覆盖

- Windows 回收站适配器与实机合同。
- 网络盘、移动盘和不同文件系统的真实设备测试；当前只通过故障注入验证硬链接失败回退复制。
- Extended XMP、多标准 XMP APP1、无 BOM UTF-16 和接近 APP1 上限等低频格式仍按阶段 0 风险登记处理。
- Finder 与 inode 定位没有读取用户真实废纸篓，仅用准确文件名脚本和注入的假废纸篓验证。
- 阶段 2 核心尚未连接 ViewModel/QML；这属于阶段 4。

## 下一阶段边界

若用户确认进入阶段 3，只建立 Mac QML 设计 Token、主框架组件、四页占位布局和动效策略，不接照片写入功能。Windows 未验收前不得宣称跨平台阶段 2/3 完成。
