<div align="center">
  <h1>📷 旭影的摄影工具集</h1>
  <p>给摄影工作流一键装上「整理、配对、同步」能力。</p>
  <p>把按拍摄时间重命名、RAW/JPG 配对清理、Adobe Bridge 星标与颜色标签同步，收进一个克制、安全的 macOS 图形界面。</p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/xuying-studio/xuying-photo-toolkit?style=flat-square" alt="MIT License"></a>
    <img src="https://img.shields.io/badge/macOS-11%2B-000000?style=flat-square&amp;logo=apple" alt="macOS 11+">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.10+">
  </p>
  <p>
    <img src="assets/app_icon.png" width="144" alt="旭影的摄影工具集应用图标">
  </p>
  <p>
    <a href="#-快速开始">快速开始</a> ·
    <a href="#-它能做什么">功能清单</a> ·
    <a href="#-在你动手前你可能想知道">安全机制</a> ·
    <a href="docs/使用说明.md">完整说明</a> ·
    <a href="#-从源码构建">从源码构建</a> ·
    <a href="CONTRIBUTING.md">贡献</a> ·
    <a href="#-许可证">许可证</a>
  </p>
</div>

---

## 为什么需要它？

拍完一组照片后，最耗时间、也最不该靠手工硬扛的，往往是这些琐碎步骤：

- 📁 RAW、JPG、XMP 侧车混在多个子文件夹里，想按拍摄日期统一命名。
- 🧹 导出或转存后留下孤立 JPG / RAW，不敢批量清理，怕删错。
- ⭐ 在 Adobe Bridge 里选好片，却要在 JPG 和 RAW 之间反复同步星标、颜色标签。
- 🛡️ 想批量处理，但更担心重名覆盖、误删文件，或改完后无法回退。

这些事并不复杂，但一次次手动整理非常容易出错。

旭影的摄影工具集把流程固定为：**先扫描和预览 → 看清待处理数量 → 确认后执行 → 必要时撤回**。

---

## ✨ 它能做什么？

| 功能 | 你会用在什么时候 | 它怎么保护你的文件 |
| --- | --- | --- |
| 🕒 按时间重命名 | 统一整理 RAW、JPG 与 XMP 侧车 | 预览、冲突阻止、两阶段改名、可撤回 |
| 🧹 RAW / JPG 配对清理 | 找出缺少同名配对文件的 JPG 或 RAW | 仅移入废纸篓，另建安全恢复副本 |
| ⭐ 星标与颜色同步 | 在同名 RAW/JPG 间同步 Adobe Bridge 标记 | RAW 只写 `.xmp`；目标完整备份，可撤回 |

所有页面默认递归扫描所选文件夹及其子文件夹，并在扫描后显示照片总数、配对情况和实际待处理数量。

> 不需要记命令，也不会在你点击“执行”前修改任何照片文件。

---

## ✅ 在你动手前，你可能想知道

| 关注点 | 说明 |
| --- | --- |
| 🔒 隐私 | 所有照片、文件路径和元数据只在本机处理；应用没有上传、同步或发送照片的功能。 |
| 👀 先预览 | 三个功能都必须先扫描，列表和统计信息会在执行前展示出来。 |
| 🛡️ 不覆盖 | 重命名遇到目标已存在或目标冲突时会直接停止，不会静默覆盖。 |
| 🗑️ 不永久删除 | 配对清理只移入 macOS 废纸篓，并保留本地安全恢复副本。 |
| ↩️ 可撤回 | 重命名、清理恢复和 XMP 同步都保留最近一次操作的恢复能力。 |
| 📷 尊重 RAW | RAW 原始文件永远不直接写入；元数据只通过 `.xmp` 侧车处理。 |

> ⚠️ 这是批量文件工具，不是备份工具。第一次处理某个摄影项目时，请先拿一小批副本验证结果。

---

## 🚀 快速开始

### 直接使用 macOS App

