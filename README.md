# 旭影工具箱 QML 跨平台版

这是“旭影工具箱”的下一代重构项目，目前只完成了开发规划和 Agent 约束，尚未开始编写产品代码。

## 已确定的技术方向

- 共享业务核心：Python 3.12
- 跨平台界面：PySide6 + Qt Quick/QML
- macOS：完整动画、转场和原生磨砂材质
- Windows：保持相同功能与布局，默认减少动画并使用稳定的实体背景
- 当前版本只作为功能基线，不在原目录上直接重写

## 参考基线

- 现有源码：`/Users/nerophotographer/VS CODE/把代码封装成app-关键词快切内嵌版`
- GitHub 基线：`xuying-studio/xuying-photo-toolkit`
- 基线版本：`v1.4.0 / build 23`
- 基线提交：`4a287ff57f43b2632861d86607ea0c088793743f`

参考项目在整个重构过程中只允许读取和对照，不允许由本项目 Agent 修改。

## 开始前必须阅读

1. [AGENTS.md](AGENTS.md)
2. [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

## 在新窗口中建议发送的第一句话

> 请完整阅读 AGENTS.md 和 DEVELOPMENT_PLAN.md。先执行阶段 0：只读审计现有 v1.4.0 功能与数据格式，建立功能等价清单和测试迁移清单，不要立刻开发界面。完成审计后向我汇报，等我确认再进入阶段 1。

## 当前状态

- [x] 新项目目录
- [x] 完整开发计划
- [x] Agent 行为约束
- [ ] 现有功能基线审计
- [ ] 工程脚手架
- [ ] 功能迁移
- [ ] QML 界面
- [ ] macOS/Windows 打包
- [ ] v2.0 发布

