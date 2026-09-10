# PySide6/QML 最小打包验证

## 验证环境

- macOS 26.5.2
- Apple Silicon arm64
- Python 3.12.1
- PySide6 6.11.2
- PyInstaller 6.22.2
- `pyside6-deploy`（随 PySide6 6.11.2）
- Nuitka 4.1.2
- `uv` 0.9.8

验证源位于 `experiments/stage0_qml_packaging/`，只显示一个 Qt Quick Controls 窗口，不含正式业务。

## 结果汇总

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 源码直接启动 | 通过 | 当前 macOS arm64，offscreen 启动退出码 0 |
| QML/Qt Quick Controls 加载 | 通过 | 最小 proof app 的 `rootObjects()` 非空 |
| PyInstaller macOS onedir/App 构建 | 通过 | 最小 proof app 生成 `.app`，构建退出码 0 |
| PyInstaller 打包产物启动 | 通过 | offscreen 与正常 Cocoa 窗口启动退出码均为 0 |
| PyInstaller 签名结构 | 通过 | ad-hoc；`codesign --verify --deep --strict` 返回 0 |
| PyInstaller 体积 | 不合格，待优化 | 418544 KiB，约 408.73 MiB |
| `pyside6-deploy` / Nuitka 最小验证构建 | 通过（非发布验收） | Nuitka 4.1.2 生成 standalone `.app` |
| Nuitka 打包产物启动 | 通过 | offscreen 与正常 Cocoa 窗口启动退出码均为 0 |
| Nuitka 签名结构 | 未通过 | `Main.qml` 子组件未签名，深度校验返回 1 |
| Nuitka 体积 | 不合格，待优化 | 432976 KiB，约 422.83 MiB |
| 两个产物架构 | 通过 | Mach-O 64-bit arm64 |
| QML 资源 | 通过 | 两个 App 均包含 `Main.qml` 与 Qt QML 资源 |
| Windows 构建与启动 | 未执行 | 当前没有 Windows x64 实机/runner |

## PyInstaller 观察

打包产物：

- 实际启动成功，退出码 0。
- 可执行文件是 arm64。
- App 为 ad-hoc 签名，符合本地技术验证，但不代表可发布。
- 最小程序体积约 408.73 MiB。
- 产物包含大量未使用的 Qt Quick 3D、ParticleEffects 等 QML 资源。
- 构建日志还提示一个未使用的 `qmlassetdownloaderprivateplugin` 二进制不存在；本次应用仍可启动，但正式打包必须消除或解释该警告。
- ad-hoc 签名结构可通过深度严格校验，但没有 Developer ID 签名和公证。

结论：在当前两条路线中，PyInstaller 证据更完整，可作为阶段 1 的候选主路径；默认收集策略仍不适合直接发布。

## `pyside6-deploy` 观察

Qt 官方 `pyside6-deploy` 会调用 QML import scanner，并在 macOS 上使用 `dyld_info` 分析 Qt 模块依赖。安装更新后的 Command Line Tools 后，`dyld_info` 已能正确读取 Qt framework，最初的工具链阻塞解除。

第一次正式构建使用默认 Nuitka 4.1.1 时，命中了已知的 macOS 静态 QML 库错误：

```text
FATAL: ... libqmlassetdownloaderprivateplugin.a(mocs_compilation.cpp.o) ...
```

Nuitka 官方 issue `#3899` 说明该问题在 4.1.2 hotfix 修复。把临时验证环境升级到 4.1.2 后，`pyside6-deploy` 成功生成 App，offscreen 与正常窗口启动均返回 0。

新的实测问题：

- 最小 App 约 422.83 MiB，比本轮 PyInstaller 大约 14.10 MiB。
- 自动生成的排除项没有阻止 Quick3D、WebEngine 等未用模块进入最终 App。
- 产物主可执行文件为 arm64、带 ad-hoc 信息，但 `codesign --verify --deep --strict` 因 `Main.qml` 子组件返回 1。
- 完整 Xcode 26.6 已可用；7 个 Core 原测试通过，但旧完整 Swift Package 仍有 Vision/Swift 6.3 UI 编译冲突。Developer ID 签名与公证尚未执行。

结论：官方路线的“构建 + 启动”链路已经通过，但当前版本组合在体积、插件裁剪、版本固定和签名结构上没有优于 PyInstaller。

## 建议

1. 阶段 1 候选主路径调整为 PyInstaller onedir；`pyside6-deploy` / Nuitka 保留为对照路径。
2. 两条路线都必须建立 QML 模块白名单/排除清单，先把最小包体积降到合理范围。
3. 不优先 onefile：照片工具需要可预测地收集 QML、平台插件、OCR 模型、FFmpeg 和许可证，onedir 更容易检查。
4. 若继续 Nuitka，至少固定 4.1.2 或更新的已修复版本，并补上完整 App 重签名步骤。
5. 正式包验证必须覆盖：全新账户、无 Python 环境、断网、中文路径、外置盘、签名、Gatekeeper、安装包内容和 SHA-256。
6. Windows 上必须分别验证 Inno Setup 安装版与便携 ZIP，不能用“构建成功”替代“产物启动成功”。

## 复现命令

源码启动：

```bash
QT_QPA_PLATFORM=offscreen QML_PROOF_AUTO_QUIT_MS=300 python main.py
```

PyInstaller 验证：

```bash
pyinstaller --noconfirm --clean --windowed --onedir \
  --name XuyingStage0Proof --add-data 'Main.qml:.' main.py
```

Qt 官方工具验证时，虚拟环境要放在源码目录外，并使用已修复的 Nuitka：

```bash
python -m pip install 'Nuitka==4.1.2'
pyside6-deploy main.py --name XuyingStage0Proof --mode standalone
```

机器可读结果：`experiments/stage0_qml_packaging/results/macos-arm64.json`。

## 官方资料

- Qt for Python deployment：<https://doc.qt.io/qtforpython-6/deployment/index.html>
- `pyside6-deploy`：<https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html>
- Qt for Python 与 PyInstaller：<https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html>
- Nuitka 静态 QML 库修复：<https://github.com/Nuitka/Nuitka/issues/3899>
