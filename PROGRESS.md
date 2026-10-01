# CUAgent 实际进度

更新：2026-10-01。主路线：[Harness最小可用底座 → Computer Use主线 → 通用增强/O0](Harness_Development_Plan.md)。设计、实际实现、本轮测试和历史结果分别记录。

## 当前交付

| 项目 | 状态与证据范围 |
|---|---|
| 新仓库 | 公开 `9leaa/CUAgent`；首次发布使用 `harness-migration` 分支，不创建PR；以Git远端实际状态为准 |
| 旧仓库 | `9leaa/os_agent` 已归档，描述/主页指向新仓库；后续按用户要求将旧本地源码和Pi移至废纸篓，VM/镜像保留 |
| 设计与计划 | README、DESIGN、Harness_Development_Plan、AGENTS、COLLABORATION、MIGRATION已按Harness与Computer Use优先顺序改写 |
| 核心工具迁移 | 20个文件逐字节迁入；manifest记录来源类别和SHA-256，其中15个来自旧未跟踪文件 |
| 工具核心测试 | Node 24.9.0：最新本地回归 36/36 通过；属于无模型单元测试 |
| 本轮VM工具测试 | 本阶段无凭证测试重新核对；实际模型结果见阶段总结 |
| Harness版本 | 当前官方 Desktop App 0.2.0-rc.2 / 内置 Node 24.18.1，同版源码参考639ed015；初始 Web 固定源码00102833d / 0.1.7-alpha.2仅历史 |
| Harness A0最小底座 | Desktop A0 迁移记录见下文；后续 C2 回归不计入本分支 |
| C0-01及C0–C3 | 本分支已完成 c0-01、c0-02；后续阶段尚未纳入 |
| A1通用增强 | 三份文本、CSV和完整插件/会话体验待实施；不阻塞C0–C3 |
| O0 | 后置，未开始 |

## 2026-09-30：Desktop A0 迁移与真实验证

- App 自动更新到 `0.2.0-rc.2`；按同版本源码 `639ed015` 核对接口，适配器使用 App 内置 Node 24.18.1 和同版工具库验证，7/7 测试通过。
- 五个旧受控工具已迁入 Desktop profile；保留用户账号模型和 UI 设置。root guard、30 次持久预算、工作区边界及审计继续有效，关闭插件清单上报以兼容本地文件插件。
- App 自带 Office 工具在 Host 中直接注册，profile 禁用项不能移除它；通过 `agent/created` 的 scoped `tools.restrict` 隐藏 `load_workspace_dependencies`。真实模型请求记录只有五个受控工具。
- 真实 `deepseek-account/deepseek-flash`：读取 input.txt，计算 27+16=43，写 result.txt 并读回，独立文件核对一致。工具返回真实图片，四象限红/绿/蓝/黄全部与独立答案记录一致。
- 停止：首次算术任务过快，20 次调用在点击前已完成，不计为停止证据；第二次长文本任务即时停止，UI 显示已停止，末尾计算未派发。运行时停止后拒绝派发另由内置工具库测试覆盖。
- 预算：实际派发严格停在 30 次，第 31 次被拒；同 run-id 重启后再次调用仍被拒，会话与结果恢复。预算按 run-id 共享，不是每个会话重新计数。
- 证据 `.runtime/runs/desktop_a0_20260930_001/verification.json`、`audit.jsonl`、`request-audit.jsonl`、profile 快照和 workspace/result.txt。此验证 run 已耗尽；新的验证使用新的 run-id，不删除旧账本。
- 可复用入口：build-desktop-plugins.mjs、configure-desktop.mjs、cordis.desktop.a0.patch.yml、start-desktop.sh。未提交/推送；不计为 C0 桌面智能体任务通过，也未验收直接上传图片。

## 2026-09-30：移出 Web，改用官方 Desktop

