# CUAgent 实际进度

更新：2026-10-02。主路线：[Harness最小可用底座 → Computer Use主线 → 通用增强/O0](Harness_Development_Plan.md)。下方“当前交付”及最新收尾记录代表当前状态；各日期过程中的未提交/未完成描述保留当时事实，不代表目前状态。

## 当前交付

| 项目 | 状态与证据范围 |
|---|---|
| 新仓库 | 公开 `9leaa/CUAgent`；四阶段分支已分别提交推送，默认 `harness-migration` 按本次授权快进同步最新阶段与文档；不创建PR/标签，远端以Git为准 |
| 旧仓库 | `9leaa/os_agent` 已归档，描述/主页指向新仓库；后续按用户要求将旧本地源码和Pi移至废纸篓，VM/镜像保留 |
| 设计与计划 | README、DESIGN、Harness_Development_Plan、AGENTS、COLLABORATION、MIGRATION已按Harness与Computer Use优先顺序改写 |
| 核心工具迁移 | 20个文件逐字节迁入；manifest记录来源类别和SHA-256，其中15个来自旧未跟踪文件 |
| 工具核心测试 | Node 24.9.0：最新本地回归 36/36 通过；属于无模型单元测试 |
| 本轮VM工具测试 | 最新 Python 103/103 执行层/mock/反例通过；不替代真实 VM 七故障、18 次与九计算器证据 |
| Harness版本 | 当前官方 Desktop App 0.2.0-rc.2 / 内置 Node 24.18.1，同版源码参考639ed015；初始 Web 固定源码00102833d / 0.1.7-alpha.2仅历史 |
| Harness A0最小底座 | 最新 Desktop 真会话/文件/直接与工具图片/标准取消/30 次持久预算回归通过；重启首回复错误和后续澄清保留，Web记录仅历史 |
| C0-01及C0–C3 | C0-01、C0-02、C1 与 C2 本地验收完成；C2 正式 18/18、七故障、九计算器及 A0/声明安全范围回归通过；C3 未做 |
| A1通用增强 | 三份文本、CSV和完整插件/会话体验待实施；不阻塞C0–C3 |
| O0 | 后置，未开始 |

## 2026-10-02：文档收尾与默认分支同步

- 四阶段已分别推送：C0-01 `be77dbd`、C0-02 `373e2d3`、C1 `46b4d47`、C2 `5d5383e`。此前 GitHub 首页仍显示旧 `harness-migration`，仅推阶段分支不会更新首页。
- 用户授权先做文档收尾和默认分支快进同步。修正 README 的 A0 Web/历史 mock/目录描述，同步 DESIGN 和开发计划的版本、现有能力及 C3 下一步；历史方案、失败和过程日志不倒改为成功。
- 文档修正提交追加于 C2；默认分支只做 fast-forward，不重写四阶段提交、不强推、不改默认分支设置，不创建 PR、标签或 C3 发布。检查文档链接、差异及远端 README/提交一致性，不以此次检查冒充重跑模型/VM。
- 本次仅变更文档及 Git 引用；虚拟机、Driver、SSH/VNC、运行配置和私有原始证据保持原状。

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

## 2026-10-01：进入 C1

- 新建 `c1-computer-use`，实施前写 `docs/stages/c1-design.md`，固定六类真实任务及前后各三次、相同模型/环境/预算的 36 次评测。C1 尚未实现或通过；不以 C0 的 12 次成功替代。
- C0 最终任务已冻结，bridge 无监听，已验证的残留 fixture 正常结束；VM 和用户接受的端口保持运行。不提交/推送，用户原未提交文件继续保留。
- 新增独立 `c1_cases.py` 固定六例、独立期望和完整 36 次 schedule；不自动注册或授予工具权限。注册表不可变、跨应用确为不同应用、前后各三次及恢复新观察要求有测试；当前 Python 无模型/mock 共 38/38。尚未开始 C1 baseline 真实任务，不将注册表或 mock 当作 C1 通过。
- C1 原生 fixture 与 `c1_bridge.py` 已实现六类任务；复用 C0 准入、预算、审计、停止和 HTTP，新增固定标题的 `vm_select_target`，切换后旧快照失效。跨应用输入只接受刚观察到的计算器值；GUI 返回记尝试，新观察证明效果后才记完成。官方 C1 preset 没有增加模型循环或开放默认工具。
- 启动前真实诊断：输入纠错 10 raw、窗口变化 13、弹窗第三次 17、跨应用 25、三页流程 18、失败后重新观察 14，均独立 SUCCEEDED。弹窗前两次 UNVERIFIED 保留（面板失焦隐藏/自动锁屏、重复完成记账）；这些诊断不计正式 36 次评测。VM 已重新解锁，限时两小时防休眠，未改永久系统设置。
- 当前 Python mock/注册表共 44/44，官方 App 工具适配测试 2/2，fixture 编译和签名通过。启动器核对 guest 六个 Python 源码与签名 fixture 二进制哈希，正式 phase 源码冻结；完整阶段前后各 18 次的基线自动串行运行已启动，尚未登记 C1 完成。
- 首个正式 baseline `c1_baseline_cross_app_20261001_001` 独立 SUCCEEDED，23 raw、20 个模型工具调用、约 52.9 秒；第二次真实会话已启动。源码不再中途修改，后续报告须保留全部 18 次，不用诊断替代，也不因单例通过宣布 C1 完成。

