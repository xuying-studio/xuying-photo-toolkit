# v1.4.0 数据 Schema 与 v2 迁移边界

所有示例路径均为虚构脱敏路径。迁移器只能读取旧目录，写入必须进入独立的 v2 目录。

## 1. 扫描与执行对象

### 时间重命名

```text
RenameOperation
  source: str
  target: str
  kind: "照片" | "XMP 侧车"

RenameScanStats
  total_images: int
  raw_count: int
  jpg_count: int
  already_named_count: int
  skipped_count: int
  xmp_count: int

RenamePlan
  operations: list[RenameOperation]
  image_count: int
  conflicts: list[str]
  warnings: list[str]
  stats: RenameScanStats
```

支持扩展名：JPG、JPEG，以及 ARW、CR2、CR3、CRW、NEF、NRW、RAF、RW2、ORF、PEF、DNG、X3F、3FR、FFF、SRW、MRW、MOS、ERF、IIQ、KDC、MEF、RAW、GPR；比较时不区分大小写，输出时保留原大小写。

### 配对清理

```text
CleanupItem
  path: str
  missing_pair_kind: str

CleanupScanResult
  items: list[CleanupItem]
  total_images: int
  raw_count: int
  jpg_count: int
  target_count: int
  paired_target_count: int
```

`delete_kind` 仅允许 `JPG` 或 `RAW`。

### XMP 同步

```text
SyncOperation
  source: str
  target: str
  target_is_raw: bool
  rating: int | null
  label: str | null
  old_rating: int
  old_label: str | null

SyncScanResult
  operations: list[SyncOperation]
  total_images: int
  source_count: int
  target_count: int
  matched_count: int
  marked_count: int
  up_to_date_count: int
```

`direction` 仅允许 `JPG → RAW` 或 `RAW → JPG`；`sync_rating`、`sync_label` 至少一个为真。

## 2. 重命名撤回记录

旧路径：

- macOS：`~/Library/Application Support/摄影文件后期处理助手/rename_backups/`
- Windows：`%APPDATA%\摄影文件后期处理助手\rename_backups\`

```json
{
  "created_at": "2026-09-05T10:00:00+08:00",
  "operations": [
    {
      "source": "/fixtures/session/A001.ARW",
      "target": "/fixtures/session/DSC26-09-05-00001.ARW",
      "kind": "照片"
    },
    {
      "source": "/fixtures/session/A001.xmp",
      "target": "/fixtures/session/DSC26-09-05-00001.xmp",
      "kind": "XMP 侧车"
    }
  ]
}
```

v2 兼容要求：不得修改原清单；解析失败、源/目标冲突或来源文件身份无法确认时，只展示“请使用旧版撤回”，不得猜测执行。

## 3. 清理恢复记录

旧路径：`~/Library/Application Support/摄影文件后期处理助手/cleanup_undo.json` 或 Windows 对应 AppData 路径。

```json
{
  "created_at": "2026-09-05T10:05:00+08:00",
  "paths": [
    "/fixtures/session/A001.JPG"
  ],
  "items": [
    {
      "original_path": "/fixtures/session/A001.JPG",
      "deleted_at": "2026-09-05T10:05:01+08:00",
      "trash_path": "/fixtures/trash/A001.JPG",
      "device": 16777220,
      "inode": 123456,
      "recovery_path": "/fixtures/session/.摄影文件后期处理助手-恢复备份/session/A001.JPG",
      "recovery_method": "hardlink"
    }
  ]
}
```

兼容旧格式：若没有 `items`，旧版会把 `paths` 转换为仅含 `original_path` 的记录。`recovery_method` 为 `hardlink`、`copy` 或 `null`；Windows 通常没有 `recovery_path`。

注意：旧版只有一份 `cleanup_undo.json`，后一批清理会覆盖前一批记录。v2 不得把它误读成完整历史。

## 4. XMP 同步备份

旧路径：`~/Library/Application Support/摄影文件后期处理助手/xmp_backups/<session>/manifest.json`。

```json
{
  "created_at": "2026-09-05T10:10:00+08:00",
  "undone_at": null,
  "entries": [
    {
      "target": "/fixtures/session/A001.JPG",
      "target_is_raw": false,
      "backup_method": "hardlink",
      "backup_name": "00000_A001.JPG.bak"
    },
    {
      "target": "/fixtures/session/B001.ARW",
      "target_is_raw": true,
      "sidecar": "/fixtures/session/B001.xmp",
      "sidecar_existed": true,
      "backup_name": "00001_B001.xmp.bak"
    },
    {
      "target": "/fixtures/session/C001.ARW",
      "target_is_raw": true,
      "sidecar": "/fixtures/session/C001.xmp",
      "sidecar_existed": false
    }
  ]
}
```

JPG 目标条目包含 `backup_method`，值为 `hardlink` 或 `copy`；RAW 侧车条目不包含该字段。RAW 侧车原本不存在时也没有 `backup_name`，撤回语义是删除本批新建的侧车。

## 5. 关键词快切设置与运行态

UserDefaults 键：`KeywordAligner.ProjectSettings.v1`。

读取顺序：当前应用的 `UserDefaults.standard` → 旧 suite `com.xuying.keyword-aligner`。仅当前域缺失时复制旧值；旧域不删除。

```json
{
  "aspectRatio": "9:16",
  "width": 1080,
  "height": 1920,
  "frameRate": 30,
  "framesPerImage": 4,
  "keyword": "婚礼摄影",
  "targetRect": {
    "x": 0.33,
    "y": 0.475,
    "width": 0.34,
    "height": 0.05
  },
  "exportMode": "MP4"
}
```

允许值：

- `aspectRatio`：`9:16`、`16:9`、`1:1`、`4:5`、`3:4`、`自定义`
- `exportMode`：`处理后 PNG`、`逐帧 PNG`、`MP4`
- `targetRect`：0–1 归一化坐标；宽高最小 0.01

运行态 `OCRCandidate`：

```text
id: UUID
text: str
box: NormalizedRect
confidence: float
isExactMatch: bool
similarity: float
```

运行态 `RecognitionState`：`pending`、`recognizing`、`matched`、`fuzzyMatched`、`notFound`、`failed`。图片队列、OCR 缓存和当前选择只存在进程内，不是持久工程文件。

## 6. 快切输出

输出目录：`<安全关键词>-yyyyMMdd-HHmmss[-suffix]`。

- 处理后 PNG：`001-<原文件名>.png`
- 逐帧 PNG：`000001.png`
- MP4：`<安全关键词>-effect.mp4`

MP4 为 H.264 视频，无音轨。总帧数为 `图片数 × framesPerImage`，总时长由有理帧率计算。

## 7. v2 新目录与版本化包装建议

v2 应写入独立目录，例如：

- macOS：`~/Library/Application Support/旭影工具箱/v2/`
- Windows：`%APPDATA%\旭影工具箱\v2\`

每份 v2 清单至少增加：

```json
{
  "schema_version": 2,
  "operation_id": "uuid",
  "created_at": "ISO-8601 with timezone",
  "source_version": "1.4.0",
  "source_manifest": "/read-only/legacy/path",
  "platform": "macos | windows",
  "state": "planned | executing | completed | rollback_required | undone",
  "entries": []
}
```

这是 v2 建议，不是 v1.4.0 已存在字段。迁移实现前必须先用 Characterization Test 锁定旧格式，再决定哪些旧撤回记录可以安全导入。
