# CUAgent

CUAgent 的开发主线是**通用且更强的 Computer Use**：先基于 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 跑通最小可用 Agent，马上进入真实电脑观察、操作与独立验证。三份文本、CSV和完整通用插件体验不阻塞 Computer Use；OS 原生能力最后按需要扩展。2026-09-30 起交互入口改为官方 macOS Desktop App；继续复用模型接入、会话与 Agent 循环。

**当前使用官方 Desktop App；此前 A0 Web 验收保留为历史。C0-01、C0-02、C1、C2 本地阶段已完成；C2 新正式评测 18/18、七故障、九计算器和 A0 回归通过。** 具体证据与限制见 [PROGRESS](PROGRESS.md) 和 [C2 总结](docs/stages/c2-summary.md)。这不是 C3 发布/第二人复现，Pi 的历史通过记录不计入 Harness 验收。

## 当前进度

后续按 [个人任务服务路线](docs/product-roadmap.md) 推进：P1 日报 → P2 后端/日志 → P3 长任务 → P4 效率 → P5 日常用途。目前进入 `p1-daily-report`，先写 [技术方案](docs/stages/p1-design.md)，实现和真实 20 组评测尚未完成。

- [x] 切换主基座为 DeepSeek Harness；创建公开仓库 `9leaa/CUAgent`。
- [x] 迁移工具核心、测试、CSV fixture、图片探针和历史 VM 回归资产。
- [x] 重写整体设计与阶段计划；开发顺序调整为最小底座→Computer Use主线。
- [x] A0：官方 Desktop 专用配置下，真实模型/会话、受控文件、直接与工具图片、标准取消及 30 次持久预算回归通过；重启首回复错误及后续澄清保留，见 C2 总结。旧 Web 验收仅作历史。
- [x] C0-01：真实模型在测试 VM 中完成计算器12×34，轨迹、新显示、文件读回和独立期望值闭环通过（20/30 raw 调用，见阶段总结）。
- [x] C0-02：真实观察驱动计算器九例和三个基础界面任务（失败保留，见阶段总结）。
- [x] C1：六类前后各三次，36/36 独立通过，见 [阶段总结](docs/stages/c1-summary.md)。
- [x] C2：七故障、正式 18/18、九计算器、A0 和声明范围内安全回归通过，见 [阶段总结](docs/stages/c2-summary.md)。
- [ ] C3：第二位开发者能部署、扩展和复现 Computer Use 任务；用户指定暂时跳过，仍未完成。
- [x] A1 本地部分：三文本/CSV、通用插件与会话、安全及真实 VM 回归通过，见 [本地总结](docs/stages/a1-summary.md)；第二人验收按用户确认暂缓、未验。
- [x] 单人真实应用小任务：VM TextEdit 输入、保存、结果读回独立通过；结束后在线重观察失败单独保留，见 [总结与限制](docs/stages/real-app-summary.md)。不算 C3 或广泛泛化。
- [ ] O0：按真实用例另行增加系统原生接口。

A1 新真实三文本与 CSV 业务、重启续接、手动压缩、首轮前 preset 切换、两种图片、标准取消和跨重启预算拒绝已独立通过，见 [业务阶段记录](docs/stages/a1-business-progress.md)。核心测试 59/59、同版官方工具注册集成 25/25；当前 App 使用 A1 配置，文本/CSV/只读任务预算为 10/30、30/30、1/30，CSV 已耗尽。已提供[受控插件示例](docs/stages/a1-plugin-extension.md)和[等效流程](docs/stages/a1-controlled-workflow.md)；新真实 C0 计算器、安全能力拒绝、VM 持久预算与在途停止回归已独立通过，A1 本地部分完成。第二人独立扩展按用户确认暂缓、未验，不算通过；C3 继续跳过。

详细结果见 [PROGRESS](PROGRESS.md)。旧仓库 `9leaa/os_agent` 已归档；旧本地源码和Pi安装已按用户要求移至废纸篓。VM、镜像和原始证据仍保留在旧环境目录，不迁移到Git。

## 阅读与开发入口

最新无模型回归为核心 59/59、官方注册集成 26/26、Python 123/123；原 A1 总结保留当时测试数量。当前仍为 A1 配置，本次独立任务 executor 已退出，旧预算未变。2026-10-02 用户授权逐阶段验证后提交推送；A1 与 TextEdit 分别保存在 `a1-agent-expansion`、`real-app-textedit`，历史“未提交”说明保留当时状态。