## 2026-10-01：C1 基线冻结与候选对照

- 正式 baseline 六类各三次共 18/18 独立成功，完整报告 `.runtime/runs/c1-baseline-report.json`。弹窗 raw 为 21/18/19，重复 Open 尝试为 4/2/2；真实弹窗效果每轮一次。全部原始会话与任务证据保留。
- 在基线全部终止后，依实施前方案增加默认关闭的观察提示；只在真实同 PID 可见确认窗口出现时，计预算地查询窗口清单，提示选择后重新观察。不自动切换或点击，不改变任务/fixture/模型/权限/30 次预算。
- after 18 次已启动，沿用同一模型和环境，源码哈希逐次冻结并核对 guest；目前跨应用三次独立通过。尚未完成全部 after 或 C1 总结，不能标 C1 验收通过。
- 离线报告校验固定 36 次、唯一 session、模型工具边界、源码一致性和独立 GUI/文件证据；默认启用须同时满足预定成本收益、各类成功不退步及单独安全回归，不能用成功率代替安全证明。

## 2026-10-01：C1 独立验收完成

- baseline 18/18、after 18/18，六类每轮 3/3，官方真实 session、请求审计及 guest 36 份账本/文件再次核对。原始证据保留，停止后无新增派发；两轮只有候选观察提示源码不同。
- raw 合计 295 → 286，累计时间 639.166 → 585.153 秒，正式轮次人工介入均 0。弹窗 raw 21/18/19 → 14/17/15，平均减少约 20.7%；默认仍关闭，待 C2 完整安全/恢复回归后决定。
- Python 53/53、核心 Node 36/36、官方 App 适配 2/2；离线 `c1-independent-comparison.json` 完整覆盖 36 次及实际官方 usage。阶段总结 `docs/stages/c1-summary.md` 已写，C1 完成，不宣称 C2 或发布完成。
- C1 suite 正常退出，全部任务冻结，guest bridge 无存活进程。VM/现有端口继续运行，未提交或推送。下一步建 C2 分支，先写可靠性方案。

## 2026-10-01：进入 C2

- 新建 `c2-reliability`，先写 `docs/stages/c2-design.md`，固定原计划 18 次、七故障、人工接管/取消/安全/恢复/反假成功及九计算器/A0 回归门槛。没有以 C1 成绩替代。
- 当前只有方案，C2 实现和验收尚未完成；不提交/推送，保留用户未提交改动、任务证据、VM 和现有端口。
- 新增 `c2_cases.py` 固定新 18 次 schedule、七故障具体证据、九计算器及 A0/安全 gate。三项注册表测试通过，Python 共 56/56；仅无模型定义验证，尚未实现恢复或执行 C2 真实故障。

## 2026-10-01：C2 接管/恢复控制初步实现

