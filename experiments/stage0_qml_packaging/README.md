# 阶段 0：PySide6/QML 最小打包验证

该目录只包含技术验证程序，不是正式产品代码。它用于确认：

- Python 可以加载 Qt Quick/QML 与 Qt Quick Controls。
- 打包工具会收集实际使用的 QML 插件。
- 打包产物可以脱离开发入口启动并正常退出。

`pyproject.toml` 只列出本实验的两个源文件，防止部署工具把临时虚拟环境误当成应用数据。

构建产物、虚拟环境和 `pysidedeploy.spec` 必须放在仓库外的临时目录，不提交到项目。

## 当前 macOS 结论

- PyInstaller 6.22.2：最小 App 可启动，约 408.73 MiB，深度签名结构校验通过。
- `pyside6-deploy`：需把 Nuitka 从默认 4.1.1 升至包含静态 QML 库修复的 4.1.2；最小 App 可启动，约 422.83 MiB，但深度签名结构校验失败。
- 两种方案都收集了未使用的 QML 模块，当前产物只可作为链路证明，不可发布。

完整机器结果见 `results/macos-arm64.json`。
