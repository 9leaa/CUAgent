# macOS VM 桥接与历史诊断

P6证据核验已区分“结果写入依据”和之后的只读观察：final_state须为write_result前紧邻且30秒内的Save后观察，后续观察仍核对原图片/状态哈希及正文/窗口身份，只允许观察与读回。188项执行层测试、原失败字节离线复核通过；旧任务不改成功，尚未部署新guest或完成真实新版回归。

P6 `desktop_expiry_live.py --run p2-<uuid> --owner <uuid> --approve-task`仅供已批准的可信VM诊断窗口；须先核对源码、P5空闲和共享锁，不是模型工具。真实观察后等待短许可自然过期，同任务再次观察必须拒绝，原/重新构造controller不能续期，finally关闭原runtime。原trace/PNG/state/许可及expiry-diagnostic.json留私有目录，业务保持UNVERIFIED。2026-10-03真实VM3raw诊断与独立原文件核对通过；不证明官方App/HTTP/DB完整失权链路，不可替代P6业务验收。对应4项本地反例、执行层181项测试通过。

2026-10-03 P6已有真实SSH/VM/App最小闭环11raw通过；固定正式第一例因拒绝输入后复用旧观察而UNVERIFIED，独立验证未放行。DesktopTask现已在拒绝路径作废snapshot，不改旧C0实现或预算；176项本地测试和36子测试通过，修复版真实回归仍待运行。下方“尚未真实部署”等描述是历史快照，不代表完整P6已验收。

P6 `desktop_bootstrap.py`仅由可信后端通过固定SSH/Python调用：验证部署清单及源码SHA后，单次启动guest控制服务，日志写私有P6Launch目录。其stdout包含本次新建的模型/控制token，只能由后端有界接收并保存私有回执，禁止打印或上传。未知就绪不重启/不自动杀进程，且不授权GUI；当前仅模拟环境测试，真实启动仍待验收。

P6 `desktop_install.py`为可信部署端传送的独立安装器：仅普通mvpagent/VirtualMac，完整校验固定源码包后新建CUAgent-p6-commit目录，保留来源许可证和部署清单；已有目录拒绝，不覆盖旧文件、不启动服务。host使用backend.desktop_deploy从明确Git commit取包，不打包.runtime或凭证。当前仅本地安装/模拟传输验证，真实VM部署仍待门槛核对。

P6 `desktop_export.py --run p2-<task-uuid> --owner <worker-uuid> --epoch <positive-int>`仅供可信SSH采集端使用，stdin为`{"lines":["本次批准正文"]}`，stdout为核验后的原始证据tar，不是JSON日志。必须先撤销许可、确认零在途；固定run内只导出白名单证据，token/lease不导出，错误仅stderr固定代码并非零退出。后端不得把manifest当官方会话验收，仍须核对原任务及Flash/off。174项本地执行层测试通过，尚无真实SSH导出验收。

P6 `desktop_guest.py --run p2-<task-uuid> --owner <worker-uuid> --epoch <positive-int> --approve-task`是测试VM专用启动入口（当前尚未真实部署验收）。固定普通mvpagent的C0Evidence与旧bridge.lock，新run独占，先仅开loopback控制端口；私有guest-ready.json指明端口，凭证单独存为bridge-token/control-token，不能交给模型或输出日志。终止信号撤销许可；在途未清空时保留bridge.lock.quarantine，必须人工核对，不能自动删除或混跑不识别它的旧桥接。169项本地执行层测试通过不等于真实VM连通。

P6 `DesktopGuestRuntime`负责显式共享bridge锁、许可后单次activate、工具服务及撤销/在途状态；配合control_server(runtime=...)开放可信/activate和/status，模型凭证不能访问。准备时不启动工具服务，失败保留意图并撤销；close遇在途拒绝释放锁。164项本地执行层测试通过。仍无生产启动CLI，后续部署必须核对VM身份与旧服务所用同一实际锁，不能拿另一个文件当全局互斥。

P6的`desktop_evidence.inspect_guest_evidence`只读核验固定run原始轨迹、界面/PNG哈希、TextEdit文档和result；不构造Task或补发观察。可信调用者必须先撤销许可、确认无在途，再收集核验；返回vmStatus与sessionVerified=false，不能替代官方会话/Flash-off验证。DesktopTask仅在P6增加观察哈希记录，旧RealAppTask未改；158项本地测试通过，合成PNG不是视觉验收证据。

P6新增`desktop_tools_http.tools_server`仅为独立工厂，须由可信端先授权并构造DesktopTask，模型token必须与控制token不同。默认固定192.168.64.3:8766/来源192.168.64.1；显式loopback_test仅供测试。只接受原TextEdit五工具与stop，不开放在线verify或许可修改；逐次最终准入和原30次预算不变。当前无生产launcher，不要用它替换P5服务；153项本地执行层测试通过不代表真实VM验收。

当前收口状态（2026-10-01）：C0-01、C0-02、C1、C2 本地验收完成；最终冻结版七故障、正式 18/18、九计算器和 A0/安全回归见 [C2 总结](../../docs/stages/c2-summary.md)。以下初次诊断及“待完成”描述保留开发过程，不作为当前完成状态；C3 未做。