- 新增 `c2_bridge.py` 的独立 C2Task 扩展，不改 C0/C1 默认执行行为。控制 owner/epoch 持久化，停止使旧快照失效，在途/UNKNOWN 未核清不能接管；重启恢复 PID/窗口/传递上下文与原预算，但不恢复旧快照或自动准入。
- 开发侧恢复观察使用线程与 epoch 绑定的只读能力，只允许 list_windows/get_window_state，仍计原 30 次；恢复期间再次停止使该能力失效。交还须新观察、当前控制权、足够预算及无 UNKNOWN，模型重新观察，旧 session/epoch 拒绝。
- Python 65/65（新增九项 mock，含停止与恢复并发、重启、预算、UNKNOWN/悬空 dispatch、会话串扰、坏 epoch 和非法 session）；不能作为真实模型或全故障验收。
- 独立 VM 目录 `/Users/mvpagent/CUAgent-c2-20261001` 部署，host/guest C2 两源码 SHA 一致。`c2_control_live.py --run c2_control_20261001_001 --approve-task` 真实 Driver 诊断 PASS：3 次初始请求 → 5 次接管后恢复观察 → 6 次交还后新观察，三个 snapshot 不同，最终 stopped。host 独立读回 trace/报告核对每次派发、结果、控制 epoch 与预算；诊断 fixture 正常结束，VM 保持运行。
- 该诊断无模型、无业务提交，明确 taskStatus UNVERIFIED，不计入 C2 18 次或七故障完成。模型/HTTP 控制通道集成、UNKNOWN 独立对账、真实七故障与正式评测/回归仍待完成；尚未写完成总结，不提交/推送。
- 诊断后收紧 session 格式与 epoch 的整数类型，新增反例通过；该额外参数校验尚未重跑 live，原诊断源码哈希不倒改，新版须在后续集成中重新部署验证。

## 2026-10-01：C2 官方模型控制集成与一次 UNKNOWN 恢复

- C2 HTTP 分离 model/verifier/control 三种能力；只有开发控制通道可接管、恢复观察、独立对账和交还，模型配置不含 control/verifier token。官方插件携带真实 session/epoch，停止响应立即关闭 guard，旧会话/epoch 不能继续派发；没有增加模型主循环。
- 正常模型诊断 `c2_model_gate_20261001_001` 独立 SUCCEEDED，11/30 raw、8 个模型工具调用；实际模型为 `deepseek-account/deepseek-flash`。六项实际 HTTP 能力拒绝检查通过，拒绝不消耗合法任务的 Driver 预算。
- 故障 `c2_timeout_gate_20261001_001` 在实际 Driver Submit 返回后丢弃响应；首次官方会话真实 error，原 UNKNOWN 保留。开发侧新观察结合实际提交文件、完整轨迹及 fixture 效果确认已生效一次，再明确交还新官方会话；没有重新输入/提交，没有清零预算。
- 恢复会话真实 completed，独立 GUI、result.txt、读回和期望一致，最终 SUCCEEDED，原任务共 19/30 raw；两个真实会话共 10 个模型工具调用。恢复首次 prompt RPC 拒绝，错误细节未保存；独立核对新会话仍无用户消息/轮次后向同一 session 派发，未重建任务或重复动作。不能据此声称 RPC 根因已确定。
- `c2_fault_audit.py` 只离线审查这一响应丢失故障；核对原 Submit、UNKNOWN、不同新快照/真实 AX/截图、同 PID/窗口、单次效果、预算连续、停止后的只读恢复和显式交还。VM 原证据重新审计 PASS。新增九项合成反例测试，不能冒充真实故障注入。
- 当前 Python 78/78（含新增审计反例及进程退出钩子 mock）；官方 App 适配上轮 3/3。正常与超时故障 run 均已冻结并结束对应 executor/fixture，VM 和用户接受的 VNC 端口保持运行。没有提交/推送。
- 开始下一故障：开发钩子在实际首次观察和目标绑定持久化后退出 VM 执行进程（exit 85）；重启必须同 run、保留预算、默认暂停且旧快照不可用。单元测试不替代真实进程/模型恢复证据，实际验收结果另记。
- 进程退出诊断 `c2_exit_gate_20261001_001` 实际进入退出钩子，观察原 executor 已不存在；同 run 重启后 paused、3 次预算，能力拒绝不新增派发，开发恢复观察后共 5 次。恢复程序没有刷新重启后旋转的 model token，官方恢复会话工具实际 Forbidden、没有 GUI 输入；最终 UNVERIFIED 保留，不能计故障恢复成功。修复私有恢复程序：重新读取当前 model token，仍不传 verifier/control token，prompt 请求 ID 与内容先持久化，RPC 拒绝细节以后留私有证据。新诊断 `c2_exit_gate_20261001_002` 已启动，结果待独立核对。
- 本轮直接执行 TypeScript 测试因未经过官方 App 依赖打包而 ERR_MODULE_NOT_FOUND，不计通过；使用现有 `build-c0-tests.mjs` 按官方 App 同版库重新打包后，官方 Electron Node 3/3 通过。未安装另一版本依赖或修改 App 包。
- 修复后 `c2_exit_gate_20261001_002` 首次模型实际触发 executor 退出（当时累计 4 raw），观察确认无该 run executor；同 run 重启仍 paused、4 raw。新恢复观察两次实际请求，明确交还 epoch 4/新官方 session 后恢复业务；最终独立 SUCCEEDED，14/30 raw、两个会话共 12 个模型工具调用，Submit 实际效果一次。独立账本审查预算连续、结果完整、无 UNKNOWN、重启至交还期间仅两次只读恢复请求、目标 PID/窗口未变，以及新界面/文件/期望一致。两会话真实 terminal、任务冻结并结束对应 executor/fixture；VM 仍运行。原会话虽 completed，但没有业务成功证据，不能把框架 completed 当作首次任务成功。
- 当前响应丢失与进程退出两类有真实恢复通过证据；窗口关闭、人工 GUI 改文档、模型失败、真实权限撤销、预算耗尽，以及新 18 次正式评测、九计算器和 A0/完整安全回归未完成。C2 仍未验收，不写完成总结。

