# CUAgent

CUAgent 的开发主线是**通用且更强的 Computer Use**：先基于 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 跑通最小可用 Agent，马上进入真实电脑观察、操作与独立验证。三份文本、CSV和完整通用插件体验不阻塞 Computer Use；OS 原生能力最后按需要扩展。2026-09-30 起交互入口改为官方 macOS Desktop App；继续复用模型接入、会话与 Agent 循环。

**当前使用官方 Desktop App；此前 A0 Web 验收保留为历史。C0-01、C0-02、C1、C2 本地阶段已完成；C2 新正式评测 18/18、七故障、九计算器和 A0 回归通过。** 具体证据与限制见 [PROGRESS](PROGRESS.md) 和 [C2 总结](docs/stages/c2-summary.md)。这不是 C3 发布/第二人复现，Pi 的历史通过记录不计入 Harness 验收。

## 当前进度

按 [个人任务服务路线](docs/product-roadmap.md) 推进：P1 日报 → P2 后端/日志 → P3 长任务 → P4 效率 → P5 日常用途。P1、P2 已完成并推送，当前验证 P3，P4/P5 尚未开始。P1 先写 [技术方案](docs/stages/p1-design.md)，两轮真实模型对照首轮17/20、修正后新轮次20/20，失败保留；见 [使用方法](docs/stages/p1-usage.md) 和 [结果](docs/stages/p1-summary.md)。

后续 DSH 推理按用户指定固定 **DeepSeek 4.1 Flash，思考关闭**：当前 App 路由 `deepseek-account/deepseek-flash`、`reasoningEffort=off`。旧阶段 high 的记录保留为历史，不再沿用。

P2 `6bd8c4a` 已推送阶段和默认分支：先写 [后端技术方案](docs/stages/p2-design.md)，通过 API→数据库→独立 Worker→真实 Flash/off→核对→下载闭环。提供提交、查询、停止、有限恢复、工具日志和用量；见 [使用](backend/README.md)、[验证与限制](docs/stages/p2-summary.md)。当前新分支 `p3-durable-execution`，已根据 P2 实际断点重写 [P3 恢复与长运行方案](docs/stages/p3-design.md)，尚未验收。

P3 最终审计中：数据库检查点、原请求只读核对、有限观察重试、同会话续接及持久无进展检测已实现。后端71/71、核心64/64、官方注册31/31、Python日报验收13/13。1小时、8小时及声明范围内故障测试通过；阶段尚未推送，默认分支仍保持已验收P2。

| 真实中断点 | 当前证据 |
|---|---|
| 完成但未登记成功 | 原会话/文件/日志不变，10/30，恢复无新增推理 |
| 创建会话但未发送提示 | 同一会话核对后仅发送一次，10/30 |
| 已接收提示但确认丢失 | 原请求匹配、未重发，9/30 |
| 已写 JSON，缺 Markdown | 新任务恢复 5→9/30，原 JSON 不变，补齐并完整读回，API SUCCEEDED、下载 SHA 一致 |

部分产物首试因停止原因分类遗漏而保留 UNVERIFIED；修正后新任务完整闭环通过，未改写首试历史。P1 单轮规则不变；续接必须绑定原会话/账本前缀、无未返回调用、原文件与独立期望一致、预算连续。详细失败、原始证据位置和各次提交见 [PROGRESS](PROGRESS.md)。

长时间用例“草稿→等待发布时间→同会话最终发布”已接通提交入口、WAITING_RELEASE、到期领取和工具端门禁；提前渲染及普通写Markdown绕过均拒绝。先完成约97秒、6→10/30的短时间闭环，再依次执行下方1小时及8小时门槛，不用短测试代替。

1小时实测已通过：`6757af50-e903-467b-aea1-e4ada4be5fcf` 实际观察3659.080秒、243次采样，同session到期发布，6→10/30、18011 token，独立verify与API SUCCEEDED一致；等待证据不变，最大采样间隔15.170秒，API/Worker实际重启。首个长测因模型漏写CSV path被拦截，原失败和费用保留。

8小时实测已通过：`9295c25e-a411-4d6e-9d39-2992fe6a089b` 实际28863.758秒、1912次采样，1910份等待快照完全一致，最大采样间隔15.304秒。API/Worker在等待期间实际重启；到期后原session续接，6→10/30、19591 token、Flash/off。重新独立核验、当前API状态及两产物下载SHA一致，基础配置恢复记录齐全。此项证明定时业务等待后的持久恢复，不代表连续推理8小时；P3尚待最终审计与阶段推送。

无进展保护新完整轮次已通过：冻结观测后真实302.374秒触发停止，先关闭工具派发、再重新查询；实际会话已结束，因此不重复取消或推理。任务STOPPED、10/30，产物下载拒绝；这是观测停滞故障，不冒充模型挂起。早期测试计时及盲目取消失败仍保留。另补丢失执行权时立即撤销本地许可及旧owner不能撤销新owner；后端44/44。

