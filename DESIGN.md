# CUAgent 整体设计

版本：v1.2，更新 2026-10-02。状态：A0 Desktop、C0-01/C0-02/C1/C2 和 A1 本地部分已验收；C3/所有第二人验收按用户要求暂缓、未验，O0 未做。本文描述现有架构与后续约束，不将历史设计稿或固定测试当通用能力证明。主基座为 DeepSeek Harness，不并行维护 Pi 运行时。

## 1. 产品目标与职责

目标是通用且更强的 Computer Use Agent。2026-09-30 起用官方 macOS Desktop App 交付能对话、续接、真实调工具和处理图片的**最小可用Harness底座**，随后优先接入屏幕观察、目标定位、执行动作和独立验证；完整文件/CSV业务流程及通用插件体验不挡在首个Computer Use闭环前。macOS 是第一套桌面测试后端，跨 OS 不作为已有能力。

| 组件 | 专业职责 | 直白解释 |
|---|---|---|
| Harness | 模型适配、Agent loop、会话、官方 Desktop UI、插件生命周期 | 提供可用 Agent 的主体 |
| 项目插件 | 注册受控工具、接入执行策略、输出可展示结果 | 给主体增加我们要的能力 |
| 工具核心 / 执行器 | 路径、目标、参数、调用上限、停止检查 | 真正检查能不能执行 |
| Cua Driver + 测试 VM | 桌面观察、AX 与输入动作、环境隔离 | 在测试电脑里操作 |
| 独立验证器 | 核对轨迹、实际界面、产物及期望值 | 判断任务到底有没有完成 |

专业架构为“单 Agent 运行时 + 受控执行 + 独立验证”。直白说：复用 Harness 管连续工作，我们负责电脑操作及结果可信度。

```text
用户 → 官方 Desktop App → Harness 会话 / Agent 循环 → 模型
                            ↓ 结构化工具调用
                     项目插件 / 统一执行策略
                       ├─ 最小受控文件工具（CSV等通用扩展在A1）
                       └─ Computer Use适配 → Cua Driver → 测试VM
                            ↓ 轨迹、观察、产物
                     独立验证器 → 项目任务状态 → Desktop结果
```

Agent 循环只保留 Harness 一套；不额外套第二套主循环。Cua 是执行后端，Harness 是运行时，两者不是替代关系。AX、截图和原生输入按可靠性组合，不以“接原生接口”为名扩大到任意 OS 操作。

## 2. 上游与版本

当前验收固定到官方 Desktop App `0.2.0-rc.2`、内置 Node `24.18.1` 和同版源码参考 `639ed015`；真实模型为 `deepseek-account/deepseek-flash`，执行后端为 Driver `0.28.2` / guest Python `3.12.14`。版本冻结与真实证据见 [C2 总结](docs/stages/c2-summary.md)。

初始 Web A0 使用 `deepseek-ai/deepseek-harness@00102833dfaee1da9f48a3a8eae9d34005a75218` / `0.1.7-alpha.2` 及其 lockfile，本地 Node `24.9.0`、pnpm `11.7.0`；已安装、验收后归档，仅作历史。安装、构建与原生模块验证见[接入说明](agent/harness/README.md)。不使用浮动 latest 或混用两版 API，变更基点需另行回归。

上游是开发者预览版，公开声明尚未完成安全审计。项目不把官方组件名称当作边界已验证的证据。具体基点、来源和未测状态在 [upstream-reference.json](agent/harness/upstream-reference.json)。

## 3. Harness 集成方式

### 3.1 Desktop profile 与插件组合

复用官方 Desktop 和其独立 `.runtime/desktop-home` 下的 `desktop` profile，通过项目 `cordis.desktop.*.patch.yml` 组织受控插件和 preset，不读旧 Pi 配置。Desktop 内部共享 Web 客户端，不恢复旧 Web 服务。配置补丁替换整个 config 块，不能假定递归合并。

已接入 A0 的 `a0-verify`、C0 的 `c0-calculator`/`c0-ui`、C1/C2 的受控 preset，按任务显式选择，不同时开放默认工具。A0只启用受控 list/read/write、算术诊断和图片探针；CSV及完整文件业务验收在A1。C0另接 VM 工具，不能继承任意宿主桌面能力。preset 可能重新挂载工具，需同时检查根插件、继承层、模型请求和最终 guard；只禁用根 `tool-bash` 不足以证明无 Shell。