## 2026-10-01：C2 窗口关闭与同任务恢复

- 实现前补充 `c2-design.md` 窗口故障细化。fixture 只有显式 `--keep-alive-after-close` 的输入纠错测试保留进程；关闭后重开创建新窗口，复用原内容/效果，不重新创建任务或覆盖旧文件，默认 C0/C1 行为不变。
- 独立开发控制操作只在停止、人类控制权、无在途/UNKNOWN、当前 epoch 下获准。Close 必须是实际新截图/AX 中同 PID/窗口、唯一标题栏按钮；关闭点击和新窗口清单都计预算。重新打开前核对旧窗口消失和固定可执行文件身份；模型/verifier 不能调用关窗或重开。
- 首轮 `c2_window_gate_20261001_001` 已真实关闭原窗口，但 Driver launch 只激活进程，没有新窗口；两次新观察确认仍无目标。最终 UNVERIFIED、11 raw 保留，不继续盲重开。模型首次因受控暂停出现真实 error，不称模型服务故障。
- 修复开发恢复路径：固定 `/usr/bin/open -a /Users/mvpagent/Applications/CUAgentFixtures.app`、不使用 shell/任意路径/新实例；原生请求计预算、在途与结果，超时为 UNKNOWN，重启仍禁止交还。返回只说明已请求激活，不能当窗口证明；必须实际新 Driver 观察后继续。
- 新诊断 `c2_window_gate_20261001_002` 官方真实模型恢复并独立 SUCCEEDED，22/30 raw、两个会话共 8 个模型工具调用；原 PID 23069，关闭窗口 784，恢复窗口 791，Submit 效果一次。交还后实际旧快照请求 409/Fresh observation required，被审计为拒绝，没有旧窗口输入；八项 HTTP 能力隔离检查通过。
- `c2_window_audit.py` 独立读回实际 guest 账本、效果/产物/验证文件 PASS；核对原新截图中的 close 按钮、真实点击与旧窗口消失、同 PID 新窗口、恢复前新观察、持久预算和完整结果/拒绝。五项合成反例不能代替真实故障。本轮 Python 87/87，fixture 编译/签名和 guest 严格签名核对通过，`git diff --check` 通过。
- 诊断有明确开发介入，控制/GUI动作均在账本，不能用启动 metadata 的初始零值声称零介入；私有 `window-fault-audit.json` 另记介入类型。两官方会话真实 terminal，任务冻结并退出确切 executor/fixture；VM 与 VNC/SSH 保持运行，不提交/推送。
- 当前三类故障有诊断通过证据，版本/源码哈希逐 run 保留；不把不同版本诊断拼成同版完整验收。人工 GUI 改文档、模型失败、真实权限撤销、预算耗尽、正式 18 次、九计算器、A0 和完整安全回归仍待完成。C2 不登记完成。

## 2026-10-01：C2 真实文档接管、正文纠正与 GUI 保存