## 当前 C0 接口

`c0_bridge.py` 只在 VirtualMac 普通 mvpagent 账户运行；`c0_cases.py` 是开发侧固定任务注册表，`c0_identity.py` 校验应用可执行文件。模型只能调用当前任务允许的观察、点击、输入/滚动、result.txt 写入及读回；不开放 shell、任意文件路径或独立验证器。每个任务最多 30 次实际请求（包含失败、拒绝及内部请求），停止后不再派发，审计失败即关闭执行。

`fixtures/CUAgentFixtures.m` 提供原生表单、长滚动页面和文档编辑；保存使用系统 NSSavePanel。`build-fixture.sh` 生成签名测试 app，只能在测试 VM 运行。fixture 不代替模型操作，Driver 返回也不等于效果成功，最终核对实际界面、轨迹、真实文件与固定独立期望。

无模型测试仍使用下方 unittest 命令；它们不是 GUI 验收。真实证据留在 VM `C0Evidence/<run-id>` 与私有 `.runtime/runs/`，不得公开凭证、原始截图或完整会话。阶段结果见 [PROGRESS](../../PROGRESS.md)，方案见 [C0-02](../../docs/stages/c0-02-design.md)。

## 历史固定回归

C2 方案见 [可靠性方案](../../docs/stages/c2-design.md)。`c2_bridge.py` 的 `C2ControlMixin` 提供持久 owner/epoch、停止/在途检查、保持预算的开发侧只读恢复观察、明确交还及新观察要求；`C2Task` 复用 C1 六例，`C2DocumentTask` 复用 C0 原生正文/系统保存面板，后者仅用于故障诊断，不替换正式六例。显式 C2 HTTP 通道分离 model/verifier/control；模型不能控制恢复或验证。UNKNOWN 的已生效 Submit 仅在实际新观察、完整轨迹、提交文件及效果独立一致时对账，原 UNKNOWN 不删除；不能用调用者提供的 verdict 清除不确定性。

开发故障开关 `CUAGENT_C2_FAULT` 允许 `none`、`submit_response_timeout`、`process_exit_after_observe`、`window_close_after_observe`、`manual_document_edit`、`permission_revoke_after_observe`。依次为正常、真实 Submit 返回后丢响应、首次观察/窗口绑定后退出 executor、首次观察后暂停供开发侧实际关窗、真实文档初次输入后暂停供 GUI 接管修改、首次观察后暂停供开发侧真实撤销 guest 权限。最后一项钩子不模拟权限错误或自动改设置；真实 VNC Off/On 与 Driver 自身权限状态、不可用 AX、原预算恢复已有 15/30 raw 诊断通过证据。故障只注入一次，重启读取原账本并暂停，不自动重放。窗口故障仅在输入纠错测试启用固定 keep-alive 参数；恢复通过开发 control 关窗/原生打开固定应用，同 PID 新窗口观察后才能交还。原生打开请求也计预算与 UNKNOWN，不授权模型 shell。

文档编辑控制只允许当前文档正文的固定干扰文本，必须新观察确认变化才能交还。恢复模型 `vm_type` 只替换固定原文；内部 `set_value` 绑定唯一新鲜原生正文、按真实工具名计预算，C0/C1 不开放此 raw 能力。模型没有通用 set_value 或人工改文档入口，最终仍必须经 GUI Save 并独立核对完整前后轨迹和文件。真实诊断通过 25/30 raw；首次追加失败保留。控制层重构后的旧故障同版回归仍待完成，不能合并不同版本成绩当作整体验收。

官方模型流故障另由开发侧 C2 私有连接的 `modelFault: after_first_observation` 启用：真实 VM 图片进入上下文后，官方 `llm/stream` 项目钩子持久化一次标记、暂停并抛错，provider 调用前发生，不声称服务商宕机。原真实 error 与新会话恢复独立通过 14/30 raw；同 run 重启不再注入，C0/C1 与默认 C2 不启用。

`c2_fault_audit.py --directory <private-guest-evidence>` 只离线核对响应丢失；`c2_window_audit.py` 只核对窗口关闭恢复。两者及合成反例测试都不是完整 C2 发布报告。`c2_control_live.py` 是无模型/无业务提交的 Driver 诊断，taskStatus 为 UNVERIFIED，不计固定 18 次。目前七类故障有历史版本真实诊断证据；正式评测、A0/九计算器及最终同版完整回归仍待完成，见 PROGRESS。

`c2_budget_live.py --run c2_budget_<unique-id> --stage fill|restart|audit --approve-task` 同样仅供测试 VM 开发诊断：fill 实际观察到 30 次，restart 须在第二个独立 Python 进程运行，audit 离线核对实际请求/结果/图片和拒绝。真实诊断已通过：30 次实际请求、七项继续/恢复拒绝、跨进程预算不清零、停止后零派发，业务 UNVERIFIED。禁止改计数、补造请求或把 UNVERIFIED 业务写成成功；不替代官方模型的预算回归。

