# Windows 阶段 0 测试交接

## 已生成的文件

- 本机路径：`~/Desktop/旭影阶段0-Windows测试包.zip`
- SHA-256：`11b67cf50a8b3201f844cb5caefc2e9604eb85a75640e41619d0e0bd1c3cfcdf`
- 压缩包大小：约 3.6 MiB
- 图片：21 张用户授权 JPG，SHA-256 全部不同
- 默认关键词：`AGI`（依据截图内容推定，可编辑 `keyword.txt`）
- Mac 基线：Apple Vision 与 RapidOCR 的完整本地 JSON

真实截图和完整识别文本只存在于这个私有交接包，没有写入 Git。

## 在 Windows 上操作

1. 把 ZIP 拷到 Windows 10/11 x64 并完整解压。
2. 确认已经安装 Windows x64 Python 3.12，并保持联网。
3. 双击 `双击运行阶段0测试.cmd`。
4. 测试期间会短暂出现两个 QML 窗口并自动关闭。
5. 完成后把整个 `results/` 文件夹复制回 Mac。

脚本只在解压目录内创建 `.venv`、`work` 与 `results`，不会自动安装 Python、Visual Studio、语言包或其它系统软件。

## 应生成的结果

- `results/summary.json`
- `results/ocr-rapidocr.json`
- `results/ocr-windows-media.json`
- `results/pip-install.log`
- `results/pywinrt-install.log`
- `results/pyinstaller.log`
- `results/pyside6-deploy.log`

`summary.json` 会记录两个 OCR 后端的状态，以及两种 QML 打包方案的构建退出码、启动退出码和包体积。

## 允许失败的项目

- `Windows.Media.Ocr` 可能因简体中文语言包或桌面包身份要求失败；错误会写入 JSON。
- `pyside6-deploy` 可能因缺少 Visual Studio Build Tools 的 `dumpbin` 失败；脚本不会自动安装。
- 任一项目失败不会抹掉已经完成的其它结果。

## 结果返回后的验收

收到 `results/` 后需要按图片 SHA-256 对齐三组结果：Apple Vision、Windows.Media.Ocr、RapidOCR。最终比较 21/21 命中率、候选总数、中心候选位置、平均耗时、包体积和离线首次运行能力，再锁定 Windows OCR 与打包主路径。