实施时核对固定版本的 profile/preset API，使用官方配置展开能力保存有效插件清单，运行时再断言模型可见工具和可执行工具一致。新增工具默认不获准，参数错误或策略加载失败应拒绝运行。

preset热更新时已有Agent保留原revision；进程重启后按preset ID使用当前定义。热重载与进程重启分别测试，不能只观察新会话就声称旧会话权限同步。

### 3.2 工具适配

现有 `agent/workspace-*.mjs` 和 `image-probe.mjs` 保持框架无关；新增 `agent/harness/` 插件负责 Harness 的参数 schema、输出 schema、`execute`、取消信号及结果图片转换。

旧 Pi 注册层、`defineTool` 导入、文件写入队列、`--no-tools` 和会话格式不直接照搬。Harness 工具输出是规范 JSON 值及声明的投影，图片结果必须转换成模型实际可读的内容块；只返回本地路径不算成功。输入与输出 schema、取消时机、并发写入、错误类型和 UI 展示都需要接入测试。

已迁移的工具核心与接入顺序：

| 工具 | 现有核心 | Harness 适配状态 |
|---|---|---|
| workspace_list | 限定目录、排序、最多200项 | 已注册并真实调用，受 A0 策略约束 |
| workspace_read | UTF-8白名单、1 MiB文件、最多200行/64 KiB输出、SHA-256 | 已注册，真实文件读回与独立核对通过 |
| workspace_write | 文本白名单、256 KiB上限、默认不覆盖、临时文件落盘 | 已注册，受控写入、读回、取消和边界测试通过；不宣称 OS 竞态隔离 |
| workspace_csv_stats | 1 MiB、10000行、100列、最多20个指定数值列 | A1 本地实际统计/产物/读回通过；不经 Shell |
| workspace_image_probe | 固定96×64四象限PNG | 官方附件/image block、实际模型识别和独立像素核对通过 |

现有 Computer Use 由官方 Harness 工具插件 → 私有受控 HTTP bridge → VM 内 Driver 执行；bridge 负责目标/预算/停止/审计，验证器能力独立。未开放通用 MCP 或宿主 native provider，不能因框架支持它们就开放整个服务器。

### 3.3 Desktop 交互

当前入口复用官方 Desktop 的会话、模型设置、工具卡片、停止和审批界面，不自行开发桌面壳。Desktop 独占其 home 中的 `desktop` profile，不能直接启动旧 `cuagent-a0` Web profile；项目插件须在新入口重新接入和核验。Web 只绑定受控本地地址，远程协作走受控连接；不能把管理端口直接暴露公网。UI 显示工具结果不等于独立验证成功。

A0 检查附件上传、手动终端、插件管理、预置切换和后台任务是否扩大可用能力。A0/C0在后端落实最低任务状态、预算、停止和验证记录；A1可完善UI呈现与通用插件体验，但不承担首次建立安全边界。

## 4. 环境、权限与数据

沿用已确定的本地A0路线：开发源码、文档、无凭证单元测试及一个受控文件试验位于新项目目录。A0运行前先核验Harness专用profile、任务根、可见工具和网络；原有本地授权不等于默认Web配置已安全。A0最小验收后优先进入C0；桌面执行及对应任务数据、原始证据必须位于测试VM。首次桌面动作前核验VM隔离、授权目标、停止、预算和审计，不能等到A1。

当前运行时数据分开保存，不提交到 Git：

```text
.runtime/desktop-home/         # Desktop 配置、开发凭证、会话；不向模型开放
.runtime/runs/<run>/workspace/ # A0 专用文件；桌面数据和原始证据在VM
.runtime/runs/                 # host 私有汇总；模型不能修改验证/审计
```

同进程路径检查只针对模型工具参数，不隔离恶意插件、同用户并发进程或竞态攻击；处理不可信输入与真实桌面时需要 OS/VM 边界。不能宣称核心单测覆盖了全部系统攻击面。

必须核对的 Harness 差异：

