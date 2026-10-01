# Harness A0 接入与边界

当前收口状态（2026-10-01）：C0-01、C0-02、C1、C2 本地验收完成，C2 正式 18/18、七故障、九计算器、A0 和声明安全范围回归通过，见 [C2 总结](../../docs/stages/c2-summary.md)。下文开发过程中的“待完成”和初次诊断次数仅是历史记录，不替代最终冻结版结果；C3 尚未完成。

2026-09-29 已建立独立 `cuagent-a0` profile 和启动脚本，固定版源码见 [上游参考版本](upstream-reference.json)。下文保留安装过程与早期设计记录；当前有效状态以本节和 [PROGRESS](../../PROGRESS.md) 为准。

## 当前入口：官方 Desktop（更新 2026-10-02）

用户要求移出旧 Web 并安装官方桌面 App。首次安装包为 `0.1.7-rc.2`；实际验收 App 已更新到 `0.2.0-rc.2`，安装来源与历史签名记录见 [PROGRESS](../../PROGRESS.md)。完成下节 A0 构建与配置、正常退出已有 App 后，A0 项目入口为：

```bash
/bin/zsh /Users/zhangchengjie/CUAgent/agent/harness/start-desktop.sh
```

启动脚本使用专用 `.runtime/desktop-home`。旧 Web 的源码、home、依赖、日志、启动脚本和配置移至 `/Users/zhangchengjie/Documents/ChatGPT/osagentmvp/retired-dsh-web-20260930`，其中 `archive-manifest.json` 记录每项原路径和恢复方法。任务运行证据保留在 `.runtime/runs/`。可复用的工具与策略源码仍在本目录；旧 Web 的真实通过记录不构成 Desktop 验收，不复制旧凭证或会话。

官方 Desktop 是 Electron 壳，内部继续使用共享 Web 客户端和 Harness Host；其受管 `desktop` profile 与 Web 的自定义 profile 不同。安装之后已另行完成 Desktop A0 项目工具、模型、文件、工具图片、停止与预算验收；Computer Use 和 VM 验收仍独立进行。以下固定源码安装和 Web 接入记录为历史，所列旧 `.runtime/harness` 路径现已归档。

## Desktop A0 配置与运行

当前已验证 App `0.2.0-rc.2`，六个项目适配插件编译到专用 desktop profile，官方 App 包未修改。构建依赖仅用于编译与合并 YAML，固定版本：

```bash
cd /Users/zhangchengjie/CUAgent
npm install --prefix .runtime/desktop-build-tools --ignore-scripts --save-exact esbuild@0.28.1 js-yaml@4.3.1
node agent/harness/build-desktop-plugins.mjs
node agent/harness/configure-desktop.mjs
# 先退出 App；指定新的 run-id 开始新验证
agent/harness/start-desktop.sh desktop_a0_new_run
```

configure 保存原 patch 备份，合并项目限制，保留账号模型/UI 设置。不要迁入旧凭证。Launcher 检查 App 版本和运行状态；版本变化先重新核对接口。不传 run-id 会生成时间戳；恢复同次运行必须传原 run-id，30 次预算不会重置。工具根目录是 `.runtime/runs/<run-id>/workspace`，在 App 中添加该目录作为测试工作区。

Desktop A0 初次验证见 `.runtime/runs/desktop_a0_20260930_001/verification.json`；最新 C2 回归 `c2_a0_20261001_001` 已核对真实文件、工具及直接输入图片、标准取消和持久预算，见 [C2 总结](../../docs/stages/c2-summary.md)。两旧 run 均已耗尽；新任务必须新 run。直接图片经官方 prompt API 验证，不冒充本轮人工点击上传按钮；VM Computer Use 使用下方独立配置。

## 历史 Web 固定基点（2026-09-23）

源仓库 `deepseek-ai/deepseek-harness`，commit `00102833dfaee1da9f48a3a8eae9d34005a75218`，源码版本 `0.1.7-alpha.2`。Node要求 `^22.19.0 || >=24.0.0`，包管理器 `pnpm@11.7.0`。本机Node 24.9.0（macOS arm64）已通过完整源码构建及CLI版本/帮助检查；尚未验证Web启动和真实模型。

初始实现选择固定源码及其lockfile，构建输出放忽略目录。源码下载后遵循其AGENTS与LICENSE；依赖安装/构建和模型执行分别记录。npm latest=0.1.5-rc.2与当前源码不一致，不能混用API。