- 用户指定官方 macOS Desktop App 为当前交互入口；旧 A0 Web 通过记录保留为历史，不计入 Desktop 验收。
- 移出前 3080、3099、3100 均无监听，无须结束运行中的 Web 进程。旧源码、依赖、home、启动脚本及 Web 配置已移至 `/Users/zhangchengjie/Documents/ChatGPT/osagentmvp/retired-dsh-web-20260930`，恢复清单为 `archive-manifest.json`；保留测试产物和通用工具核心。
- 下载官方域名 `download.deepseek.com` 的 `deepseek-harness-0.1.7-rc.2-mac-arm64.dmg`。安装包内 App 的深度严格签名检查通过，签名主体为 Hangzhou DeepSeek Artificial Intelligence Co., Ltd，Team ID `NAN929V4UM`；Gatekeeper 接受为 Notarized Developer ID。
- 安装目标为 `/Applications/DeepSeek Harness.app`；项目启动脚本为 `agent/harness/start-desktop.sh`，使用独立 `.runtime/desktop-home`。未复制旧 Web 凭证、会话或插件。
- Desktop 实际启动到欢迎页，无障碍观察确认“登录”和“添加 API Key”两个按钮；尚未登录或配置凭证，未发起模型请求。安装记录保存在 `.runtime/desktop-installation.json`；启动脚本通过 zsh 语法检查，`git diff --check` 通过。项目插件、模型真实请求、停止与预算、VM Computer Use 均未因安装而自动通过。

## 2026-09-23：仓库与方案迁移

本轮工作：

- 创建新本地仓库与公开远端，配置origin。只建阶段分支，提交和推送仍由用户负责。
- 将旧公开仓库归档为只读并设置迁移指向；未删除仓库、旧工作树、VM、镜像或开发凭证。
- 读取最新Pi计划及实现，同时审阅更早整体设计、联合开发计划、MVP计划和交接要求；逐项映射见MIGRATION。
- 复用框架无关工具核心、测试和验证器；旧Pi安装/启动/注册层不作为新运行时迁入。
- 以固定Harness源码核对profile/preset、工具schema、执行guard、取消、Web展示、额外会话上报、文件沙箱和Computer Use provider差异。
- 保留Cua补丁和MIT许可证；迁入历史Pi验收摘要但明确不构成Harness通过。

实际验证：

```bash
node --test agent/tests/*.test.mjs
python3 -m unittest discover -s tools/mac_vm/tests -v
```

结果：31项Node单元、7项Python mock均通过。迁移的20对文件SHA-256与原工作树一致，清单见 [migration-assets.json](migration-assets.json)。本轮没有重新构建Swift/Lume、启动VM、安装Harness、读取密钥或发送模型请求。

九份旧设计/进度/规则文档另保存来源哈希；本轮文档检查覆盖13份Markdown相对文件链接及5份JSON解析，无缺失链接或解析错误。尚未发布到GitHub。

## 2026-09-23：本地安装 Harness

- 路径：`.runtime/harness`；固定源码浅克隆，Node 24.9.0/macOS arm64，项目本地pnpm 11.7.0。未全局安装。
- `pnpm install --frozen-lockfile --store-dir ../pnpm-store`通过；随后`pnpm run build`退出0，包含原生模块、Host/Client与Web，生成263个client artifacts。
- 以独立`DSH_HOME=.runtime/harness-home`（执行时使用绝对路径）运行根目录`pnpm dsh --version`与`--help`，均退出0，版本输出`0.1.7-alpha.2`。
- 构建后离线frozen install复核通过；上游源码无修改，锁文件摘要与具体命令见[接入说明](agent/harness/README.md)。初次安装的三个子包bin链接缺失仍记录为限制；使用根目录CLI不受影响。构建有弃用项/体积警告，无构建错误。
- `.runtime/harness-installation.json`记录本地安装，build/install日志保存在同目录，全部被Git忽略；本次未提交、推送或创建PR。
- 没有读取/配置API Key、启动Web服务、调用模型或操作桌面。A0-01仅环境安装/构建部分完成，模型/策略固定以及整个A0仍未验收。