- 上游 `fs-sandbox` 主要限制写入；读取、列目录与元数据不能假定被同样限制。项目保留自己的读写路径检查。
- 只允许专用任务根内的规范化相对路径；绝对路径、任意 `..` 段和越界符号链接拒绝。写入最终符号链接拒绝，父目录真实路径和目标类型检查必须执行。
- `sdk-minimal` 是较小功能组合，不是默认安全组合，不能直接替代专用 profile。
- Shell、终端、网络搜索/fetch、动态装插件、子 Agent、任意代码执行和不需要的 MCP 路径在 A0 不启用。Web 的手动入口也必须纳入实际配置清单。
- OTel 上报与 DeepSeek session-log contributor 是不同路径；逐项关闭非必要遥测、反馈会话上传和 session-log contribution，再做离线与网络行为核验。不能以 local-first 推断无上报。
- 运行时调用模型会把任务内容发给已配置模型服务，这与额外会话上报不同；只用开发数据、项目凭证，不读个人旧认证。

上游 Computer Use provider 可作为接入候选。native desktop provider 控制其运行主机，因此必须部署在测试 VM，不能把宿主安装插件误写成“远程控制 VM”。同桌面互斥仍由项目协调。

## 5. 会话、任务、事件与停止

会话记录对话；任务记录执行目标和权限，两者分开。一个会话可以有多个 run，同一个 run 的恢复、压缩和接管不会重置规则或预算。执行策略保存程序状态，不靠模型摘要保持约束。

最小事件包含 `session_id`、`run_id`、`call_id`、工具、脱敏参数、起止时间、结果/错误、产物引用、观察标识、实际调用计数和验证状态。凭证不进日志，原始截图和完整会话不自动发布。

每任务默认最多30次实际工具请求。观察、失败、重试和复合工具的内部实际请求均计数；包装入口不重复计数，未派发的拒绝记录单独分类。预留新鲜验证观察，到限只离线核对已有证据。预算上调须先修改策略和该任务验收协议。

审批前不执行，拒绝后不能换另一工具绕过。停止先关闭新派发，再记录在途状态；取消信号不等于副作用被撤销。超时副作用记 UNKNOWN，预算内重新观察再决定，不能盲目重复。恢复后暂停执行，核对现场与控制权后继续；`call_id` 只追踪，不自动幂等。

项目状态统一为 RUNNING、SUCCEEDED、FAILED、BLOCKED、UNVERIFIED。审批、停止、UNKNOWN 是控制/动作事件，不随意增加一套冲突任务枚举。Harness 完成事件只触发验证，只有独立验证通过才 SUCCEEDED。

## 6. Computer Use 与验证

C0 首先复核历史 macOS VM/Driver，保留固定12×34 smoke作为诊断对照。最早的真实模型闭环也用12×34，但必须由模型根据新观察实际操作，随后核对轨迹、新显示、`result.txt`读回和独立期望值；单例通过不代表九例及三个界面用例完成。模型工具的截图、AX、点击、输入、滚动绑定允许应用、PID、窗口和新观察；坐标或目标失效重新观察。文件对话框、URL跳转和跨应用动作同样受限。

计算器验收同时核对实际轨迹、操作后新显示、`result.txt`读回和独立期望值。期望值只给验证器；模型不能自算后写文件冒充执行，禁止 eval 用户表达式。可靠 AX 读不到或结果歧义则 UNVERIFIED，不能让模型猜答案。

验证器独立于模型工具权限；日志、截图、验证报告不能由模型修改。开放式任务没有充分证据时报告未验证。C1固定六类任务，C2加入故障注入和人工接管，完整门槛见开发计划。

## 7. 当前复用与延期

复用：文件/CSV核心及边界测试、图片探针、CSV独立核对器、三份Python历史文件、Lume五文件补丁与MIT许可证。Pi历史摘要只用于追溯。

已完成 Desktop 专用配置、真实模型/文件/图片链路、C0 固定桌面任务、C1 六类增强、C2 控制权/故障恢复和独立评测，以及 A1 本地三文本/CSV、插件/会话/安全回归。实现与失败记录见 [PROGRESS](PROGRESS.md) 和各阶段总结。C3/第二人暂缓，O0 后置；当前范围为 A1 本地验收。

后置：多Agent、第二套规划循环、长期记忆平台、完整OS原生库、跨设备调度、独立GUI。Agent-S/Jev仅在固定失败或成本记录支持时另行评估。

## 8. 上游依据

以下均固定到本轮参考commit，升级时重新核对：

- [架构与profile组合](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/docs/architecture.md)
- [工具schema、执行与guard](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/docs/subsystems/tools.md)
- [base组合与会话上报说明](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/bundle/base/README.md)
- [Web预置配置](https://github.com/deepseek-ai/deepseek-harness/tree/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/bundle/web-app)
- [安全状态与隔离限制](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/SAFETY.md)
