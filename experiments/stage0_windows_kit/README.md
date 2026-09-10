# 阶段 0 Windows 验证工具包

把本目录复制到 Windows 10/11 x64 后，双击 `双击运行阶段0测试.cmd`。工具包只使用当前目录的 `.venv`，不会安装 Python、Visual Studio 或其它系统软件。

## 使用

1. 将待测试的 JPG 放入 `input/real/`。
2. 修改 `keyword.txt`（默认关键词为 `AGI`）。
3. 双击 `双击运行阶段0测试.cmd`。
4. 等待依赖下载、21 张 OCR 与两种打包完成。
5. 把整个 `results/` 文件夹复制回 Mac。

需要 Windows x64 的 Python 3.12 和网络。`pyside6-deploy` 还可能需要 Visual Studio Build Tools 的 `dumpbin`；脚本只检查和记录，不会自动安装。

缺少 Windows.Media.Ocr、中文语言包、包身份或某项依赖时，会记录 `failed`/`skipped`，不会阻止其它项目继续执行。真实截图、结果、虚拟环境和构建目录都已加入 `.gitignore`，避免误提交。
