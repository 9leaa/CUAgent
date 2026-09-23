# AGENTS.md — CUAgent

## 当前路线

先完整阅读 README.md、Harness_Development_Plan.md、PROGRESS.md，再检查实际 Git 和文件状态。架构依据 DESIGN.md；迁移范围见 MIGRATION.md。文档尚未生成时先向负责迁移的主任务核对，不恢复旧路线。

用户于 2026-09-23 明确切换到 DeepSeek Harness，并将Computer Use定为开发主线。复用官方Web UI、Agent循环、模型适配、会话及Cordis插件系统；顺序为A0最小可用底座→C0单例及固定用例→C1–C3增强、评测和交付。A1三份文本、CSV及通用插件体验可并行或后补，不阻塞Computer Use；O0系统原生能力后置。Pi、OpenCode、Claude SDK仅作历史来源，不是运行依赖。

## 实现与验证

- 不自行重写主循环，不复制整套上游源码到本仓库。项目工具核心保留于 agent/，Harness 适配器在 agent/harness/；历史诊断在 tools/mac_vm/，Lume 改动在 patches/cua/。
- 固定框架包、对应源码、Node、模型、Driver 和策略版本。npm 发布版与源码 master 的接口不能混用；候选或调研版本不等于已安装、已验收。
- 现有文件工具与测试可以复用；Pi 的模型和图片链路通过记录只能作为历史，不计入 Harness 验收。31 项工具测试及 7 项 VM mock 的结果也不能冒充模型或 VM 集成通过。
- A0只需一个真实受控文件任务、会话、图片及必要执行边界；不要为了三份文本、CSV或完整插件体验推迟C0。第一次真实桌面动作前必须完成VM隔离、目标授权、审批/拒绝、停止、实际请求预算和基本审计，不能把这些安全控制后移到A1。
- 开发工具可在授权项目目录编辑和运行无凭证测试。沿用用户已确定的A0本地开发：受测Agent只处理新项目专用测试目录，先验证Harness profile、工具和网络范围。桌面操作及其任务数据、原始证据从C0起必须在测试VM，不能控制宿主个人环境。
- 不共享宿主目录或剪贴板，不关闭 SIP，不授予免密 sudo 或全盘访问，不复制旧凭证、会话或 VM。开发凭证由用户为新运行时配置。
- 只启用明确审查的工具。执行端检查目标、路径、参数、URL、调用预算与停止状态；默认 shell、网络、MCP、子 Agent、动态装插件均不是隐含授权。
- Prompt、Skill、Web 审批和框架的“沙箱”名称都不是边界证明。Harness profile、原生文件/命令通道和会话上报默认行为需要逐项核验。
- 每任务最多 30 次实际工具请求，观察、失败、重试、封装内部调用计数；预留验证预算，恢复不清零。到限不得再观察，不能运行时放宽。
- 副作用超时记 UNKNOWN，先观察再决定，不盲目重试；call_id 不提供幂等。停止后不得派发新动作，在途动作单独记录；接管后必须重新观察。
- 独立验证器核对动作轨迹、新界面显示、产物读回和独立期望值。禁止 eval 用户表达式，禁止模型自算后写文件冒充 GUI 运算；不能让模型修改日志、截图或验证报告。
- 状态使用 RUNNING、SUCCEEDED、FAILED、BLOCKED、UNVERIFIED；缺证据不得标成功。框架 finished/done 不是项目 SUCCEEDED。
- 每阶段更新 README 和 PROGRESS，记录命令、版本、证据、失败、阻塞、未测项；区分本地单元、mock、真实模型和真实 VM 测试。

## 协作

遵循 COLLABORATION.md。阶段分支不使用 codex/ 前缀。默认由用户 commit、push 和决定是否开 PR；助手不得自行提交、推送、创建 PR 或合并。例外：用户已单独授权本次在 `harness-migration` 完成首次提交并直接推送至 `9leaa/CUAgent`，不创建 PR；此授权不延伸至后续发布。

保留用户未提交改动、历史实现来源和上游许可证。未经用户明确要求，不删除工作区、VM、镜像、凭证或不可复现的历史证据。旧Pi安装及源码已按用户2026-09-23的明确要求移至废纸篓；VM与镜像仍保留。下游修改历史 VM 实现前阅读 tools/mac_vm/README.md、patches/cua/README.md 和 MIGRATION.md 的来源；UFO 固定参考 be75a7ded2ad98d97819e15ff1b39d4202ac3ac5，仅为历史设计参考。

中文简洁汇报，先说明完成内容、测试与阻塞。用户已选定 Harness，不再自行切换框架。