- 依实施前方案将持久控制权提为 `C2ControlMixin`；`C2Task` 保持 C1 六例后端，新增 `C2DocumentTask` 复用 C0 原生 NSTextView、owned 系统保存面板和固定文件规则。文档仅为故障诊断，不加入或替代六例正式 18 次。
- 首次模型真实输入原正文后停止；开发侧只能在接管、无在途/UNKNOWN、当前新观察的固定 Document Body 下编辑，操作计原预算，模型不能调用此控制入口。交还前必须实际观察干扰正文；恢复后独立要求新会话观察到干扰，再纠正正文、新观察、GUI Save Document/Save 和真实文件核对。原始两次模型输入保留，不删首轮轨迹。
- 首轮 `c2_document_gate_20261001_001` 确认 Driver type_text 会在 NSTextView 追加。实际新观察为原文加干扰文本，恢复条件拒绝，UNVERIFIED、11 raw 保留；新建的空恢复 session 未派发任务，不将其算作恢复通过。
- 固定 Driver `describe set_value` 确认原生 AXValue 支持；只在 C2 文档唯一新鲜正文与两个固定值下使用。实际请求记录为 set_value，不伪装 type_text；未增加模型通用 set_value/shell/键盘工具，C0/C1 默认 raw 仍拒绝。新增超时 UNKNOWN 跨重启保留和越权反例。
- 新诊断 `c2_document_gate_20261001_002` 独立 SUCCEEDED，25/30 raw、两个官方会话共 13 个模型工具调用，实际模型仍 deepseek-account/deepseek-flash。新观察先确认固定干扰正文，恢复模型再纠正，动作完整 Save Document/Save；真实 task-note.txt、新 Saved 界面、result.txt/读回和预定正文一致。原首次错误会话与全部证据保留。
- Python 94/94（包括既有全部控制/UNKNOWN/窗口测试和七项文档 mock），`git diff --check` 通过；无模型测试不替代 GUI。私有 `document-fault-audit.json` 只读重核原账本、实际 GUI/保存完整判据及开发介入，不构造 Task、不改 guest 证据，亦不是完整 C2 发布报告。
- 两官方会话真实终止，任务冻结并退出确切 executor/fixture；VM、SSH/VNC 保持运行，未提交/推送。控制层变化后旧故障需在最终冻结版重新回归，不能把不同版本绿色诊断拼成同版全通过；模型失败、真实权限撤销、预算耗尽、真实在途停止、正式 18 次、九计算器和 A0/完整安全回归仍未完成。

## 2026-10-01：C2 官方模型流故障恢复

- `c2_model_error_gate_20261001_001` 在官方 `llm/stream` 项目钩子、provider 调用前注入单次错误；此前真实 VM 图片已进入上下文。原官方会话以明确受控错误终止，任务暂停在 4 raw，无在途或 UNKNOWN；不将此测试称为服务商宕机。
- 九项实际 HTTP 能力隔离检查通过且调用预算未变。开发接管、原预算新观察、明确交还新官方会话后，模型重新观察并完成 Submit；独立 SUCCEEDED，14/30 raw、两会话共 9 个模型工具调用，实际效果一次。单次故障标记跨 App 重启保留，没有再次注入。
- App 重启后首次 prompt 返回 `gateway/service-unavailable`，错误细节保留。独立检查同一新会话尚无用户消息/轮次后，使用相同 session 和持久 request ID 派发；不新建任务/会话，不重复已准入的 prompt。恢复完成及原错误会话均真实 terminal。
- 私有 `model-fault-audit.json` 只读重核实际账本、原错误、恢复前后观察、连续预算和单次效果 PASS；原任务已冻结，对应 executor/fixture 已不存在，VM 与 VNC 保持运行。官方 App 同版打包适配测试 4/4、Python 94/94 属于无模型测试。
- 目前五类故障有历史版本诊断通过证据，不拼成冻结同版完整验收；真实权限撤销、预算耗尽、真实在途停止、正式 18 次、九计算器和 A0/全安全回归仍待完成。C2 未完成，不提交/推送。

## 2026-10-01：C2 实际预算耗尽与跨进程保持

- 先补充预算诊断方案，再新增 `c2_budget_live.py`；复用 C2Task/真实 Driver，在固定输入纠错窗口连续观察，未设置 used、未伪造 dispatch、未执行业务输入或提交。
- `c2_budget_gate_20261001_001` 实际 30 raw（一次 launch、一次窗口清单、28 次不同新观察）；第 31 次、停止后观察、开发恢复观察、换会话交还均 BLOCKED，未新增派发。第二个独立 Python 进程 PID 25179（原 24815）读取同一账本，仍 30/30、paused、无可用旧快照；重启后观察/恢复/交还仍被拒。
- 离线 `budget-audit.json` 核对 30 个唯一连续 dispatch/result、28 张真实 PNG/不同快照、七项拒绝、同源码与不同进程及停止后零派发 PASS。安全 gate 通过，业务保持 UNVERIFIED；没有官方模型会话，不计正式 18 次，也不替代 A0 的真实模型预算回归。
- 新增五项无模型反例（缺结果、重复观察、同进程冒充重启、伪成功产物等）；Python 99/99、`git diff --check` 通过。原账本/报告仍留 VM，并独立复制至私有 host 目录；诊断进程已正常结束，对应唯一 fixture PID 24961 已退出，VM 和端口未改。
- 目前六类故障有历史版本真实诊断证据；真实权限撤销、真实在途停止、最终同版故障回归、正式 18 次、九计算器和 A0/完整安全回归仍未完成。C2 保持未验收。