`c2_inflight_live.py --run c2_inflight_<unique-id> --approve-task` 在真实 Driver 正文输入返回后暂存响应，独立线程 stop 必须立即返回并记在途 ID，新请求和提前接管被拒；放行原返回后再接管、新观察证明正文实际变化。真实诊断 6 raw 通过，未业务提交、状态 UNVERIFIED；不是官方模型 UI 取消或网络超时证明。临时返回 hold 层、完整顺序与所有真实结果保留。

C1 扩展为 `c1_cases.py` 和 `c1_bridge.py`，复用同一准入/预算/审计/停止层。注册表固定六类、前后各三次；只有开发者显式启动 C1 才注册目标切换能力，C0 默认注册表不包含 C1。窗口选择仅按当前任务固定标题，重新核对应用/PID/可见窗口，旧观察失效。`--approve-task` 仍必需；模型不能直接传 bundle、可执行路径或期望值。实际启动前诊断与正式评测必须分别报告，见 [C1 方案](../../docs/stages/c1-design.md)。

三个Python文件从旧项目原字节迁入，源头是 `cua/samples/mac_agent_mvp/`。它们是环境诊断和固定运算对照，不是Harness Agent。来源哈希见根 [迁移清单](../../migration-assets.json)。

- `preflight.py`：开发侧只读环境清单，不启动VM，不调用桌面工具，不输出VNC密码。
- `driver_smoke.py`：在指定测试VM内固定执行12×34，检查计算器PID/窗口、新AX显示和执行证据。
- `tests/test_driver_smoke.py`：7项mock边界测试；`--live`另在测试VM执行固定流程与独立smoke断言。

P6缺结果文件恢复：desktop_evidence显式启用real_app_verifier的allow_missing_result_read，默认旧TextEdit调用不启用。仅原完整配对的read_result/FileNotFoundError早于唯一写入，且错误后有新鲜原观察、成功写入和正确读回，才允许该失败留在成功证据中；原账本/预算完整不变。其他错误、写后失败、缺读回/新观察等仍拒绝，host另对照官方读写顺序和错误。此项离线核验不登记旧任务成功。

P6输入拒绝恢复：desktop_evidence显式启用allow_rejected_input，旧TextEdit默认仍拒绝。只允许实际输入前、完整配对且明确refused的rejected_type_text；之后必须有原文件/PNG绑定的新观察以及唯一实际输入，不能接纳输入error/UNKNOWN、重复编辑、晚于输入的拒绝或旧观察。全部原调用仍计数，报告recovered_input_refusals；host另逐项对应官方vm_type与guest序列。旧失败仅可离线复核，不改任务状态或补交付。

P6初始窗口就绪：仅DesktopTask在首次observe单次launch后，对原PID最多做3次list_windows，所有查询计原30raw；只接受同PID/应用/完整任务标题且可见的唯一窗口，再取得原截图/AX证据。缺失只等最多两次、每次≤1秒；多匹配、结构错误、失权/停止、超预算或超5秒观察截止均停止，不重启、不选历史窗口。5秒在每次查询前后核对；单次Driver调用仍使用原传输超时，不承诺整个方法墙钟硬限5秒。旧C0/TextEdit实现不改。

根目录无模型测试：

```bash
python3 -m unittest discover -s tools/mac_vm/tests -v
```

历史live入口需要VM内Python 3.12.14或验证过的兼容版本、Driver 0.28.2、普通mvpagent账户与已授权图形会话。将本目录部署至VM后在该目录执行：

```bash
open -n -g -a CuaDriver --args serve
python3 tests/test_driver_smoke.py --live
```

以上命令只供测试VM的C0复核，不能在宿主删除VirtualMac/账户检查来运行。实际请求最多30次；动作超时不盲重放；每次在VM任务目录新建证据。当前固定smoke不生成完整MVP的result.txt。

开发側只读inventory：

```bash
python3 tools/mac_vm/preflight.py --storage /absolute/path/to/vm-storage --vm mac-agent-mvp-15-6-1-restored
```

退出0仅代表读取完成，NOT_ASSESSED不等于隔离或任务通过。

## 恢复与来源

[vm-manifest.json](../../vm-manifest.json)记录历史环境；[Lume补丁](../../patches/cua/README.md)记录固定源码与隔离改动。configured是历史停机基线，restored是曾配置开发凭证的副本，不能直接分享。

使用经过核验的隔离Lume二进制，从停机无凭证基线clone到新名字，明确source/dest storage；先核对固定版本help与当前资源。启动历史参数为 `LUME_MVP_HOST_ISOLATION=1`、`LUME_TELEMETRY_ENABLED=false`、`--display none --network nat`。不得覆盖现有VM或启用宿主目录/剪贴板共享。

普通账户图形登录后启动Driver daemon，再验证权限、新截图、应用信息与隔离。恢复基线不会自动安装Harness或配置模型。

历史M1为17次调用、AX408、独立smoke通过；本轮只重跑7项mock，没有新的VM验收。九组计算器、结果文件及异常要求见 [新计划C0](../../Harness_Development_Plan.md)。UFO固定参考与旧阶段迁移见 [MIGRATION](../../MIGRATION.md)，不依赖可能已不可达的旧Git历史才能理解规范。
