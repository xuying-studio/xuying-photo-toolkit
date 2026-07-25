# 贡献指南

感谢你关注“旭影的摄影工具集”。提交问题或代码前，请先阅读以下约定。

## 开发环境

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 main.py
```

项目以 Python 标准库、Tkinter、`exifread` 和 `Send2Trash` 为基础；macOS App 通过 PyInstaller 构建。

## 提交原则

- 不要提交真实照片、真实文件路径、备份清单、废纸篓记录或任何隐私元数据。
- 功能变更应补充或更新测试；界面变更应确认原有按钮命令和页面流程未丢失。
- 文件操作必须先扫描和预览，再执行；不得引入静默覆盖或永久删除。
- RAW 原始文件不得被直接修改；元数据写入应使用 XMP 侧车。
- 代码注释、界面文案和文档优先使用中文。

## 提交前检查

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q photo_assistant tests
bash -n build_app.sh
```

## Issue 建议格式

请包含：应用版本、macOS 版本、复现步骤、期望结果、实际结果和完整错误文本。若涉及文件名，请使用虚构或脱敏示例。
