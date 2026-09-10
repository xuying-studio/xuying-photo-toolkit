# 第三方软件与许可证说明

本文件对应旭影工具箱 `2.0.0-rc.1` 的 macOS arm64 内部候选包。它用于记录软件来源和再分发材料，不替代正式法律意见。

| 组件 | 版本 | 用途 | 本包采用的许可证路径 |
| --- | --- | --- | --- |
| CPython | 3.12.1 | Python 运行时 | PSF License |
| PySide6 / Qt for Python | 6.11.2 | Qt Python 绑定 | LGPL-3.0-only |
| PySide6 Essentials / Addons | 6.11.2 | Qt/QML 运行库 | LGPL-3.0-only |
| Shiboken6 | 6.11.2 | PySide6 运行时 | LGPL-3.0-only |
| ExifRead | 3.5.1 | 只读 EXIF 元数据 | BSD-3-Clause |
| Send2Trash | 1.8.3 | 移入系统废纸篓 | BSD 类许可证 |
| FFmpeg | 9.0.1 | PNG 帧转无声 MP4 | LGPL-2.1-or-later |
| PyInstaller | 6.22.2 | 仅构建发布包 | GPL-2.0-or-later + Bootloader Exception |

## FFmpeg 构建边界

- 源码固定为 FFmpeg 官方 `ffmpeg-9.0.1.tar.xz`，发布目录同时提供源码包、官方签名文件、SHA-256 和完整构建参数。
- 构建参数不含 `--enable-gpl`、`--enable-nonfree`、libx264 或其他第三方编码库。
- 仅保留 PNG 输入、MP4 封装和 macOS `h264_videotoolbox` 编码；网络功能关闭。
- `otool -L` 必须只出现 macOS 系统库和系统 Framework，不得链接 `/opt/homebrew` 或 `/usr/local`。

## PySide6 / Qt 再链接说明

Qt 与 PySide6 以动态 Framework / 动态库随 App 提供，没有静态链接进旭影工具箱业务代码。用户可以用同版本、接口兼容的 LGPL 构建替换这些库并重新签名 App；本项目不限制为调试这些库而进行的逆向工程。

对应许可证原文放在 App 的 `Contents/Resources/licenses/`，并复制到发布目录的 `licenses/`。精确源码可从以下官方位置获得：

- Qt for Python：<https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.11.2>
- Qt：<https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/>
- FFmpeg：<https://ffmpeg.org/releases/ffmpeg-9.0.1.tar.xz>

正式公开发布前应再次核对实际打包文件、源码可得性和适用于发布主体的法律义务。
