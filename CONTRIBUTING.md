# 参与开发

提交修改前，请先阅读 [AGENTS.md](AGENTS.md) 与 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)，并保持现有文件安全语义和分层边界。

## 本地环境

需要 Python 3.12、`uv`、Qt/PySide6；macOS 原生能力还需要 Xcode Command Line Tools。

```bash
uv sync --locked --group dev
./scripts/test.sh
```

启动开发版：

```bash
./scripts/run-macos.sh
```

## 提交要求

- 不提交真实照片、私有路径、密钥、构建目录或发布二进制。
- 批量文件操作必须保留预览、确认、冲突拦截、回滚与撤回语义。
- 新增或修改代码时补充相应测试；代码注释使用中文。
- 提交前至少运行相关测试、QML 静态检查和 `git diff --check`。
