# 关键词对齐器

一款离线运行的 macOS 批量截图关键词对齐工具。导入截图并输入关键词后，软件会使用 Apple Vision OCR 找到靠近画面中心的匹配文字，统一它在画布中的位置和大小，再导出处理后 PNG、逐帧 PNG 或无声 MP4。

## 本地运行

```bash
swift run KeywordAlignerApp
```

## 测试

```bash
swift test
```

## 打包

```bash
./scripts/build-app.sh
```

打包产物位于 `dist/关键词对齐器.app`。

## 实现原理

详细技术说明见 [`关键词对齐器-实现原理说明.md`](./关键词对齐器-实现原理说明.md)。
