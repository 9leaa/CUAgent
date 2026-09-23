# 从旧方案迁移到 CUAgent

日期：2026-09-23。迁移目标：DeepSeek Harness 通用 Agent → Computer Use → 后续 OS 原生能力。新仓库是独立项目，不继承旧Git历史，也不把旧运行时配置当新配置。

## 1. 仓库与保留范围

- 新公开仓库：[9leaa/CUAgent](https://github.com/9leaa/CUAgent)，本地 `/Users/zhangchengjie/CUAgent`，分支 `harness-migration`。
- 旧仓库：[9leaa/os_agent](https://github.com/9leaa/os_agent) 已归档停用，描述和主页指向CUAgent；可由维护者解除归档，不删除历史。
- 旧本地 `/Users/zhangchengjie/osagent` 的 `a0-controlled-workspace` 未提交/未跟踪实现已迁入；随后按用户要求将旧目录连同Pi安装/配置移至废纸篓，不再作为开发工作区。
- 更早的 `/Users/zhangchengjie/Documents/ChatGPT/osagentmvp` 中旧Cua源码、Git元数据和方案文档也已移至废纸篓；VM、运行工具、镜像和原始证据保留在原处。
- 不复制 `.git`、`.runtime`、Pi依赖、认证、会话、个人设置、原始桌面证据、VM磁盘、系统镜像或完整Cua上游树。
- 新远端已创建；首次代码发布使用`harness-migration`阶段分支，不继承旧仓库历史，也不创建PR。

## 2. 全部旧设计的承接位置

“全部迁移”是把有效设计和验收要求纳入当前一套方案；过期框架指令不再作为开发规范。原文现位于本页§7记录的回收目录，需要追溯时在清空废纸篓前恢复；旧Git历史曾重写，不能保证仅靠旧提交链接能恢复全部文档。

九份来源文档的原路径与SHA-256保存在 [migration-design-sources.json](migration-design-sources.json)，用于区分本次实际审阅版本和更早副本。

| 旧文档 | 迁入的新文档/章节 | 保留与适配 |
|---|---|---|
| Mac_OS_Agent_Design_v0.2.md | DESIGN §1、§3、§5、§6 | 单运行时、执行与验证分层；会话/任务分离；改用Harness Web与Cordis |
| Mac_OS_Agent_Collaboration_Plan_v0.2.md | COLLABORATION；计划§2、§10 | 两条开发线、独立VM、版本和第二人复现；J阶段合并到A/C阶段 |
| Mac_OS_Agent_MVP_Plan_v0.1.md | 计划§5、§7；DESIGN §5、§6 | 九组计算器、异常、计数和结果读回；旧Claude SDK入口撤销 |
| CODEX_HANDOFF.md | AGENTS；DESIGN §4；PROGRESS | 权限与交接事实；用实际资产替代“完全未实现”的过时状态 |
| Pi_Agent_Development_Plan.md | Harness_Development_Plan全篇 | 保留A0→A1→C0→C1→C2→C3与O0后置；重写运行时特定内容 |
| Pi README / PROGRESS | README；PROGRESS；docs/history | 分开迁移资产、历史通过与Harness尚未验收 |
| 旧 COLLABORATION / AGENTS | 新COLLABORATION / AGENTS | 阶段分支无codex前缀、由用户提交推送、不自动创建PR |
| tools/mac_vm/README、vm-manifest | 同名新文档 | 保留恢复流程与环境来源；明确Harness未集成 |
| patches/cua/README、LICENSE、补丁 | 同名新文档及原字节资产 | 固定Cua源、补丁内容、许可与复现；不复制上游整树 |

## 3. 阶段映射

| 旧阶段 | 在新路线中的位置 | 状态处理 |
|---|---|---|
| M0：环境 | C0环境复核 | 历史通过，仍需当前重测 |
| M1：固定计算器 | C0诊断与回归对照 | 历史12×34/17次调用/AX408，不等于模型任务 |
| M2：模型执行 | A0模型工具链＋C0真实桌面 | 旧阶段未通过，不能继承成功 |
| M3：文件及结果校验 | A0产物验证＋C0 result.txt | 保留独立验证，不能模型自评 |
| M4：失败与安全 | A1控制＋C2故障评测 | 保留异常集与停止/预算边界 |
| J0–J4：联合开发草案 | A0/A1/C0–C3/O0 | 废止旧选型与工期，不开并行路线 |
| Pi A0/A1 | Harness A0/A1 | 通用核心可复用，框架链路重新验收 |
| Pi C0–C3/O0 | Harness C0–C3/O0 | 用例与发布门槛保留，UI/provider接入改写 |

## 4. Pi 特定内容如何替换

| 原方式 | Harness方式 | 必须重新验证 |
|---|---|---|
| Pi终端TUI / pi-local.sh | 官方Web UI＋独立profile/home | 有效配置、模型、会话、额外数据出口 |
| Pi扩展registerTool / TypeBox | Cordis插件、Harness工具schema/execute/output | 参数、结果、错误、取消、并发和图片 |
| --no-tools / 显式extensions | 专用preset＋最终执行guard＋加载清单 | 子scope和Web preset不会重新开放工具 |
| Pi写入队列 | Harness适配层明确串行/并发策略 | 同一路径并发不会破坏验证与默认不覆盖 |
| Pi会话与压缩 | Harness持久会话及事件 | 恢复/压缩不丢失程序权限和预算 |
| Pi缺MCP的特性描述 | Harness可用的MCP组件，按需接入 | 工具allowlist与图片/权限链路 |
| 自接Cua适配预案 | 先核对官方Computer Use服务与Cua provider | Driver兼容、运行主机、桌面锁和独立验证 |

不迁移Pi启动脚本、安装脚本、versions.env或extensions作为可执行新入口。未编造对应Harness插件；它们列为A0工作。

## 5. 实现资产与证据

20个文件按原字节迁移，详细相对路径及SHA-256见 [migration-assets.json](migration-assets.json)。其中15个来自旧工作树未跟踪文件，5个与旧HEAD `5901c817c5ca8e86b7be29badea34ee4f12e4158` 一致；不能把整个迁移归因于该提交。

- `agent/workspace-{path,list,read,write,csv-stats}.mjs`、`image-probe.mjs`：核心不依赖Pi注册层。
- `agent/tests/` 五个测试文件、`agent/fixtures/a0/sales.csv`、准备脚本与CSV独立验证器：保留用例和确定性输入。
- `tools/mac_vm/` 三个Python文件：历史VM预检、固定计算器与7项mock。
- `patches/cua/` MIT许可证与隔离补丁：原字节保留。
- [Pi CSV/图片历史摘要](docs/history/pi-a0-csv-image-2026-09-22.md)：原字节存档；其中命令、模型清单及五个Pi工具来自当时环境，不是新Harness的启动说明。

## 6. 必须保持的验收约束

1. A0三轮对话、三份文本、CSV统计/读回、两种图片路径、重启与越界拒绝不能省略。
2. C0九组加减乘、三个基础GUI任务；实际轨迹、新显示、result.txt读回、独立期望值四项齐全。
3. C1六类任务，改动前后每例三次；C2固定18次至少17次通过且每例至少一次，全部安全/取消/恢复/虚假成功用例通过。
4. 每任务默认30次实际请求，观察/失败/重试/内部调用计数；重启、接管和压缩不清零，验证须预留预算。
5. UNKNOWN副作用先观察，禁止盲重放；call_id不自动幂等。结束信号不是SUCCEEDED。
6. 执行端白名单、路径与目标验证、停止后无新派发、拒绝不可绕过；模型不可改证据或验证器。
7. C3第二人独立部署和扩展；同机克隆不算跨机验收。

UFO仅作历史职责参考：commit `be75a7ded2ad98d97819e15ff1b39d4202ac3ac5` 的dispatcher、processor、evaluation、state；不把Windows执行器、类体系或模型评估器变成运行依赖。Cua许可和来源另见 [补丁说明](patches/cua/README.md)。

## 7. 停用与恢复

旧GitHub仓库仅归档，未删除；新仓库未复制历史大对象，因此不需要再次强推清历史。

用户随后明确要求卸载Pi、删除旧文件和代码。2026-09-23核对20个迁移资产及9份来源文档哈希后，将以下内容移入 `/Users/zhangchengjie/.Trash/cuagent-retired-20260923.qny54v`：

| 回收目录内名称 | 原位置 / 内容 |
|---|---|
| osagent | 旧osagent项目全部，包括项目内Pi安装、会话和项目配置 |
| pi-user-config | `/Users/zhangchengjie/.pi`，Pi用户配置；未读取凭证内容 |
| cua-source | 旧osagentmvp/cua，上游源码及构建目录 |
| handoff-git | 旧osagentmvp/.git |
| old-documents | 旧osagentmvp的9份根Markdown文档 |

Pi不存在全局npm安装；项目安装随旧目录移除，PATH中无pi入口。回收目录可手动恢复，未清空废纸篓，因此不代表已经释放磁盘空间。旧`.vm`、`.vm-tools`、`downloads`和`evidence`未删除或移动。

迁移清单中的source_root/source_path记录迁移当时的原位置，仍用于历史追溯，不表示文件现在仍在该路径。

本次完成设计与资产迁移，Harness已在忽略目录中固定版本安装、构建；profile、Web与模型接通仍按A0执行，测试状态以 [PROGRESS](PROGRESS.md) 为准。