## 历史 Web A0 实施顺序

1. 已完成固定源码构建和launcher help/版本检查；独立设置 `DSH_HOME`，不用默认个人配置。当前 A0 profile 已固定模型和策略；开发凭证只保存在本地，不入库。
2. 根据官方Web模板创建项目profile，在启动模型前展开有效配置。第一次创建与已存在profile的启动参数分开处理。已完成。
3. 禁用Web默认standard/PTC/Cordis/minimal presets及不需要的执行插件，注册项目专用preset。A0只允许list/read/write、图片探针和无副作用算术诊断工具；CSV工具等通用增强排在A1。已由真实请求核对五工具清单。
4. 关闭独立的DeepSeek session-log contributor和OTel会话上报，复核插件管理、终端、网络与配置覆盖入口。
5. 在Cordis插件中注册最小工具，最终执行guard做fail-closed检查；再验证官方Web中的模型、会话、一个受控文件任务和两种图片路径。达到最小门槛后优先接C0真实桌面，不等待CSV完整业务流程。

官方CLI有 `--profile`、`--from-default-profile`、`--patch`、`--dump-config` 等入口。创建自定义profile时可从web模板初始化；同一profile已经存在后不能重复传初始化参数。它们是固定源码文档提供的机制，不是本项目已验证的启动命令。

配置补丁替换整个config块。实施时必须保存最终展开结果，不能从一段YAML推断全部生效配置。

## 本地安装与检查（2026-09-23）

源码与构建产物：`/Users/zhangchengjie/CUAgent/.runtime/harness`。项目本地 pnpm：`/Users/zhangchengjie/CUAgent/.runtime/toolchain/node_modules/.bin/pnpm`，未全局安装。

```bash
cd /Users/zhangchengjie/CUAgent/.runtime/harness
../toolchain/node_modules/.bin/pnpm install --frozen-lockfile --store-dir ../pnpm-store
../toolchain/node_modules/.bin/pnpm run build
DSH_HOME=/Users/zhangchengjie/CUAgent/.runtime/harness-home \
  ../toolchain/node_modules/.bin/pnpm dsh --version
DSH_HOME=/Users/zhangchengjie/CUAgent/.runtime/harness-home \
  ../toolchain/node_modules/.bin/pnpm dsh --help
```

以上安装时通过。锁文件SHA-256：`b86256be5afec5814a404747893cab392a73b40901d14fa8135f663fb42c8d40`。上游源码安装后已应用下面记录的本地补丁，工作树不再干净。独立home、workspace、runs已建立；没有配置API Key、授权桌面或修改个人配置。

本地记录：`.runtime/harness-installation.json`、`.runtime/harness-build.log`、`.runtime/harness-install.log`（后者为构建后的离线锁文件复核）。首次安装在CLI产物生成前提示三个SDK/desktop workspace的`dsh` bin链接缺失；构建后离线install未补建它们。已验证的入口是上述根目录`pnpm dsh`，这些子包入口未验收。构建另有上游弃用项及bundle体积警告，不影响本次退出码为0。全部`.runtime`内容被Git忽略，不公开上传。

## C0/C1/C2 专用入口

方案见 `docs/stages/c0-01-design.md`。guest 先以新 run-id 启动受控 bridge，完成授权、登录和新窗口观察；开发侧为对应 run 建立 `.runtime/runs/<run-id>/c0-connection.json`（0600，仅固定私有 VM URL 和 model token，不含 verifier token）。不要把 token 放进 prompt 或 Git。

正常退出现有 App 后，使用官方 Electron Node 构建 `build-desktop-plugins.mjs --c0`，运行 `configure-desktop.mjs --c0`（保留账号/UI项并备份 patch），再用 `start-c0-desktop.sh <run-id>` 启动。C0 preset 只提供 `vm_observe`、`vm_click`、`vm_write_result`、`vm_read_result`；取消传 guest stop。每任务 raw 30 次由 guest 计数，审批、白名单、轨迹与独立验证仍在 guest。

恢复 A0 时重新运行 `configure-desktop.mjs`，正常退出后使用原 `start-desktop.sh`；不删除任何旧任务账本。C0 的独立验证必须走开发侧 verifier token，不能由执行模型声明成功。2026-10-01 C0-01 与 C0-02 的真实模型/VM 用例已经通过，见阶段总结；此入口不自动证明后续可靠性。