1. 在项目的 [Releases](https://github.com/xuying-studio/xuying-photo-toolkit/releases) 下载 `.dmg`。
2. 打开镜像，将“旭影的摄影工具集.app”拖入“应用程序”。
3. 打开 App，选择照片文件夹，先点击“扫描并预览”。

> 请优先下载 DMG 安装包。当前发布包使用本地 ad-hoc 签名，尚未经过 Apple Developer ID 公证；在其他 Mac 上首次打开时，可能需要右键点击 App 后选择“打开”。

### 从源码运行

要求：macOS 11 或更高版本、Python 3.10 或更高版本，以及系统自带的 Tkinter。

```bash
git clone https://github.com/xuying-studio/xuying-photo-toolkit.git
cd xuying-photo-toolkit
python3 -m pip install -r requirements.txt
python3 main.py
```

### 第一次处理照片，建议这样做

1. 复制一小组 RAW/JPG 到测试文件夹。
2. 选择对应功能页，点击“扫描并预览”。
3. 核对统计卡片和待处理列表。
4. 再点击执行，并检查结果。
5. 确认符合预期后，再处理完整项目。

完整操作步骤、支持格式、命名规则、恢复机制与常见问题见：[📖 详细使用说明](docs/使用说明.md)。

---

## 🧭 三个功能怎么用？

### 🕒 根据拍摄时间重命名

#### 什么时候用？

当你使用多台相机联合拍摄时，不同设备的文件编号往往互不连续；
又或者相机拍到 `9999` 张后重新从 `0001` 开始编号。此时，单纯按文件名排序无法反映真实的拍摄先后顺序。

使用这个功能后，工具会读取照片的 EXIF 拍摄时间，将待处理的 RAW、JPG 和对应 XMP 侧车按真实时间顺序统一整理为连续编号。
这样，无论照片来自几台设备，文件列表都能按照正确的拍摄时间顺序排列，后续选片、导入 Lightroom 或交付都会更清晰。

输出格式为：

```text
DSC26-07-25-00001.arw
DSC26-07-25-00001.jpg
DSC26-07-25-00001.xmp
```

工具优先使用 EXIF 拍摄时间；无法读取 EXIF 时会使用文件修改时间作为备用依据。同名 RAW 的 `.xmp` 侧车会一起改名；已符合格式的照片会保留，编号会从当日已有最大编号继续，避免覆盖已有文件。

### 🧹 RAW / JPG 同步清理

#### 什么时候用？

后期整理时，你可能已经单独删除了某些 RAW 文件；但对应的 JPG 仍留在硬盘中。若希望把这些失去 RAW 配对的 JPG 也一并清理，就可以使用这个功能。

例如，你删除了 `A001.ARW`，但 `A001.JPG` 还在。选择“JPG（没有对应 RAW）”后，工具会找出这类孤立 JPG，让你先预览，再统一移入废纸篓。反过来，如果你想清理没有对应 JPG 的 RAW，也可以选择“RAW（没有对应 JPG）”。

配对仅在**同一文件夹内**按同名主文件名进行，且不区分大小写：

```text
A001.JPG  ↔  a001.ARW
```

文件不会被永久删除，而是移入mac的废纸篓；恢复时优先使用隐藏安全恢复副本，必要时才请求 Finder 协助。

### ⭐ Adobe Bridge 星标与颜色同步

#### 什么时候用？

如果你习惯只在 RAW 文件上完成选片，例如在 Adobe Bridge 中给 RAW 打星、标记颜色，但又希望对应 JPG 也拥有完全相同的标记，就可以使用这个功能。

选择 `RAW → JPG` 后，工具会读取 RAW 侧车中的星标和颜色标签，并同步写入同名 JPG。
反过来，如果你的标记先做在 JPG 上，也可以选择 `JPG → RAW`，将标记同步到 RAW 的 `.xmp` 侧车。

可分别选择同步星标、颜色标签或两者：

- 写入 RAW 时，仅创建或更新 `.xmp` 侧车。
- 写入 JPG 时，先完整备份目标 JPG，再更新内嵌 XMP。
- 一批操作中任一文件失败，会自动恢复已处理的目标，避免半完成状态。

---

## 🎨 外观与本地数据

应用会跟随 macOS 浅色/深色外观。右上角“外观…”支持 70%–100% 界面透明度，默认 92%，调整可即时预览。

透明度设置保存在：

```text
~/Library/Application Support/旭影的摄影工具集/ui_config.json
```

为兼容旧版本的撤回记录，业务备份目录保留历史名称。具体位置和清理恢复机制请参阅[详细使用说明的本地数据章节](docs/使用说明.md#8-本地数据与隐私)。

---

## 🧰 从源码构建

```bash
chmod +x build_app.sh
./build_app.sh
```

脚本会先执行全部测试，再生成 Apple Silicon 与 Intel 通用的：

- `dist/旭影的摄影工具集.app`
- `dist/旭影的摄影工具集-macOS-universal.zip`
- `dist/旭影的摄影工具集-macOS-universal.dmg`

默认使用本地 ad-hoc 签名。若要对外无警告分发，请准备 Apple Developer ID Application 证书和 `notarytool` 配置：

```bash
APPLE_SIGN_IDENTITY="Developer ID Application: 你的名称 (TEAMID)" \
APPLE_NOTARY_PROFILE="你的-notarytool-profile" \
./build_app.sh
```

---

## 📦 历史独立脚本

仓库根目录保留了项目最初的三份独立脚本，供追溯与参考：

- `根据时间重命名文件排序.py`
- `根据RAW:JPG双向同步.py`
- `同步颜色与星号标记.py`

日常使用请优先运行统一图形应用 `main.py` 或 macOS App。统一应用包含递归扫描统计、冲突保护和更完整的撤回机制；历史脚本不再作为推荐入口维护。

---

## 🤝 贡献与反馈

- 想参与开发？请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。
- 遇到错误或有功能建议？请提交 [Issue](https://github.com/xuying-studio/xuying-photo-toolkit/issues)。
- 发现可能导致覆盖、丢失或泄露文件的问题？请按 [SECURITY.md](SECURITY.md) 的方式私密报告。

请勿在 Issue 中上传真实照片、完整个人路径、废纸篓记录或含私密元数据的 EXIF/XMP 文件。

---

## 📄 许可证

[MIT License](LICENSE) © 2026 旭影