## 历史资产，不计入 Harness 验收

| 来源 | 已有结果 | 尚未完成或限制 |
|---|---|---|
| Pi 0.86.1 / deepseek-flash | 历史三轮对话；CSV统计/写入/读回及独立核对；固定图直接输入与工具图片返回 | 新Harness需重验；默认模型固定/重启、三份文本与真实越界拒绝当时尚未齐备 |
| workspace_list | 核心与边界测试；用户报告真实调用成功 | 当时没有单独保存真实调用证据 |
| 受控文件核心 | 路径、类型、大小、默认不覆盖等测试 | 进程内策略，不是OS沙箱；并发/取消/宿主权限不能由这些测试推断 |
| M0 | 历史VM隔离、普通用户、Driver截图/应用信息及停机基线恢复通过 | 本轮未检查当前VM运行状态 |
| M1 | 固定12×34；17次Driver请求；新AX显示408；独立smoke通过 | 无完整result.txt闭环；其余八例和模型桌面执行未通过 |
| Lume补丁 | 历史五文件隔离补丁、两项Swift测试和零共享检查 | 本轮只保留文件，没有重新构建或重跑真实隔离 |
| 旧M2–M4 | 旧SDK路线停止 | 不恢复旧模型入口，不将未通过阶段改写成功 |

历史模型摘要：[Pi CSV与图片链路](docs/history/pi-a0-csv-image-2026-09-22.md)。其正文保持当时原字节，引用的是旧环境命令和能力，不是本项目启动方式。

## 2026-09-23：卸载 Pi 与清理旧代码

- 用户明确要求卸载Pi、删除旧文件和代码。确认没有全局Pi npm包或PATH入口，Pi实际安装在旧osagent/.runtime/pi。
- 清理前再次核对新旧20个资产和9份来源文档SHA-256一致，没有读取认证内容。
- 将旧osagent项目（含Pi运行时与项目配置）、用户`.pi`、旧Cua源码、旧交接Git目录和9份旧文档移入私有废纸篓目录；映射见MIGRATION §7。
- 保留旧osagentmvp内`.vm`、`.vm-tools`、`downloads`、`evidence`；未停止或修改Lume/VM进程，未卸载Node、npm或Cua运行工具。
- 清理只涉及旧资产及文档状态更新，没有改动新核心代码；不重复调用模型、启动VM或重新安装框架。没有commit、push或PR。

## 2026-09-23：修复原生模块架构错误

- 用户Web运行报`system.node`为x86_64、Node需要arm64。实查Rosetta状态为1，`cc -dumpmachine`为x86_64；此前构建退出0与CLI检查未覆盖原生加载，不能作为该模块可用证据。
- 在原生ARM64 shell中重新执行官方`build:native-system`，没有改上游源码、模型配置、密钥或会话，也未重启用户Web进程。
- 验证：`file`为arm64；ARM64 Node实际加载与导出检查通过；上游文件锁测试按名称筛选4项，4/4通过（加锁、竞争、释放、非法fd）；上游工作树干净。
- 模块SHA-256：`a0d2d9eddd629515646c5fe3e13c83d07713c97ab880fd11e2b5e65db6251623`。重编译与防复发命令见[接入说明](agent/harness/README.md)。用户重启后的Web/模型结果待验证，不将此修复计为A0通过。

## 2026-09-23：修复插件元数据异常

- 固定Harness的profile resolver在改写Node解析异常时直接赋值只读`error.stack`，把可预期的`ERR_PACKAGE_PATH_NOT_EXPORTED`变成`TypeError`，导致Web插件元数据卡片全红。仅修改本地上游源码的两处异常栈处理，并加一项回归测试；可重放补丁见[patches/harness/readonly-error-stack.patch](patches/harness/readonly-error-stack.patch)。
- 在`.runtime/harness`运行`pnpm exec vitest run packages/boot/app-boot/tests/profile-resolution.spec.ts packages/boot/app-boot/tests/package-meta.spec.ts --reporter=dot`：304通过、1跳过；`git diff --check`及补丁反向检查通过。`pnpm run build:lib:host`成功，产物包含修复，`system.node`仍是arm64；未重建原生模块，未触碰密钥或用户运行中的Web进程。
- Web重启后的插件显示尚未复验，不计入A0验收；上游源码当前有本地修改，重装需重新应用补丁。