## 2026-10-01：C2 真实 guest 权限撤销与恢复

- 实施前补充方案；新增只负责首次实际观察后暂停的 `permission_revoke_after_observe`，不模拟权限错误或自动改变 TCC。官方原会话在 3 raw 后真实 error 终止，开发接管后，经独立 guest VNC/测试管理员授权将 CuaDriver Accessibility 真正关闭。
- 实际设置 Off 截图与 Driver daemon 自身权限 false 一致，Screen Recording 仍为 true。同一任务的真实恢复观察返回 409，预算从 3 到 5；Driver 返回原窗口 `ax_window_unresolved`、空 AX 树和无 snapshot，执行器拒绝使用。没有 GUI 输入、结果文件或成功报告，不换工具绕过。
- 经同一 guest 设置恢复原 On，新 VNC 截图与同 daemon PID 1144 的权限 true 一致；关闭设置窗口后新 Driver 观察核对原 fixture PID 25440/窗口 828。明确交还 epoch 4、新官方会话重新观察并完成任务，独立 SUCCEEDED，15/30 raw、两会话共 8 个模型工具调用、Submit 效果一次。九项实际 HTTP 能力隔离检查通过且预算不变。
- 私有 `permission-fault-audit.json` 只读核对权限前/关闭/恢复时间、真实不可用观察、连续原预算、停止期间四次只读恢复请求、新模型观察后输入及实际文件/效果 PASS。开发介入明确记为两次权限切换、一次管理员确认、接管和交还，不用 metadata 初始零值宣称零介入。
- Python 100/100（新增暂停/重启 mock，不代替真实权限证据）；对应任务冻结，executor/fixture 已不存在，Driver 原权限已恢复。未修改宿主 TCC/SIP、全盘访问、SSH或端口；VM 保持运行。七类故障已有不同版本真实诊断证据，但真实在途停止、最终同版全部门槛、正式 18 次、九计算器和 A0/全安全回归仍未完成，C2 不登记完成。

## 2026-10-01：C2 真实在途停止及当前版预算复验

- 实施前补充在途方案，新增 `c2_inflight_live.py`。固定正文由真实 Driver 输入；仅在实际 Driver 返回之后、执行器 result/清除 inflight 之前暂存返回。`c2_inflight_gate_20261001_001` stop 约 0.000685 秒返回并携带唯一在途 call-id，新请求和提前接管均 BLOCKED、无新增派发。放行原返回后只记录一次 result，才允许接管；新 Driver 观察确认同 PID/窗口正文 cedra-42 → cedar-42。
- 独立离线审查 dispatch→实际返回暂存→stop→原 result→takeover→新观察的顺序通过，共 6 raw。无 UNKNOWN、无业务提交/结果文件，业务 UNVERIFIED；这是实际执行层停止诊断，不称官方 UI 取消、网络超时或模型业务成功。三项新增 mock/反假证据测试不替代真实 GUI，Python 103/103。
- 添加真实权限暂停钩子后，重跑 `c2_budget_gate_20261001_002`：当前相同 C2 源码下实际 30 次、七项拒绝、独立进程重启预算不变、停止后零派发，再次 PASS。新原账本/报告保留，不倒改首次预算证据。
- 两诊断均已停止，独立进程已退出；准确核对并结束对应 fixture PID 25930/26137，VM/Driver/SSH/VNC 保持原状态。最新权限、预算和在途证据同 C2 bridge 哈希 `3d98634cc7ec83c7b594ae431a5f4d7cdd984a80fb389e1990c425f8cf7a605f`；其余旧故障仍需当前版回归，不把历史绿灯拼成最终同版全通过。正式 18 次、九计算器和 A0/完整安全回归未完成，未提交/推送。

## 2026-10-01：C2 冻结版故障回归与正式评测准备

