# CUAgent

CUAgent 的开发主线是**通用且更强的 Computer Use**：先基于 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 跑通最小可用 Agent，马上进入真实电脑观察、操作与独立验证。三份文本、CSV和完整通用插件体验不阻塞 Computer Use；OS 原生能力最后按需要扩展。复用官方 Web UI、模型接入、会话与 Agent 循环。

**当前本地 A0 已有独立 Web profile、真实模型/会话/工具/两种图片链路及最低安全控制的验收记录；尚未开始 C0 真实桌面操作。** 具体证据与限制见 [PROGRESS](PROGRESS.md)。Pi 的历史通过记录不计入 Harness 验收。

## 当前进度

- [x] 切换主基座为 DeepSeek Harness；创建公开仓库 `9leaa/CUAgent`。
- [x] 迁移工具核心、测试、CSV fixture、图片探针和历史 VM 回归资产。
- [x] 重写整体设计与阶段计划；开发顺序调整为最小底座→Computer Use主线。
- [x] A0：独立 Web profile 中真实模型、会话、简单受控工具、图片和最低执行边界通过（Web 停止按钮在先前同策略隔离实例人工验收；正式 profile 未重复点击）。
- [ ] C0-01：真实模型在测试 VM 中完成计算器12×34，轨迹、新显示、文件读回和独立期望值闭环通过。
- [ ] C0-02：真实观察驱动计算器九例和三个基础界面任务。
- [ ] C1：长流程、弹窗、窗口变化与跨应用任务。
- [ ] C2：人工接管、异常恢复和固定任务集评测。
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

这两条命令仅验证工具核心与历史 mock。Harness 已安装到 `.runtime/harness`（0.1.7-alpha.2）；A0 的正式启动入口是 `agent/harness/start-a0-web.sh <run-id> [port]`，实际验证见 [接入说明](agent/harness/README.md)。后续重编译须使用接入说明中的原生 ARM64 命令。下一步是 **C0-01 真实 Computer Use 闭环**；VM 桌面动作的窗口白名单、逐项授权与独立观察仍须先实现，不能用 A0 文件工具边界代替。

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