## 2026-09-23：首次分支发布

- 用户单独授权助手检查、提交并直接推送本仓库到公开`9leaa/CUAgent`的`harness-migration`分支，不创建PR；后续仍沿用用户自行提交推送的约定。
- 发布范围仅含设计、迁移工具与测试、历史脱敏摘要和可重放Harness补丁；忽略`.runtime`、开发凭证、会话、VM磁盘和原始桌面证据。具体提交与远端结果以Git记录为准。

## 2026-09-23：调整开发顺序，Computer Use优先

- 用户指出旧清单把完整A0/A1放在C0之前，与当前Computer Use主目标不符。计划改为A0最小底座→C0-01真实12×34闭环→C0-02九例及三个基础GUI→C1–C3；A1通用增强可并行或后补。
- A0只保留真实模型/会话、一个受控文件任务、两种图片链路与最低执行边界；三份文本/CSV业务验收移至A1，不删除原有用例。审批、停止、预算、目标授权和基本审计在首次桌面动作前必须落实，不因A1后移而放松。
- 本次仅修改计划与说明，未新增Harness插件、调用模型、启动VM或完成任何C阶段验收。

## 2026-09-29：A0 本地最小门槛收口

- 固定 `cuagent-a0` profile：仅 base+Web bundle；正式补丁 `agent/harness/cordis.a0.profile.patch.yml`，启动脚本 `agent/harness/start-a0-web.sh`。四个上游 Web preset 已禁用，`agentPresets/list` 仅返回默认 `a0-verify`，请求 `standard` 被拒绝。真实模型请求头只列五个 A0 工具，没有 shell、团队协作或通用文件工具。`session-log-deepseek`、OTel 在有效配置中关闭；未抓包，不推断无其他网络流量。
- 隔离 3100 实例、`a0_closure_20260929`：`deepseek-official/deepseek-flash` 三轮真实对话从“青杉”改成“海星”，重启后同会话仍回答“海星”；真实 `workspace_list` 有派发/结果审计。`workspace_write`→`workspace_read` 生成 `result.txt`，独立程序核对 29 字节、SHA-256 `d90eaf55cc26ed44d4fc99e54357363d13acc3ff8c4f6723411250170a3eb347`。
- `workspace_image_probe` 返回的 96×64 图片有真实 image block；独立验证器解码对象像素、核对答案库与模型回复，四象限 blue/red/green/yellow 全匹配。再将同一图片作为新会话的用户输入，真实模型直接回答蓝/红/绿/黄。此前用户在 Web 中直接发图也有成功记录；本轮新会话走 Web 的 `session/prompt` API，不等于重新人工检查上传按钮。
- 最终执行层 7/7 集成/单元测试通过：第 31 次拒绝、重启继承预算、禁用工具/停止信号无派发、审计损坏或不可写即拒绝；受控文件适配器还实测绝对路径、`..`、越界符号链接及覆盖拒绝，原内容不变。TypeScript 检查通过。此前同策略隔离实例的 Web 停止按钮经用户人工点击，日志证明停止后无新派发；正式 profile 未重复点击该按钮。
- A0 仅说明模型在当前专用 profile 下的最小能力与进程内安全边界，不是 OS 级沙箱、网络零流量证明，也不授权 VM 桌面动作。会话、附件、审计位于被 Git 忽略的 `.runtime`。验收时未修改 3099 用户实例或操作 VM；Git 发布另行记录。

## 2026-10-01：C0 桥接策略修复与无 VNC 启动检查