C0 GUI 配置使用 `configure-desktop.mjs --c0-ui`；字段输入、滚动仅按固定任务注册。C1 配置使用 `configure-desktop.mjs --c1`，固定六类来自 `tools/mac_vm/c1_cases.py`，guest 显式运行 `c1_bridge.py --run <new-run> --case <reviewed-case> --approve-task`。只有 C1 注册 `vm_select_target`，只接受当前任务审查过的完整窗口标题；切换后必须新观察。启动器仍为 `start-c0-desktop.sh`，不增加第二套 Agent 循环。

C1 观察提示为开发侧 `CUAGENT_C1_OBSERVATION_HINTS=1`，默认关闭，仅在 popup 主窗口观察到真实 owned Confirmation 窗口时提示下一步；查询窗口也计 30 次预算，不自动点击。前后 36 次及独立核验结束前不宣称 C1 完成。离线汇总命令：`python3 tools/mac_vm/c1_report.py --runtime /absolute/private/runtime --output /absolute/private/new-report.json`；它核对实际官方会话与请求审计，缺任何固定轮次即失败，原报告不覆盖。

C2 使用 `configure-desktop.mjs --c2` 与同一 `start-c0-desktop.sh`，模型工具集合不新增开发控制/验证能力。私有连接标记 `stage: c2` 和当前 epoch，每次实际请求附官方 session ID；响应停止后根 guard 关闭，交还新 session 必须由开发控制通道明确授权且重新观察，原任务预算保持。最终冻结版七故障、正式 18/18、九计算器及 A0/声明安全范围回归已通过；原失败与 UNKNOWN 保留，见 PROGRESS 和 C2 总结。

C2 文档故障复用原五个 VM 工具（观察、点击、正文输入、写/读 result），不提供模型手动改文档或通用 set_value。开发控制编辑后，官方新会话重新观察、纠正正文并经系统保存面板保存；真实独立诊断 25/30 raw 通过，首次追加失败保留。内部正文替换受新观察/固定内容/原任务预算约束，未增加另一 Agent 循环；不将文档诊断当正式六例之一。

C2 单次模型流故障由私有连接 `modelFault: after_first_observation` 控制，不接受模型 prompt 开启。真实工具图进入上下文后，在官方 `llm/stream` 项目钩子、provider 调用前持久化私有标记并抛错；先停止 VM 新派发。原官方 error、明确接管及新官方会话恢复有真实独立通过记录（14/30 raw），不是服务商停机证明。默认关闭，恢复/重启同 run 不再注入。官方 App 同版库打包适配测试 4/4 只验证插件行为，不冒充完整 C2 或真实模型验收。

C2 真实权限撤销诊断在 guest 关闭再恢复 Driver Accessibility；恢复观察确实因 AX 不可用被拒，原预算内新观察/明确交还后官方新会话完成业务，独立 15/30 raw 通过。撤权由独立开发 VNC 完成，受测模型没有这个绕过入口；不操作宿主权限。不同版本初次诊断不能拼成同版成绩；最终冻结版全部门槛另已完成，见 C2 总结。C3 干净部署与第二人复现仍未做。

## macOS ARM64原生模块修复（2026-09-23）

首次完整构建虽退出0，但Rosetta环境中的`cc`默认生成x86_64，Node却是arm64，导致`system.node`到实际调用时才报架构错误。CLI版本/help不加载此模块，不能替代原生功能验收。本次未修改上游源码，仅在ARM64 shell中重新执行官方原生模块构建：

```bash
cd /Users/zhangchengjie/CUAgent/.runtime/harness
/usr/bin/arch -arm64 /bin/zsh -f -c '/usr/bin/cc -dumpmachine && exec /opt/homebrew/Cellar/node/24.9.0/bin/node /Users/zhangchengjie/CUAgent/.runtime/toolchain/node_modules/pnpm/bin/pnpm.mjs run build:native-system'
file native/system/packages/darwin-arm64/bin/system.node
TMPDIR=/Users/zhangchengjie/CUAgent/.runtime/workspace node --test --test-name-pattern='^(acquisition resolves asynchronously|separate opens of one file contend|closing the locked fd allows|invalid fd rejects asynchronously)' native/system/test/flock.test.js
```

结果：文件为Mach-O arm64；ARM64 Node实际`require`成功并检查`tryLock`导出；异步加锁、锁竞争、释放再获取、非法fd四项测试通过。此项修复时上游工作树仍干净；后来因下述插件元数据修复而有本地修改。模型、凭证、会话和正在运行的Web进程未修改；用户需停止并重新启动dsh。完整Web/模型链路仍未由本次测试验证。