配置已激活但尚未创建会话的断点新增有限恢复：无执行意图、空审计、无产物且实时确认原会话不存在时，才重新绑定配置；前后证据变化则拒绝。真实首试因模型漏CSV path保留UNVERIFIED（17/30）；明确新任务的完整字段提示后，新故障轮次同任务恢复、仅一条提示、10/30，独立产物核对与API下载通过。

只读RPC故障注入通过：本地故意丢弃两次真实查询响应，Worker按1/2秒退避，第三次查回原会话；原提示、账本和产物SHA不变，没有新增推理。不代表共享网络断网或写操作可重试。

完整门槛见 [P3 验收核对](docs/stages/p3-acceptance-audit.md)：小时级测试、生命周期剩余反例与最终交付分别核对，不以短测数量代替阶段完成。

最新后端71/71：新增Worker整流程检查未知请求不重发、原续接不重复、未启动会话核对及清理失败留证。清理告警目前在Worker日志/私有run记录，不在API状态单独显示；业务成功不等于配置恢复成功，操作限制见 [后端说明](backend/README.md)。

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
- [x] P1 日报：指定记录＋CSV → 来源可核对的 JSON/Markdown 报告，固定新输入 20/20 通过。
- [x] P2 任务后端与日志：两次真实闭环、API 重启保留任务、工具审计和独立下载核对。
- [ ] P3 长任务；P4 效率；P5 实际用途与一周使用。
- [ ] O0：按真实用例另行增加系统原生接口。

A1 新真实三文本与 CSV 业务、重启续接、手动压缩、首轮前 preset 切换、两种图片、标准取消和跨重启预算拒绝已独立通过，见 [业务阶段记录](docs/stages/a1-business-progress.md)。核心测试 59/59、同版官方工具注册集成 25/25；当前 App 使用 A1 配置，文本/CSV/只读任务预算为 10/30、30/30、1/30，CSV 已耗尽。已提供[受控插件示例](docs/stages/a1-plugin-extension.md)和[等效流程](docs/stages/a1-controlled-workflow.md)；新真实 C0 计算器、安全能力拒绝、VM 持久预算与在途停止回归已独立通过，A1 本地部分完成。第二人独立扩展按用户确认暂缓、未验，不算通过；C3 继续跳过。

详细结果见 [PROGRESS](PROGRESS.md)。旧仓库 `9leaa/os_agent` 已归档；旧本地源码和Pi安装已按用户要求移至废纸篓。VM、镜像和原始证据仍保留在旧环境目录，不迁移到Git。

## 阅读与开发入口

最新本地无模型回归：核心64/64、官方注册集成31/31、Python日报13/13、后端71/71。VM Python最近记录为123/123，本轮P3未重跑真实VM；旧总结保留当时测试数量。用户授权逐阶段验证后提交推送；历史“未提交”说明保留当时状态。

| 文档 | 用途 |
|---|---|
| [整体设计](DESIGN.md) | 组件、边界、插件接入、状态与验证 |
| [开发计划书](Harness_Development_Plan.md) | 各阶段任务、依赖和验收条件 |
| [协作说明](COLLABORATION.md) | 两人分工、阶段分支与 VM 调试 |
| [迁移清单](MIGRATION.md) | 所有旧方案如何承接、哪些实现复用 |
| [开发规则](AGENTS.md) | 后续代理必须遵循的范围 |
| [Harness 接入说明](agent/harness/README.md) | 固定版本、Desktop 配置、工具适配及启动限制 |

本地项目目录：`/Users/zhangchengjie/CUAgent`。GitHub 默认分支为 `harness-migration`，按用户本次授权将验证后的阶段代码及 README 快进同步；各阶段分支保留。当前交付到 P2，不创建 PR、标签或发布版本。

| 阶段分支 | 对应内容 |
|---|---|
| `c0-01-computer-use` | 单例计算器闭环、方案和总结 |
| `c0-02-fixed-ui` | 九计算器及三个基础 GUI 用例 |
| `c1-computer-use` | 六类增强和前后 36 次评测 |
| `c2-reliability` | 接管/恢复、故障与回归、当前文档 |
| `a1-agent-expansion` | A1 文件/CSV、插件与会话、本地验收 |
| `real-app-textedit` | 单人真实 TextEdit 闭环与限制 |
| `p1-daily-report` | 可复用日报、确定性排版与两轮真实对照 |
| `p2-task-service` | 单人持久任务后端、独立 Worker、执行租约与工具日志 |
| `p3-durable-execution` | 本地验证中：持久恢复、定时发布与1/8小时门槛；尚未阶段推送 |

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
