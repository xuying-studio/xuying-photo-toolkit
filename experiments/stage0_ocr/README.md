# 阶段 0：Windows OCR 对比实验

本实验使用完全合成、无个人信息的中文图片，给两个候选后端提供相同输入。

## 生成夹具

```bash
uv run --with Pillow python generate_fixtures.py
```

## RapidOCR

```bash
uv run --with rapidocr --with onnxruntime python benchmark_rapidocr.py
```

## Windows.Media.Ocr

仅在 Windows 10/11 x64 上执行：

```powershell
uv run --with winrt-runtime --with winrt-Windows.Foundation --with winrt-Windows.Globalization --with winrt-Windows.Graphics.Imaging --with winrt-Windows.Media.Ocr --with winrt-Windows.Storage.Streams python benchmark_windows_media_ocr.py
```

Windows 原生 OCR 需要系统已经安装简体中文 OCR 语言包。根据当前引用的微软文档，桌面发布形态还涉及 MSIX 包身份；该要求必须在目标 Windows 版本中核对，并用最终的 Inno Setup 与便携 ZIP 形态分别实测可用性。

这组图片只能证明技术链路和基本识别能力。最终选型前，仍需在已脱敏的 21 张真实关键词截图上复测识别率、候选框位置、冷启动和连续处理耗时。

## 真实截图关键词基线

RapidOCR：

```bash
uv run --with rapidocr --with onnxruntime \
  python benchmark_keyword_rapidocr.py /path/to/screenshots \
  --keyword AGI --output /tmp/rapidocr-real.json
```

Apple Vision：

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcrun swift benchmark_keyword_vision.swift \
  /path/to/screenshots AGI /tmp/vision-real.json
```

真实截图与结果文件默认只留在本地临时目录或交付测试包中，不提交到 Git。