- 修复已有 `tools/mac_vm/c0_bridge.py` 初稿：启动要求显式 `--approve-calculator`；停止与请求准入串行化，停止日志保留在途请求，停止后无新准入；零调用时的停止也跨重启保留。
- 审计增加 call_id、连续预算校验、审计错误 fail-closed 和链接拒绝；应用/PID/窗口错误拒绝。仅成功返回的点击记录完成动作，Driver refusal/超时不算成功；失败观察使旧快照失效。
- 结果只能匹配新鲜 AX 显示，默认不覆盖；独立验证要求完整调用结果、实际文件读回和固定轨迹。验证 HTTP 路由使用单独 verifier token，模型通道不能调用验证，验证通道不能执行动作。token 留在 VM，未向模型配置通道。
- 新增 16 项无 VM/mock 边界测试，连同历史 7 项共 23/23 通过：`python3 -m unittest discover -s tools/mac_vm/tests -v`；`py_compile` 和 `git diff --check` 通过。这不是 HTTP 集成、真实 Driver 或真实模型验收，也不是同用户恶意进程隔离证明。
- 使用现有隔离 Lume v2，以 `LUME_MVP_HOST_ISOLATION=1 LUME_TELEMETRY_ENABLED=false`、`--display none --vnc disabled --network nat` 启动现有 restored 诊断 VM；Lume 报 running、192.168.64.3、vncUrl null，`lsof` 对该 Lume PID 无 TCP listener。没有修改全局 Lume、宿主防火墙、共享目录或剪贴板。
- 该 VM 的 TCP 22 拒绝连接，缺少不依赖 VNC 的登录/部署通道。未把代码部署到 guest，未调用模型或执行计算器。诊断后关闭本次启动的 VM；既有 Desktop A0 配置、模型凭证及预算账本未改。
- C0-01 仍未通过。下一步先获得受控 VM 登录/部署通道，按规则从无模型凭证停机基线建立测试副本，完成 guest 部署及 HTTP/停止集成，接入专用 C0 Harness 工具，再跑真实 `12×34` 与独立验证。未提交或推送。

## 2026-10-01：恢复 VNC 并打通 SSH

- 用户明确接受现有测试 VM 的 VNC 监听方式，按最新授权恢复原入口；没有改全局防火墙或路由器端口转发。`--display none --network nat`，仍使用隔离 Lume v2、零宿主目录/剪贴板桥。宿主 VNC 监听 `*:57593`；未测试外部可达性，不声称仅本机或公网暴露。
- 曾只读核对旧源码和系统运行时 VNC 接口，无绑定地址选项；临时进程网络限制候选未取得有效连通性证据，不计通过。没有改旧源码、重建 Lume 或应用持久网络限制。
- VNC 新画面确认 VM 可登录。Sharing → Remote Login 直接显示 Off，确认了之前 SSH 拒绝连接的原因；用既有测试 VM 管理员账户通过设置授权，开启 Remote Login，仅保留 MVP Agent（mvpagent），移除默认 Administrators 访问组。
- 开启 Remote Login 时系统自动开启了远程用户完整磁盘访问；新观察发现后立即关闭，最终画面确认 Off。没有授予免密 sudo、改变 SIP 或开启文件共享。
- TCP 22 接通后，实际 SSH 登录 `mvpagent@192.168.64.3` 成功：`id -un` 为 mvpagent，`id -Gn` 无 admin，`hw.model=VirtualMac2,1`，SIP enabled，`mount -t virtiofs` 无输出。使用项目私有 known-hosts，登录口令由私有回调直接交给 SSH，不打印、不复制到模型配置。
- SSH 独立读回 `com.apple.access_ssh` 的 GroupMembership 仅 mvpagent，Driver 版本 0.28.2。默认 `/usr/bin/python3` 触发开发工具安装提示，常用独立 Python 路径尚未找到可执行解释器；本轮没有安装软件，guest 桥接部署前还须定位或准备 Python，不能沿用旧版本声明。
- 诊断画面和开发辅助入口仅在忽略目录 `.runtime`；现有 restored VM 保持运行，SSH 设置已保存。C0 模型任务仍未执行；本轮仅解决查看、登录和部署通道。未提交或推送。

