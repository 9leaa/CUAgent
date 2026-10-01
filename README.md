# CUAgent

CUAgent 的开发主线是**通用且更强的 Computer Use**：先基于 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 跑通最小可用 Agent，马上进入真实电脑观察、操作与独立验证。三份文本、CSV和完整通用插件体验不阻塞 Computer Use；OS 原生能力最后按需要扩展。2026-09-30 起交互入口改为官方 macOS Desktop App；继续复用模型接入、会话与 Agent 循环。

**当前使用官方 Desktop App；此前 A0 Web 验收保留为历史。本分支完成 c0-01；后续阶段不计入本分支。**

## 当前进度

- [x] 切换主基座为 DeepSeek Harness；创建公开仓库 `9leaa/CUAgent`。
- [x] 迁移工具核心、测试、CSV fixture、图片探针和历史 VM 回归资产。
- [x] 重写整体设计与阶段计划；开发顺序调整为最小底座→Computer Use主线。
- [x] A0：独立 Web profile 中真实模型、会话、简单受控工具、图片和最低执行边界通过（Web 停止按钮在先前同策略隔离实例人工验收；正式 profile 未重复点击）。
- [ ] C0-01：后续阶段。
- [ ] C0-02：后续阶段。
- [ ] C1：后续阶段。
- [ ] C2：后续阶段。
- [ ] C3：第二位开发者能部署、扩展和复现 Computer Use 任务。
- [ ] A1：三份文本、CSV和通用插件/会话能力补强；不阻塞C0–C3。
- [ ] O0：按真实用例另行增加系统原生接口。

详细结果见 [PROGRESS](PROGRESS.md)。旧仓库 `9leaa/os_agent` 已归档；旧本地源码和Pi安装已按用户要求移至废纸篓。VM、镜像和原始证据仍保留在旧环境目录，不迁移到Git。

## 阅读与开发入口

| 文档 | 用途 |
|---|---|
| [整体设计](DESIGN.md) | 组件、边界、插件接入、状态与验证 |
| [开发计划书](Harness_Development_Plan.md) | 各阶段任务、依赖和验收条件 |
| [协作说明](COLLABORATION.md) | 两人分工、阶段分支与 VM 调试 |
| [迁移清单](MIGRATION.md) | 所有旧方案如何承接、哪些实现复用 |
| [开发规则](AGENTS.md) | 后续代理必须遵循的范围 |
| [Harness 接入说明](agent/harness/README.md) | 固定上游、待实现适配点和启动门槛 |

本地项目目录：`/Users/zhangchengjie/CUAgent`。首次发布分支：`harness-migration`；本次经用户单独授权直接提交、推送，不开 PR。后续仍由维护者决定提交、推送和 PR。

现有测试无需安装 Harness、配置 API Key 或启动 VM：

```bash
cd /Users/zhangchengjie/CUAgent
node --test agent/tests/*.test.mjs
python3 -m unittest discover -s tools/mac_vm/tests -v
```

这两条命令仅验证工具核心与历史 mock。当前交互入口为官方 **DeepSeek Harness.app 0.2.0-rc.2（macOS arm64）**，安装于 `/Applications/DeepSeek Harness.app`。项目启动命令：

```bash
/bin/zsh /Users/zhangchengjie/CUAgent/agent/harness/start-desktop.sh
```

该入口使用独立 `.runtime/desktop-home`，不复制旧 Web 凭证或会话；项目插件从保留源码重新编译。Finder 直接启动应用使用应用默认 home，与本项目入口不同。旧 Web 的源码、依赖、home 和启动配置已移至 `/Users/zhangchengjie/Documents/ChatGPT/osagentmvp/retired-dsh-web-20260930`，恢复清单在该目录的 `archive-manifest.json`；任务证据仍保留。此前 A0 Web 验收属于历史，不能计入 Desktop 验收。Desktop A0 已按同版本接口重新接入并真实验证，配置和编译步骤见 agent/harness/README.md；C0 真实桌面仍须在测试 VM 中执行。

2026-10-01：本分支阶段 c0-01 完成。方案与结果见 [阶段总结](docs/stages/c0-01-summary.md)。这是验收后按用户授权整理的提交，后续 c0-02 和 C3 不计为完成。

## 目录

```text
agent/
  workspace-*.mjs         # 已迁移的框架无关文件/CSV核心
  image-probe.mjs         # 图片探针编码与随机四色测试数据
  tests/                 # 核心边界测试
  fixtures/              # 无凭证测试输入
  harness/               # A0 profile、受控插件、启动脚本和接入说明
tools/mac_vm/            # 历史计算器固定流程、环境诊断与mock
patches/cua/             # 固定上游的Lume隔离补丁和MIT许可证
patches/harness/         # 固定Harness版本的插件元数据异常补丁
docs/history/            # 明确标记为历史的验收摘要
migration-assets.json    # 原字节迁移文件及SHA-256
vm-manifest.json         # 历史VM声明，不是当前运行状态
```

Harness 的“插件”“审批”“沙箱”分别是扩展机制、用户决定和执行限制；它们不自动满足本项目的目录、桌面和调用预算边界。开发者预览版可能破坏兼容性，版本与有效配置必须固定。