- 私有 `c2-final-version.json` 固定 16 个源码/策略/fixture 源及实际签名二进制、App 0.2.0-rc.2、内置 Node 24.18.1、原模型 deepseek-account/deepseek-flash、30 raw 和默认关闭的 C1 提示。首次冻结检查发现 guest 尚无仅作注册表的 c2_cases.py，补部署原文件后独立哈希核对通过；未改运行策略或旧证据。
- 当前版新真实故障：响应丢失 `c2_timeout_gate_20261001_002` 16 raw，进程退出 `c2_exit_gate_20261001_003` 15，窗口关闭 `c2_window_gate_20261001_003` 21，人工正文修改 `c2_document_gate_20261001_003` 23，模型流错误 `c2_model_error_gate_20261001_002` 13，均原预算内恢复、实际官方会话终止和独立 GUI/文件/轨迹通过。模型错误为项目扩展层注入，不称服务商宕机；进程退出首会话虽 completed，不称业务成功。
- 真实退出前后检查原 executor 不存在、新进程 PID 27060、同 run 默认 paused/3 raw；新观察后明确交还，源任务和预算不重建。窗口真实旧 ID 879→新 886、同 PID 27396；旧快照请求实际 409。文档原输入/人工 set_value/恢复纠正两次输入及 GUI 保存完整保留。
- 模型恢复首 prompt RPC 拒绝细节保留；核对同一新 session 只有四条设置事件、没有用户消息/轮次后，沿相同持久 request ID 投递。恢复完成前另实测旧真实会话携带当前 epoch、以及新会话携带旧 epoch 均 409；当时任务为 model-owned/未停止，预算 12→12，不以已停止拒绝冒充会话隔离。
- `c2-faults-report.json` 将上述五项与当前版真实权限撤销（15）、预算耗尽（30，业务 UNVERIFIED）和在途停止（6，业务 UNVERIFIED）按哈希核对，七故障与在途 gate PASS；不代替正式评测或完整发布报告。原失败及历史版本诊断继续保留。
- Python 103/103、Node 核心 36/36、官方 App 同版适配 4/4、git diff --check 通过，均属于无模型测试。正式 runner 只负责生命周期，不替换官方主循环；先固化六类×三次唯一 run schedule，formal/diagnostic 分开、禁止补跑替换，并逐任务核对冻结源码和 fixture。正式 18 次开始，尚未登记通过；九计算器、A0 和全安全/完成审计仍待完成。

## 2026-10-01：C2 正式 18 次与原始证据复核通过

- 冻结六类各三次，18/18 独立 SUCCEEDED；每类 3/3，原全部 run/session 和失败诊断保留。跨应用 raw 23/25/24，弹窗 15/16/18，窗口变化 14/14/13，输入纠错 12/11/11，长流程 16/16/19，失败后重新观察 13/14/15；共 289 raw、233 模型工具调用。每次仍受原 30 次预算和默认关闭的提示策略约束。
- 第 2 次跨应用在创建会话前遇到 `sessionController` 未注册，官方 gateway 在调用方法前拒绝。检查 executor PID 28841 仍存活、used=0、官方只读 session list 无该 workspace 会话后，在同一 run 准入一次；未重启 VM/executor、未补跑替换。开发生命周期程序增加只读服务就绪检查、创建身份和 prompt request ID 持久化，实际 RPC 拒绝另留私有记录，不改冻结适配/执行代码。初次只读 list 参数名误用被 gateway 拒绝，按实际 descriptor 改为 `_request`，没有工具派发。
- 正式 GUI 接管 0 次，启动恢复 1 次，分别统计。全程 host 计时 1037.599 秒，包含该启动等待，不删除异常耗时。官方实际 usage：input 638368、output 31420、cache-read 5842806、cache-write 0、total 6512594；货币费用 unavailable，未猜费用。
- 私有 `c2-formal-independent-audit.json` 逐个读回 18 个原官方会话、guest 原 trace/verification/result 和真实 PNG；核对唯一会话、原模型/工具清单、冻结版本、连续预算、完整 result/error、无 UNKNOWN/接管、停止后零派发及期望一致 PASS。审计开发初次将执行器约定的末尾换行当作不一致、随后宿主 Python 3.9 不支持 ISO `Z`；修正比较与时间解析后重读全部原证据，没有修改原文件或报告。
- 本轮 Python 103/103、Node 核心 36/36、官方 App C0/C2 适配 4/4、A0 原执行层 7/7；新增私有官方注册表集成实测 16 类路径/类型/大小/链接/覆盖/审计逃逸拒绝，18 次含两个合法文件请求，原内容不变。上述属于无模型执行层回归，不冒充模型任务。
- 九计算器的新真实回归已开始，使用冻结 guest 源和新的 `c2_calc_<case>_20261001_001`；A0 真会话/文件/两种图片/取消/预算及最终全安全映射仍待完成。C2 尚不登记完成，不写完成总结；VM、权限、SSH/VNC 和端口保持原状态，未提交/推送。