## 2026-10-01：C0-01 分支、guest 部署与真实接口检查

- 先建立 `c0-01-computer-use`，写 `docs/stages/c0-01-design.md`；保留原有未提交文件，不提交/推送。仍按 GitHub 原计划推进 C0-01、C0-02、C1、C2，不改变验收要求。
- 固定用户目录 Python 3.12.14，Astral python-build-standalone release 20260929，arm64 Darwin；归档 SHA-256 `1bb3e53d231ee2c8881e8daf6426f4dd95bff0dda496af0f3af300357aa998d0` 与官方资产及 guest 独立读回匹配。安装不需要 sudo，不修改系统 Python；仅传输解释器与项目程序，没有复制模型凭证。
- 部署到 guest `/Users/mvpagent/CUAgent-c0-01-20261001`，真实 Python 下 23/23 mock 通过。Cua Driver 0.28.2；固定 bridge `192.168.64.3:8766`，限宿主 NAT 源地址，独立 model/verifier token 留 guest 私有目录。
- `c0_gate_20261001_001/002` 观察失败保留为原始证据：截图有效，但 AXWindow 为空。新 VNC 画面发现 guest 自动锁屏；解锁后 `c0_gate_20261001_003` 实际 HTTP 六项通过：错误 token 403、模型验证入口 403、shell 409、新观察 200（3 次 raw 请求）、stop 200、停止后观察 409。没有降低 AX/PID/窗口检查。guest 使用有时限的 caffeinate 防止测试中休眠，不改永久系统设置。
- 新增 `agent/harness/c0-vm-tools.ts`、专用 C0 profile 和启动入口；仍复用官方 App 的 Agent 循环。根执行 guard 限四个工具和首个任务会话，取消监听传 guest stop，真实截图通过官方 attachment 服务返回 image block。模型没有任意路径/URL/验证器工具。
- 官方 Electron Node 下 `c0-vm-tools.test.ts` 边界测试通过：实际 defineTool schema、四工具注册、会话限制、图片附件、取消停止和超时不重试。该测试使用模拟 fetch，不等于真实模型验收。现有 A0 profile 尚未切换，官方 App 包未修改。
- 宿主 Harness 窗口自动化读取超时，未因此强行关闭现有 App；C0 模型任务、独立验证及阶段总结尚待完成。现有 restored VM 为开发环境，不冒充无凭证发布基线。

## 2026-10-01：C0-01 真实模型闭环通过

- 当前分支 `c0-01-computer-use`，技术方案在实施前建立，完成后写 `docs/stages/c0-01-summary.md`。保留用户脏文件，不提交/推送。
- 只读确认旧 Desktop 测试会话无未完成轮次后，用正常 SIGTERM 退出；切换 C0 patch、重编插件、同一 home 启动官方 App，账号/历史/账本未复制或删除。新 preset 列表仅 `c0-calculator`，其他 preset 不可选。
- 官方 Host 标准认证 RPC 创建 `session-9c5a4e06-e422-450e-8fa0-2ebc2628c5bf` 并仅派发一次任务；真实 `deepseek-account/deepseek-flash` 完成 17 个专用工具调用。请求审计含 17 次 image 输入，只有四个 VM 工具，没有计算工具、shell、子 Agent 或验证器入口。
- run `c0_model_20261001_001`：实际按钮 `All Clear/1/2/Multiply/3/4/Equals`；独立新观察显示 408，`result.txt` 与已审计读回 408。验证器核对所有 raw dispatch/result 完整、无 UNKNOWN，返回 SUCCEEDED，总共 20/30 raw 请求。原始证据留 guest C0Evidence，对应 host 汇总在忽略的 `.runtime/runs/`。
- 验证开发程序的 Node CLI 请求出现 EHOSTUNREACH；未把它当作 VM/桥接终止、未重启任务。使用已真实验证的 Python HTTP 客户端完成独立验证，凭证经 stdin 传递，不进 argv、日志或模型。正式 App 内模型请求始终正常。
- 仅 C0-01 单例完成。下一阶段按原计划新增九例及三个 GUI 用例；不放宽 C1/C2 的重复评测与安全门槛。

