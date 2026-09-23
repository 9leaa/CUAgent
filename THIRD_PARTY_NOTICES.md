# 来源与许可

## DeepSeek Harness

新基座为 [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)，设计参考commit见 [版本记录](agent/harness/upstream-reference.json)。官方采用MIT；本仓库本轮没有复制Harness实现，也没有安装其运行依赖。后续分发构建产物时保留该固定版本LICENSE与THIRD_PARTY_NOTICES及依赖许可。

## Cua / Lume

`patches/cua/lume-host-isolation.patch`包含基于Cua源码的上下文与项目修改，基点 `9bbfa7dd3e27ca7f1861ede70aaca390174493f9`。完整原许可证保留在 [patches/cua/LICENSE.md](patches/cua/LICENSE.md)，重建与来源见同目录README。

`tools/mac_vm/`三个Python文件是本项目历史计算器实现，曾位于Cua样例目录。原字节与迁移来源记录在 [migration-assets.json](migration-assets.json)；不代表复制了整个Cua SDK。

## Pi 与 UFO 历史参考

Pi 0.86.1的历史验收摘要仅作为过程记录，框架及注册层未作为CUAgent运行代码迁入。UFO commit `be75a7ded2ad98d97819e15ff1b39d4202ac3ac5`只参考职责、状态与验证设计，未在本次迁移其执行代码或建立运行依赖。

## 项目自有代码

本轮未替维护者选择新的自有代码许可证；公开仓库不自动改变其许可。正式C3发布前由维护者明确自有代码许可证，并与保留的第三方许可一起发布。