## 2026-10-01：C2 回归、最终安全审计与本次目标完成

- 新九计算器全部独立成功，raw 按加/减/乘顺序 20/16/22、20/20/20、20/16/18，共 172；固定模型、当前冻结 guest 源，真实按钮/新显示/result.txt/读回/期望一致。未使用旧 C0 成绩替代，结束后各任务冻结，executor 退出。
- A0 新 run `c2_a0_20261001_001` 三轮修订与同 session/App 重启、原模型、文件字节读回、工具返回及直接输入的随机 PNG 像素/答案全部核对。重启首回复错误声称无记忆，实际原三轮用户消息完整；保留原回复为 UNVERIFIED，同会话仅澄清依据先前用户消息后正确回答，不告诉答案、不重建会话。文件 SHA-256 `531955f7dba60e127825edfdf4c1c25e5298d70235ef89962c8d610d12aaf58a`。
- 真实 A0 第 9 轮工具派发后由标准官方 cancel API 形成 aborted/user，取消之后旧轮次无新派发。随后明确新轮次用满原 30 次；第 31 次与 App 再重启后的请求均实际拒绝，最终预算 30，未重置。API 取消不冒充本轮点击 UI Stop。审计原先错误要求预算耗尽后仍恰好五工具，修为合法子集及最初完整清单；实际请求只有原五工具或空集、没有额外工具，原模型不变。
- `c2-safety-audit.json` 映射全部 13 个声明安全 gate，结合真实七故障/在途/HTTP/会话隔离和执行层反例 PASS；最终 Python 103/103、Node 36/36、官方 App C0/C2 4/4、A0 原执行层 7/7，另完整文件边界注册表 1/1/16 类拒绝。保存实际命令输出，冻结版核对、原 Driver 权限和 git diff --check 通过；不声称所有反例均为真人 GUI 或整机安全认证。
- 原 C0 的 13 个成功任务和 C1 的 36 个正式任务，当前重新读取原官方会话/独立结果通过；四分支 reflog 与四份方案创建时间核对，方案均在对应阶段实施前建立。最新 C2 总结 `docs/stages/c2-summary.md` 已补齐做了什么/怎么做/怎么验证及失败、用量、限制；README/PROGRESS 同步。原 C0/C1 总结保留其当时范围，不倒改历史为全项目成功。
- 本次 C0-01、C0-02、C1、C2 本地阶段目标完成；C3 干净部署、第二人扩展/复现、发布仍未做。四分支创建但没有独立阶段提交，改动仍未提交/推送；不冒充每分支已保存可 checkout 的阶段代码快照。
- 当前普通 mvpagent、SIP enabled、无 virtiofs 宿主挂载、SSH 仅 mvpagent，原 VM/VNC/端口保留；没有活动 Computer Use executor，Driver 原权限已恢复。App 留在 A0 回归配置，旧 run 30/30，开始新任务必须使用新 run/明确配置。私有原始证据和失败全部保留，不公开账号、token、原截图或完整会话。

## 2026-10-01：按用户授权整理四阶段提交

- 用户在本地验收完成后明确授权分别提交、推送 C0-01、C0-02、C1、C2。按依赖建立四个递进代码提交，保留各阶段方案和总结，不创建 PR、标签或合并主分支。
- 前序执行器读取保留的 guest 阶段源码；共享适配器、fixture 与阶段文档按对应能力拆分。每个整理后的树重新执行无凭证本地测试，不声称完整 Git 快照在原验收时已经保存，也不将此次本地测试冒充重跑真实模型/VM。
- 仅提交公开源码、测试、模板和脱敏文档；私有 `.runtime`、原始会话/截图、凭证、VM 和未公开证据不上传。VM、Driver、SSH/VNC 与应用运行配置不变。提交与远端结果以实际 Git 记录为准。

## 后续更新规则


每轮记录阶段、版本、文件、实际命令、运行环境、成功与失败证据、未测项和下一步。只有独立验收通过才更新阶段状态。不要恢复旧文档中“自动提交PR”“默认codex前缀”或“旧Git历史一定可恢复”的假设。