## 下一步

本次指定的 C0-01、C0-02、C1、C2 已完成。下一阶段为 C3 干净环境/第二人复现，需另行开展；继续使用官方 Desktop，不恢复已停用 Web。当前 App 为已耗尽的 A0 回归配置，新任务须新 run 和明确配置。

## 2026-10-01：C0-02 固定用例与保存面板修复（进行中）

- 分支 `c0-02-fixed-ui`，先写 `docs/stages/c0-02-design.md`，沿用固定模型 `deepseek-account/deepseek-flash`、Driver 0.28.2、官方 Desktop 0.2.0-rc.2 和每任务 30 次预算。
- 九组计算器全部首次真实尝试独立通过；raw 次数依计划顺序为 20、16、22、20、20、20、20、16、18。汇总 `.runtime/runs/c0-02-calculator-report.json`；轨迹、新显示、result.txt 与读回均核对，不是固定 smoke 脚本。
- 原生表单 run `c0_02_form_20261001_001` 通过，12 raw；滚动第一次因 Driver 未暴露 AXScrollArea 失败，第二次 `c0_02_scroll_20261001_002` 通过，14 raw，实际滚动及目标可见状态核对。改为新截图内限定 viewport 的窗口坐标，不开放任意桌面坐标。
- 文档保存前两次没有生成文件，均停止并保留 UNVERIFIED 报告。第一次 AX 输入被拒；第二次独立面板背景输入被拒。修正 `effect: refused` 判定，不将拒绝记成完成动作；增加同 PID/应用、唯一保存面板及按钮 frame 核对，只有明确 AX unresolved 的系统保存面板可用 foreground delivery。第三次真实任务正在验证，未提前登记通过。
- 最新无 VM/mock 回归 34/34 通过，含保存面板坐标映射、前台输入路由、拒绝计数、越权与假成功；不等于真实 GUI 成功。原始证据和失败均留私有目录，没有提交或推送。
- 文档第三、第四次点击返回 unverifiable，实际文件仍未出现，已停止并保留失败报告。新截图确认父窗口包含按钮而 sheet 单独截图合成父窗口；第五次去掉中间 sheet 截图并附加固定路径点击落点图，正在核对，原因未确认前不声称修复成功。Node 核心 36/36、官方 App 工具适配测试 1/1、Python mock 34/34 本轮通过。
- 第五次落点图显示 Save 坐标正确，但仍没有文件；第六次固定 return/foreground 返回明确 `delivery_failed`（modal 打开时正文窗口不能成为键盘前台目标）。两轮已停止、官方轮次终止且失败报告保留，没有盲重启同一轮。补充 Driver code 型失败识别与回归；最新 Python mock 35/35。保存用例仍未通过，下一步核对 owned modal 的真正输入目标；没有进入 C1 或缩减验收。
- 最终将固定确认键绑定到独立 owned sheet；第七次有正确文件但完成轨迹重复记录，仍保留 UNVERIFIED。修正为尝试与新观察证明完成分开，第八次 `c0_02_document_20261001_008` 独立 SUCCEEDED，16/30 raw。三个 GUI 汇总 3/3、计算器 9/9；文档前七次与滚动失败保留。阶段总结 `docs/stages/c0-02-summary.md` 已写，C0-02 完成；C1/C2 不提前登记成功。


## 阶段提交整理

本分支 c0-02 为用户在四阶段验收后授权整理的递进提交。guest 原阶段执行器保留并用于还原，适配器按阶段拆分、本地测试重新运行；没有重跑或改写原模型证据。下一阶段 c1，不计入本分支完成状态。
