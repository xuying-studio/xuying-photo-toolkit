# 旭影的摄影工具集

一个面向 macOS 的本地照片整理工具，将按拍摄时间重命名、RAW/JPG 配对清理、Adobe Bridge 星标与颜色标签同步整合到一个图形界面中。

> 所有照片处理均在本机执行。应用不会上传、同步或发送你的照片、元数据或文件路径。

![应用图标](assets/app_icon.png)

## 功能概览

| 功能 | 适用场景 | 安全措施 |
| --- | --- | --- |
| 时间重命名 | 统一整理 RAW、JPG 与 XMP 侧车 | 扫描预览、冲突阻止、两阶段改名、可撤回 |
| RAW/JPG 配对清理 | 找出缺少同名配对文件的 JPG 或 RAW | 仅移入废纸篓，同时创建安全恢复副本 |
| 星标与颜色同步 | 在同名 RAW/JPG 间同步 Adobe Bridge 标记 | RAW 仅写 `.xmp`，完整备份目标文件，可撤回 |

默认递归扫描所选文件夹内的所有子文件夹；每个功能在扫描后都会显示总照片数、配对数及待处理数量。

## 快速开始

### 直接使用 macOS App

从 Releases 下载 `.dmg`，打开后将“旭影的摄影工具集.app”拖入“应用程序”。首次使用请先复制一小批照片进行测试。

> 未经过 Apple Developer ID 签名和公证的构建，在其他 Mac 上首次打开时可能需要右键点击 App 后选择“打开”。

### 从源码运行

要求：macOS 11 或更高版本、Python 3.10 或更高版本，以及系统自带的 Tkinter。

```bash
git clone https://github.com/z865401745/xuying-photo-toolkit.git
cd xuying-photo-toolkit
python3 -m pip install -r requirements.txt
python3 main.py
```

## 使用说明

完整操作步骤、文件命名规则、支持格式、恢复机制、常见问题和数据存放位置见：[详细使用说明](docs/使用说明.md)。

## 历史独立脚本

仓库根目录保留了本项目最初的三份独立脚本，供追溯与参考：

- `根据时间重命名文件排序.py`
- `根据RAW:JPG双向同步.py`
- `同步颜色与星号标记.py`

日常使用请优先运行统一图形应用 `main.py` 或 macOS App。统一应用包含递归扫描统计、冲突保护和更完整的撤回机制；历史脚本不再作为推荐入口维护。

## 构建通用 macOS App

```bash
chmod +x build_app.sh
./build_app.sh
```

构建脚本会先执行全部测试，再生成 Apple Silicon 与 Intel 通用的：

- `dist/旭影的摄影工具集.app`
- `dist/旭影的摄影工具集-macOS-universal.zip`
- `dist/旭影的摄影工具集-macOS-universal.dmg`

默认是本地 ad-hoc 签名。若要对外无警告分发，请准备 Apple Developer ID Application 证书与 `notarytool` 配置：

```bash
APPLE_SIGN_IDENTITY="Developer ID Application: 你的名称 (TEAMID)" \
APPLE_NOTARY_PROFILE="你的-notarytool-profile" \
./build_app.sh
```

## 开发与反馈

- 贡献流程见：[CONTRIBUTING.md](CONTRIBUTING.md)
- 安全问题请按：[SECURITY.md](SECURITY.md) 的方式报告，不要公开照片或可识别的文件路径。
- 提交 Issue 前，请先使用副本复现，并附上脱敏后的操作步骤、系统版本和完整错误文本。

## 版本

当前版本：`1.0.4`

## 开源许可

本项目采用 [MIT License](LICENSE)。你可以在保留版权和许可声明的前提下使用、复制、修改、合并、发布、再授权和销售本项目副本。