后续在同类Rosetta终端做完整构建时，使用上述`arch -arm64 /bin/zsh`命令，将最后的`build:native-system`换为`build`，然后再次检查产物架构和实际加载；直接执行旧的完整构建命令可能覆盖回错误架构。

## 插件元数据错误修复（2026-09-23）

Web插件卡片读取可选`locale/en.json`时，Node可能返回只读`stack`的`ERR_PACKAGE_PATH_NOT_EXPORTED`。固定版Harness的profile resolver直接改写`error.stack`，抛出新的`TypeError`，使元数据回退失效。已在本地上游源码修复两处改写：保留原异常和`code`，只在允许时更新诊断栈；补丁及回归测试保存在[readonly-error-stack.patch](../../patches/harness/readonly-error-stack.patch)。重新克隆固定commit后，在源码根目录执行`git apply /Users/zhangchengjie/CUAgent/patches/harness/readonly-error-stack.patch`，不要重复应用。

验证命令：`../toolchain/node_modules/.bin/pnpm exec vitest run packages/boot/app-boot/tests/profile-resolution.spec.ts packages/boot/app-boot/tests/package-meta.spec.ts --reporter=dot`，结果304通过、1跳过；`git apply --reverse --check`通过。`pnpm run build:lib:host`成功，编译产物包含修复，`system.node`仍为arm64；未执行会重编原生模块的完整`build`。尚未在重启后的Web界面复验插件卡片；此修复不代表A0完成。用户重启dsh后再刷新插件页检查红色元数据错误是否消失。

## 工具接口适配

固定参考版本使用Cordis插件 `apply(ctx)`，通过工具注册服务接入定义；`execute(args, exec)`返回与 `output.schema` 一致的JSON值，`output.render`投影为模型可见内容。适配器需显式传递 `exec.signal`，复核并发与超时语义。

工具定义的 `timeoutMs` 是声明，实际超时需要 `dsh-tool-call-timeout-policy` 执行包装器；取消必须由工具协作响应，不会回滚已经发生的副作用。

最终 `ctx.tools.guard` 可拒绝执行，返回拒绝原因或不改变已有决策；guard没有“强制允许”返回值。作用域工具过滤不能替代最终guard；还要检查插件本身可能直接执行的能力。

Pi工具层的导入、注册、写入队列和 `details/content`结构需要重写。现有纯核心函数和测试无需因换框架重写。图片探针必须返回实际可读内容；Web专用卡片使用Client插件机制，Host-local的 `presentCall/presentResult` 不是Web卡片接口，A0优先使用通用显示。

## 有效配置必须覆盖的差异

- Web根tool-bash/tool-fs被禁用不代表Agent preset里没有同类工具，必须检查preset内部注册。
- 固定版本的sdk-minimal默认提供持久Bash/PowerShell并使用danger-full-access；名称中的minimal不是权限最小化。
- fs-sandbox不限制reads/listings/metadata，写入范围也未必等于本项目任务目录。
- `session-log-deepseek` 的 `enabled: false` 与 `session-telemetry-otel` 的 `mode: DISABLED` 是两条独立配置；只设OTel环境变量不等于关闭DeepSeek日志贡献。记录网络实测，不能只看配置文本。
- 原生Computer Use provider操作它所在的机器；执行进程放测试VM，另加项目桌面控制权协调。上游服务的单provider注册不是跨进程锁。

以上为当时的开发检查点；当前可执行 profile 与实测限制见本文件开头。最小底座与 Computer Use 验收见 [阶段计划](../../Harness_Development_Plan.md)。

## 固定源码参考

- [package.json](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/package.json)
- [CLI参考](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/apps/cli/reference/README.md)
- [添加工具](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/docs/cookbook/adding-a-tool.md)
- [Web配置](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/bundle/web-app/cordis.patch.yml)
- [Agent preset](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/preset/agent-preset/README.md)
- [文件沙箱](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/fs/fs-sandbox/README.md)
- [DeepSeek会话日志](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/session/session-log-deepseek/README.md)
- [OTel会话上报](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/session/session-telemetry-otel/README.md)
- [Computer Use服务](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/computer-use/computer-use/README.md)
- [Cua native provider](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/experimental/computer-use-cua-driver-native/README.md)