| 文档 | 用途 |
|---|---|
| [整体设计](DESIGN.md) | 组件、边界、插件接入、状态与验证 |
| [开发计划书](Harness_Development_Plan.md) | 各阶段任务、依赖和验收条件 |
| [协作说明](COLLABORATION.md) | 两人分工、阶段分支与 VM 调试 |
| [迁移清单](MIGRATION.md) | 所有旧方案如何承接、哪些实现复用 |
| [开发规则](AGENTS.md) | 后续代理必须遵循的范围 |
| [Harness 接入说明](agent/harness/README.md) | 固定版本、Desktop 配置、工具适配及启动限制 |

本地项目目录：`/Users/zhangchengjie/CUAgent`。GitHub 默认分支为 `harness-migration`，本次按用户授权快进同步 C0-01 → C0-02 → C1 → C2 及文档修正；不创建 PR、标签或发布版本。四个阶段分支保留，后续提交和发布仍需维护者授权。

| 阶段分支 | 对应内容 |
|---|---|
| `c0-01-computer-use` | 单例计算器闭环、方案和总结 |
| `c0-02-fixed-ui` | 九计算器及三个基础 GUI 用例 |
| `c1-computer-use` | 六类增强和前后 36 次评测 |
| `c2-reliability` | 接管/恢复、故障与回归、当前文档 |

现有测试无需安装 Harness、配置 API Key 或启动 VM：

```bash
cd /Users/zhangchengjie/CUAgent
node --test agent/tests/*.test.mjs
python3 -m unittest discover -s tools/mac_vm/tests -v
```

这两条命令仅验证工具核心和执行层单元/mock，不调用模型或控制桌面，也不替代真实 VM 验收。当前已验收入口为官方 **DeepSeek Harness.app 0.2.0-rc.2（macOS arm64）**，安装于 `/Applications/DeepSeek Harness.app`。按 [接入说明](agent/harness/README.md) 完成构建和 A0 配置、正常退出已有 App 后，A0 项目启动命令：

```bash
/bin/zsh /Users/zhangchengjie/CUAgent/agent/harness/start-desktop.sh
```

该入口使用独立 `.runtime/desktop-home`，不复制旧 Web 凭证或会话；项目插件从保留源码重新编译。Finder 直接启动应用使用应用默认 home，与本项目入口不同。旧 Web 的源码、依赖、home 和启动配置已移至 `/Users/zhangchengjie/Documents/ChatGPT/osagentmvp/retired-dsh-web-20260930`，恢复清单在该目录的 `archive-manifest.json`；任务证据仍保留。此前 A0 Web 验收属于历史，不能计入 Desktop 验收。Desktop A0 已按同版本接口重新接入并真实验证，配置和编译步骤见 agent/harness/README.md；C0 真实桌面仍须在测试 VM 中执行。

Computer Use 使用对应 VM bridge、明确任务审批、私有连接和 C0/C1/C2 配置，再由 `start-c0-desktop.sh <run-id>` 启动；A0 启动命令不授予桌面权限。旧回归 run 已耗尽预算，新任务必须新建 run，不能清零旧账本。其他机器的干净部署和第二人复现属于尚未完成的 C3。

2026-10-01：C0-01、C0-02、C1、C2 独立通过，见 [C0-01 总结](docs/stages/c0-01-summary.md)、[C0-02 总结](docs/stages/c0-02-summary.md)、[C1 总结](docs/stages/c1-summary.md) 和 [C2 总结](docs/stages/c2-summary.md)。四阶段递进提交已分别推送；2026-10-02 按用户授权将最新阶段和文档快进同步至默认分支，不将固定用例算作通用 Computer Use 或 C3 发布完成。

## 目录

```text
agent/
  workspace-*.mjs         # 已迁移的框架无关文件/CSV核心
  image-probe.mjs         # 图片探针编码与随机四色测试数据
  tests/                 # 核心边界测试
  fixtures/              # 无凭证测试输入
  harness/               # Desktop 配置、受控插件、启动脚本和接入说明
tools/mac_vm/            # C0/C1/C2 执行器、固定任务、验证器、fixture及单元/mock
patches/cua/             # 固定上游的Lume隔离补丁和MIT许可证
patches/harness/         # 固定Harness版本的插件元数据异常补丁
docs/history/            # 明确标记为历史的验收摘要
docs/stages/             # 各阶段实施前方案、完成总结与已知限制
migration-assets.json    # 原字节迁移文件及SHA-256
vm-manifest.json         # 历史VM声明，不是当前运行状态
```

Harness 的“插件”“审批”“沙箱”分别是扩展机制、用户决定和执行限制；它们不自动满足本项目的目录、桌面和调用预算边界。开发者预览版可能破坏兼容性，版本与有效配置必须固定。
