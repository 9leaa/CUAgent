# CUAgent 实际进度

更新：2026-10-03。主路线：[Harness最小可用底座 → Computer Use主线 → 通用增强/O0](Harness_Development_Plan.md)，当前按[个人任务服务P1–P5路线](docs/product-roadmap.md)推进。下方“当前交付”及最新收尾记录代表当前状态；各日期过程中的未提交/未完成描述保留当时事实，不代表目前状态。

## 当前交付

P4逐对控制器：新增`agent/efficiency_runner.py`，全局锁、空队列、每对新额度核对、冻结源码/输入检查；新正式审批预绑定30秒执行租约，每次观察前续租，结束/错误先撤销后观察原会话及恢复。启动ACK不明不重发，生命周期记录包含激活前至恢复后的单调墙钟、介入和原证据SHA；前序结果重新读取原提示/会话/验收器核对，拒绝跳过或补跑。业务未通过的任务仍统计消耗，独立安全判定未知保持INCOMPLETE。Python39/39、核心71/71、后端80/80；最初直接pytest因未载入私有测试环境得到66通过/14设置错误，改用既有`backend.manage test`后80通过，未改测试或数据库配置。正式批次尚未启动，未宣称P4验收完成。

P4原始用量提取：先补技术契约，再新增`agent/efficiency_evidence.py`，从原会话/账本提取所有已记录usage、模型工具调用、raw与模型轮次时间；要求与原文件SHA绑定的完整生命周期、单调时钟和显式介入列表，失败/error/aborted同样保留用量，缺记录不填零。型号、能力及预算异常另行输出，不把提取指标当安全通过或业务成功；仍需接完整业务复核和逐对控制器。5项新合成测试，Python34/34；本轮无新增模型调用。README删除“P4尚未开始”等与最新真实单例矛盾的当前描述；历史过程记录保留。

P4正式配对准备器：新增`agent/efficiency_suite.py`，复用P1固定20类模板新建两臂共40个唯一会话；相同输入及oracle逐字节核对，奇偶交替顺序固定，冻结源码/提示/工具/审批SHA，运行前check拒绝任何漂移。默认不派发模型、不生成产物、不覆盖已有suite。2项新测试验证完整40任务、零模型输出、输入/审批/期望篡改拒绝，Python合计29/29。正式私有批次尚未冻结：需先完成原始证据采集和逐对运行控制，避免冻结后再改受测源码；无新增模型调用。

P4最小真实闭环通过：`p4_probe_20261003_001` / `session-5e414922-7568-4cb9-beef-1019a741892d`。先确认队列/190会话空闲，停止精确空闲Worker49960并持有原全局桌面锁，再构建6插件、激活专用preset，唯一新请求显式Flash/off；真实聚合→模型写JSON→确定性Markdown→完整读回，独立verify SUCCEEDED。5模型调用、9/30实际请求，input2884/output484/cacheRead7168/total10536 token，激活至核验9.072秒（不是完整恢复墙钟）。原始证据`.runtime/runs/p4_probe_20261003_001/probe-verification.json`；JSON SHA `4dcfb7c338e04888c63637d6377a9d993e6b83dadd80c4a9c0ef513deb4dd2b2`。finally正常恢复基础配置，旧3账本SHA不变；观察程序退出0，普通Worker重新启动。此为诊断单例，不计正式20对成功率，不宣称P4收益已证明；正式冻结/采集/对照仍待完成。

用户确认夜间套餐自然重置并授权继续（2026-10-03）：实时Codex接口已用6%、剩余94%，积分62494.026057未变、重置卡1张未用。原额度口径阻塞解除，按重置后的套餐继续，仍禁用积分/重置卡，DSH固定Flash/off。只读检查后端无QUEUED/RUNNING/WAITING_RELEASE任务，官方190个会话均无running；准备P4最小新任务，未把用户本次确认倒写成此前授权。

额度口径纠正（2026-10-03）：本轮官方Codex账户工具实时返回ordinaryUsageAllowed=true、codex窗口10080分钟/usedPercent=6、积分62494.0260570000、重置卡availableCount=1。用户约62495积分及70%约束属于Codex，不能误称DSH额度。DSH只读account/getBalance返回CNY钱包，不是该积分/套餐。当前窗口与历史30–40%读数未完成同口径对应，不能据当前剩余94%自动扩张本次原70%授权；未使用重置卡、未派发P4真实模型。账户标识、凭证、卡ID不进入公开文件，DSH账户UI坐标操作noWindowsAvailable，未重启应用。下一步先确认原预算与当前窗口的执行口径，再运行真实对照；P4仍未验收。

P4专用入口已编码：A1模板新增非默认`p4-report-inputs`，旧default及P1插件组合不变；构建/启动预检同步第六个候选插件，配置清理显式处理P4 preset。runner由精确审批工具清单选择P4及聚合提示，拒绝聚合定时/continue，baseline/草稿提示保持原样；仍每次显式Flash/off。YAML静态核对唯一ID/旧default/opt-in通过，核心71/71；运行App未重配、未构建覆盖现用插件，真实新preset加载仍待实测。查同版账户controller只有安全账户/钱包读取，尚未确认套餐余量接口；未因钱包可读就推断套餐足够，未派发推理。

P4完整离线验收接入：`daily_report.prepare/verify`及CLI新增显式aggregate选项，默认P1/P3能力清单不变；聚合任务拒绝定时/续接组合，必须恰好一次聚合，内层派发总数/身份/预算/顺序全部匹配后才进入原字段、来源和两产物读回核验。新增合成完整轨迹5模型调用/9实际请求通过；缺内层、错误统计、截断读回、未显式opt-in均拒绝，Python27/27。修正辅助模块同时兼容包导入及直接CLI。真实App配置/preset尚未切换，真实P4仍未执行，无模型费用。

P4独立证据预检：先提交验收契约`5f3ac2d`，新增`agent/aggregate_evidence.py`只读核对聚合task/notes/CSV与原文件/独立oracle、全部固定内层callId、参数摘要、返回SHA和父子顺序。缺失/额外/重复/乱序/失败/伪造读取均拒绝，只有核对成功才输出可供原业务验收使用的来源观察。5项新增合成证据测试通过，Python日报/P4合计26/26。尚未接入完整verify、准备入口和专用preset，不能把预检通过算P4端到端通过；无模型调用，未改App/旧账本。

P4官方注册接入：新增独立opt-in `report-inputs-tools.ts`，A1审核候选表增加名称但旧审批/默认preset不自动授权。policy服务每个内层读取/统计单独dispatch/result，固定父调用序号、错误与SHA留证；每步重新核对许可，外层另扣1次。6项新增同版真实注册表测试通过：外层+三内层共4次、预算只余2次时止于30、旧审批拒绝、读取之间control停止禁止下一派发、取消/外会话/卸载拒绝、真实越界符号链接失败后不读CSV。首次测试发现Cordis服务代理不支持直接对象同一性比较，改用每实例UUID核对；零派发无账本的测试读取也修正，未放宽预算判据。完整官方集成37/37、核心70/70；不调用模型、不改变运行App。P4专用preset、真实证据验收及配对采集仍未接通，阶段未完成。

P4输入聚合核心：先提交内部计数方案`b1be799`，新增`agent/report-inputs.mjs`，只通过必需invoke回调逐步读取task/notes和统计CSV，不自行读盘、不生成业务报告。限制固定task结构、输入路径、数量、完整读取与64KiB总输出；取消、回调拒绝或输出过大立即停止，不重试/截断。6项无模型测试通过（含多种反例）。尚未接入官方policy/工具注册，不宣称已验证真实预算或文件隔离；下一步接入每内层调用dispatch/result及官方注册反例。原App、审批和账本未改，零模型调用。

P4首个实现：新增`agent/efficiency.py`离线指标比较器，强制完整20对交替清单、两臂同输入/期望、原任务/会话唯一、固定Flash/off和臂内源码/提示/工具哈希；所有attempt累计费用/时间/调用，任务恢复仍≤30。缺usage/介入/时间或未完成批次返回INCOMPLETE，假成功/安全失败不得推荐候选，固定10% token收益及10%墙钟回退上限。8项合成反例通过，连同日报共21/21；不是原始证据采集器或业务验收器，尚未接入真实试验。无模型调用，聚合工具及40次配对尚未执行，P4未完成。

2026-10-03开始P4：从已推送P3 `12c0e7f`新建`p4-efficiency`，先写 [方案](docs/stages/p4-design.md)。重新读取P1原报告，区分实际请求196→209与模型调用196→189，不把旧收益算作P4通过。计划先离线配对比较器，再opt-in只读输入聚合和安全反例，最后额度许可下冻结20对真实Flash/off；不换模型、不用积分/重置卡。本轮尚未实现或调用模型，P4未完成。

P3阶段提交`b6e7f7d`已推送并通过git ls-remote核对：`p3-durable-execution`及默认`harness-migration`相同。包含技术方案、实现、最终80/64/31/13项无模型回归、真实故障与1/8小时结果、README及阶段总结；没有创建PR/标签，未改写旧失败。以下“推送待核对”属于该交付前过程。

P2 `6bd8c4a` 已核实推送阶段及默认分支，技术方案 f7911f4 先于实现；后端闭环与工具审计见 [P2 总结](docs/stages/p2-summary.md)。当前分支 `p3-durable-execution`，依据 P2 的实际断点重写 [P3 方案](docs/stages/p3-design.md)，先提交方案再实现。P3本地验收完成，含1/8小时及最终断点矩阵；阶段推送单独核对；P4/P5未开始。历史套餐/积分读数见过程记录，不作为当前余额；下一次模型推理前须重新核对，禁止使用重置卡或积分。

P1–P5路线已落盘；P1阶段分支为 `p1-daily-report`，技术方案先于代码提交，首轮17/20、修正后新完整轮次20/20。A1 `9e18f70`、TextEdit `a49c236` 已分别推送其阶段分支。

2026-10-02 新授权：后续逐阶段新分支、先技术方案再代码、验证并更新 README 后推送。已补齐 A1 独立分支提交 `9e18f70`，本次 TextEdit 单独分支 `real-app-textedit`；下文未提交/未推送描述属于原执行时点。

| 项目 | 状态与证据范围 |
|---|---|
| 新仓库 | 公开 `9leaa/CUAgent`；四阶段分支已分别提交推送，默认 `harness-migration` 按本次授权快进同步最新阶段与文档；不创建PR/标签，远端以Git为准 |
| 旧仓库 | `9leaa/os_agent` 已归档，描述/主页指向新仓库；后续按用户要求将旧本地源码和Pi移至废纸篓，VM/镜像保留 |
| 设计与计划 | README、DESIGN、Harness_Development_Plan、AGENTS、COLLABORATION、MIGRATION已按Harness与Computer Use优先顺序改写 |
| 核心工具迁移 | 20个文件逐字节迁入；manifest记录来源类别和SHA-256，其中15个来自旧未跟踪文件 |
| 工具与后端测试 | 核心64/64、官方Desktop同版注册31/31、Python日报13/13、后端80/80；属于无模型测试 |
| 本轮VM工具测试 | 最新 Python 123/123 执行层/mock/反例通过；不替代真实 VM 证据 |
| Harness版本 | 当前官方 Desktop App 0.2.0-rc.2 / 内置 Node 24.18.1，同版源码参考639ed015；初始 Web 固定源码00102833d / 0.1.7-alpha.2仅历史 |
| Harness A0最小底座 | 最新 Desktop 真会话/文件/直接与工具图片/标准取消/30 次持久预算回归通过；重启首回复错误和后续澄清保留，Web记录仅历史 |
| C0-01及C0–C3 | C0-01、C0-02、C1 与 C2 本地验收完成；C2 正式 18/18、七故障、九计算器及 A0/声明安全范围回归通过；C3 未做 |
| A1通用增强 | 分支 a1-agent-expansion；业务/会话/图片/取消/持久预算通过，插件与流程示例已提供；新真实 C0/VM 声明安全及兼容回归通过，A1 本地部分完成；第二人按用户确认暂缓、未验 |
| O0 | 后置，未开始 |

## 2026-10-02：P3 检查点实现中

2026-10-03最终收口：先提交断点矩阵方案`0fb18c4`，再补9项无模型Worker测试，覆盖创建/选择响应窗口、提示响应有无、activate/start单次失败、未知续接只观察及准备失败零RPC。后端80/80、核心64/64、官方注册31/31、Python日报13/13，保留TestClient弃用警告。1/8小时和真实故障证据及已知失败汇总于 [P3总结](docs/stages/p3-summary.md)；P3声明范围内本地验收完成。没有新增模型调用或VM操作，GitHub推送结果另记。

2026-10-03 8小时门槛通过并再次独立复核：任务 `9295c25e-a411-4d6e-9d39-2992fe6a089b`，原session `session-0459ea6c-ed62-45ef-9180-2d7489203a1b`。原观察器正常退出0，`.runtime/backend/soak-8h-001/verification.json` SUCCEEDED，实测28863.758144秒、1912采样；1910份等待证据完全一致，无pending且只有草稿JSON，最大采样间隔15.304476秒。API PID46195→49955，Worker48418→49960。期限UTC00:28:20.572520，第二attempt于00:28:20.783307领取，未提前发布；同session预算6→10/30，9个模型工具调用、19591 token、Flash/off。收尾重新运行独立verify、读取当前API并下载两文件，JSON SHA `0e606c801039dad846774d81697cb687fd73aff3fd48909bb11a8b7e83ae9c97`、Markdown SHA `eb8c062e09cbb93b366be176fdc3c4862f2794f0244a8b971c9aae1fd5c7c5c9`一致；两attempt均有backend-restored且无restore-pending。只读复核未调用模型。此结果不证明连续模型推理、任意GUI长任务或关闭Desktop执行；最终阶段审计和推送仍待完成，以下运行中记录保留当时事实。

2026-10-03 00:27（北京时间）1小时门槛真实通过：原观察器89219正常退出0，`.runtime/backend/soak-1h-002/verification.json`独立SUCCEEDED，实际3659.079962秒、243采样、最大间隔15.169904秒；等待JSON/账本不变，原session `session-448f5520-d1f2-431b-95a4-e3098da29ff2`，6→10/30，18011 token，Flash/off。API同任务SUCCEEDED；两attempt且到期后领取，renderer真实派发符合不可变期限，文件/读回/来源均核对。API两PID、Worker多PID重启均有采样。首个草稿失败继续保留，不能称所有长测尝试均成功。

随后启动8小时：新任务 `9295c25e-a411-4d6e-9d39-2992fe6a089b` / session `session-0459ea6c-ed62-45ef-9180-2d7489203a1b`，草稿正确，6/30、9853 token，WAITING_RELEASE；期限UTC2026-10-03 00:28:20.572520（北京时间08:28:20）。观察器18636输出`.runtime/backend/soak-8h-001`，要求28800秒，不重启计时。初始采样捕获旧Worker48418/API46195后，核对无在途任务、资源已释放及基础配置恢复，再实际停止并重启为新API49955/新Worker；API新句柄84479、Worker33427。8小时未完成，P3不收口不推送。

2026-10-03生命周期补测：新增 `backend/tests/test_worker_lifecycle.py` 10项execute整流程测试（RPC/DB为mock，非真实模型），覆盖原会话缺失/请求接受未知拒绝重发、已有continuation意图只poll、已创建未发送仅start-existing一次、五类已有工作现场拒绝、restore失败记录pending/日志且不伪记恢复成功。后端71/71，已知TestClient弃用警告不变；补充backend/README操作指引及验收清单。生产代码未改，API清理告警尚不单独展示，不能把业务成功等同环境恢复。原1h观察器仍存活。

2026-10-03 00:04（北京时间）只读RPC故障集成通过：独立inspect进程用私有fetch包装，前两次真正收到官方session/modelCatalog响应后在本地抛传输错误，第三次正常读取原session `session-4753d133-4482-4372-9bb4-95c1bbc95ec1`。生产Worker.rpc_process完成1/2秒退避、共3次尝试/3.632548秒，terminal及原request匹配；原session/prompt/audit/两产物SHA逐一不变，零新增推理。证据`.runtime/backend/p3-readonly-response-fault.jsonl`及`p3-readonly-response-verification.json` PASS；不是共享网络断网、不证明副作用请求可重放。写操作超时不重试仍由现有反例覆盖。普通Worker48418和1h观察器46135实际存活，长测仍未到期限。

2026-10-03 00:01（北京时间）激活断点新完整闭环通过：先提交CSV字段提示方案 `9948c73`，确认统计工具实际含path，再为新任务显式列出七个必需字段；不补写模型JSON、不改验收器、不覆盖首试或已派发长测。任务 `2c74c877-8f43-436d-a3a8-6b59df89669d` / session `session-4753d133-4482-4372-9bb4-95c1bbc95ec1`，真实activate后退出90，原租约自然到期后恢复，epoch24→25、两attempt、只一条用户提示，原激活配置SHA不变；新核对前后session不存在后创建发送一次，最终SUCCEEDED/10次/15775 token/Flash-off。独立verify及API下载588字节SHA `eb8c062e09cbb93b366be176fdc3c4862f2794f0244a8b971c9aae1fd5c7c5c9` 一致，私有run内activation-recovery-verification.json PASS。首轮UNVERIFIED及36836 token保留，不宣称提示修正已证明普遍可靠性。核心64/64、Python日报13/13，后端上轮61/61；原1h观察器仍运行，普通Worker已恢复。套餐34%，积分62494.026057未变、重置卡未用。

激活断点首个真实故障：`80b1b8d8-c768-419c-897a-d9e753405ed0`，实际activate成功、inspect确认session不存在后Worker退出90；保留原配置SHA、空账本及无产物快照。原租约自然到期后resume，同task/session `session-662283d0-373b-4904-8fbf-e0492d9f1fe2`，epoch22→23、两attempt，rebind前后均确认不存在，原active-tasks SHA未改，只发送一次prompt。恢复流程有效，但模型JSON漏CSV path，renderer三次失败、覆盖已有JSON被拒；最终UNVERIFIED/INDEPENDENT_VERIFICATION_FAILED，17/30、36836 token、Flash/off、下载404，基础配置恢复。原失败不修改、不以恢复成功冒充业务成功；私有run内activation-fault-before/backend-activation-reconciled/backend-verification均保留，完整成功闭环仍待测。普通Worker已恢复持续运行，1h观察器未停止。

激活断点补充：先提交方案 `bb862ba`，再实现 `recover_activation`，替代active-tasks存在时无条件BLOCKED。执行意图/响应、已有审计或产物均拒绝；inspect须明确同一session不存在，rebind只执行一次，之后再核对现场及证据完全不变，才交给已有start唯一创建流程。新增17项无模型反例/正常路径，后端61/61（保留一项已知TestClient弃用警告）、diff检查通过。当前运行Worker未热更新；新增路径尚无真实断点验收，1h原观察器及Worker均继续存活，不重启计时。

新完整停滞轮次独立核对通过：任务 `118200a0-928a-42a6-a06d-8ca215f89f77` / session `session-444a1919-09db-4f82-9c4c-4efbcd8ac048`。真实模型完成后冻结poll观测，业务进度时间15:41:28.749783，fresh inspect前实测停滞302.374186秒；控制文件已stopped，现场terminal，因此没有cancel或新prompt。API为STOPPED/NO_BUSINESS_PROGRESS、10/30、仅一条用户消息、11986 token、Flash/off；产物清单为空、下载404。私有原run内 `stale-observation-final-proof.json`、backend-stop-inspected及backend-restored记录保留。普通Worker PID47081已恢复，1h观察器PID46135仍实际运行，原长任务WAITING_RELEASE、6/30。该故障只证明旧观测下安全停止，不声称真实模型挂起；1/8小时仍未验收。最新套餐已用34%，积分62494.026057未变，重置卡未用。

真实停滞故障：`f4b458cb-0bbc-4317-af1e-e82f63897530` / session `session-53090580-18ee-4f64-93ae-c9664a83e045`，实际模型已完成，私有适配器冻结观测并隐藏terminal（不冒充模型挂起）。最后真实进展15:30:21.967，15:35:22.075检测stalled并stop；第一测试脚本错误使用晚1.2秒的冻结起点断言，故BLOCKED，历史保留。修正测试后原任务再次恢复，持久停滞时间未重置；发现基础profile恢复后盲目cancel旧idle会话失败，保留DESKTOP_CANCEL_FAILED。新增stop_remote先fresh inspect，已结束则不cancel；第三次原任务STOPPED/NO_BUSINESS_PROGRESS，实际idle531.987秒、control在新查询前已停止、同一条prompt、原10/30/12406token不变，未再推理。三次attempt/错误均保留，不能把这项说成初次无缺陷通过。正在用新任务完整重测300秒。独立1h观察器46135始终运行、原任务仍WAITING_RELEASE 6/30；期间普通Worker在该业务等待窗口让出给故障专用Worker，到点前恢复。新增revoke_local立即关闭失联owner许可，不能覆盖新epoch；API可读business_progress，后端44/44。

1小时实测启动：首个 `80a01bd0-e8eb-4045-b733-0e255a71fbd0` / session-415b0408 在草稿漏CSV path，BLOCKED/PARTIAL_JSON_INCORRECT，7/30；未进入长等待，费用9818 token保存在原run/failed-draft-usage.json。观察器一次误指该旧失败任务也立即退出，保留soak-1h-do-not-run，仅观察故障不增加模型调用。相同输入新 `6757af50-e903-467b-aea1-e4ada4be5fcf` / session `session-448f5520-d1f2-431b-95a4-e3098da29ff2` 草稿正确，6/30、9139 token，UTC15:25:55进入WAITING_RELEASE，16:26:45.888758到期。观察器 backend.soak 于15:26:03开始单调时钟采样，证据 `.runtime/backend/soak-1h-002/`。等待中已实际退出Worker45808/API45314，重新启动API46195及新Worker；观察器必须采到两组真实PID并持续至少3600秒才可能PASS。尚未有最终验收；8小时未开始。新增异常路径保存已有官方usage，后续草稿失败不再只显示空用量，不修改已保留旧失败状态。

发布时间完整短测通过：迁移0004已应用，本项目API正常重启加载releaseAt（带时区且旧请求幂等不变）；审批绑定不可变publishNotBefore及受限write路径，工具guard/body均检查，deadline进入账本identity不能恢复时改变。官方注册拒绝提前renderer/直接写Markdown，到点renderer内部读写各扣一次。新任务 `3bb7a347-931b-469d-9160-c7977450c2f6` / session `session-17dc6fbd-159a-40d6-8ae5-0138b5cf7ccb`，6次草稿→WAITING_RELEASE；另一个提前Worker--once未领取。UTC15:20:29.130698到期，15:20:29.871772再领取，同session6→10/30成功，总97.066秒/19228 token，Flash/off；原session前缀、账本、两份产物及实际渲染派发时间独立PASS。私有release-short-submission/verification.json。后端40/40、核心63/63、官方注册31/31、Python验收13/13。1/8小时尚未完成。

长运行方案细化先提交 `5b66061`：同一日报先草稿，到业务发布时间再最终发布；明确只证明定时业务等待期间的持久任务，不声称模型连续推理8小时。新增迁移0004/release_at，WAITING_RELEASE释放资源、未到时不领取、stop→resume不绕过时间、到期保持原session与预算；真实隔离PostgreSQL反例后端39/39。此时生产尚未迁移0004、API和工具门禁未开放releaseAt，等待真实计时未开始。额度核对已用33%，积分62494.026057未变、未用重置卡。

部分产物新完整轮次通过：任务 `d37923a6-68fc-4b2b-ab6e-48c228494767` / session `session-84c60e66-714e-462a-b8d7-1c7fe7587c99`。真实 JSON 写入后停止、原 Worker 退出89；原5次派发，恢复同session/原账本，attempt 1→2、epoch12→13，补renderer内部读写及两读回共4次，最终9/30、API SUCCEEDED；原JSON与首轮会话SHA不变、完整独立验收PASS、CLI下载588字节SHA一致。Flash/off，两轮总12283 token。私有 `.runtime/backend/p3-partial-002-before.json` / `p3-partial-002-after.json`；首试仍UNVERIFIED未改。无进展检测新增持久businessProgress，提示数/派发/返回未推进300秒则先持久stop关闭工具派发，再cancel；心跳/重复checkpoint不刷新进展时间，重启读取原时间。时间回退/计数回退拒绝。后端37/37，真实新续接也经过该路径；尚未通过真实300秒卡住故障及1/8小时长运行门槛。

部分产物真实首试：任务 `8259a18c-a798-471e-9738-3344c2837fc3`，session `session-d1ed3905-365a-4da8-87ab-43cf28fe0283`。JSON 成功返回后私有故障控制器停止派发、cancel并确认终止，再退出 Worker(89)；原6次、无pending、无Markdown。恢复同session/原预算，以continuation-plan绑定原sessionSHA和账本前缀，第二轮仅renderer及两读回，累计10/30；原JSON未变。首轮结束实为精确 A1 policy unavailable 错误，初版验收只认aborted/completed，故任务保留 UNVERIFIED及原失败报告。先补方案 cd418d7，再精确增加该停止边界，所有工具完整关联/两次唯一写入/来源与读回规则不变；对原始证据重新独立verify通过（13959 token，Flash/off），没有更改DB成功状态或重写历史报告。需新任务验证修正后API完整闭环，不能把离线重核对当API已成功。Python验收13/13、后端35/35、核心62/62；继续保持P3未完成。

部分产物恢复预检：新增 backend/recovery.py，仅核对并返回缺失动作计划，不生成业务文件。JSON/Markdown 必须与原 oracle 一致，输入 SHA 未变、所有派发已返回、每个已有产物有唯一成功写入及相符 SHA；已有 renderer 还需内部读取按原账本计数且顺序正确。缺 Markdown 最少保留四次请求（内部读/写与两产物读回），都存在则只读回两次；余额不足拒绝。八项单测覆盖正常计划、UNKNOWN、错误文件、伪造/缺失写入、输入变更、预算不足及只读收尾；后端 34/34。此为预检，不是完整原会话续接或真实故障四验收。

真实故障三：任务 `1275d4fd-1dff-4ea2-b657-9bb5946cdbe7`，通过私有 fetch 包装在真实 session/prompt accepted 返回后、runner 保存响应前退出 Node 和 Worker（88）；不删改旧响应伪造故障。无 prompt-response.json，原请求及 session `session-9289ff8c-f00a-4524-b759-ca263c5fe3b7` 保留。原 Desktop 在租约到期前完成，恢复时 inspect 匹配原 rpcId，attempt 1→2、epoch 8→9；SUCCEEDED，9/30、Flash/off、12188 token。前后原 session SHA、prompt SHA、账本及两产物完全一致，仅一条 user/message，无新增推理；基础配置已恢复。私有 p3-lost-response-before/after.json PASS。新增恢复核对记录；找不到原会话或闲置会话无原请求证据则 BLOCKED，不能因确认缺失重发。取消后观察加 30 秒上限，超时记 UNKNOWN，不无期限等待或重放。后端回归 26/26。部分产物续接、无进展和长时间门槛仍未完成。

真实故障二：新任务 `b50a0cf4-9245-4511-98dd-90006bfae1eb`，session `session-058d39f6-5d4a-4314-8a44-30de44947004`，在 create-only 返回后 os._exit(87)。原日志 4 events、0 userMessages/工具调用、无 prompt 意图。租约自然到期后 resume；inspect 核对原会话，rebind 用新 epoch 重新加载审批，start-existing 拒绝任何已有 prompt 意图或工作事件，再显式 Flash/off 发送一次。原创建请求 SHA/session 保持，attempt 1→2、epoch 6→7；SUCCEEDED、10/30、12593 token，仅 1 条 user/message，基础配置恢复。私有 p3-created-recovery-before/after.json PASS。后端 26/26、核心 62/62。未把“无历史消息”独自作为无待处理请求证明：还要求本地从未记录 prompt 派发意图，并在空闲配置重新加载后再次核对。

真实故障一：新任务 `f5888cb3-a73b-41f6-8108-0bd13fb45082` 在独立核验成功、数据库 finish 前由私有测试注入 os._exit(86)。进程退出已确认，数据库仍 RUNNING，未错误发放成功产物。等原租约自然到期后 API resume，新的 Worker 在原 session `session-7bf7badf-1a60-4733-99f1-a8b86a967164` 核验并登记 SUCCEEDED；attempt 1→2、epoch 4→5，但预算仍 10/30，原账本/产物摘要和整个 session.jsonl SHA 完全一致，零新增推理。原任务 Flash/off、14045 token。恢复基础 A1 配置的结果另存私有 backend-restored 记录；修正了旧 Worker 死亡后新 Worker 没恢复基础配置的遗漏。证据 `.runtime/backend/p3-finished-recovery-before.json` / `p3-finished-recovery-after.json`，PASS；后端回归 23/23。其余三个故障窗口及 1/8 小时未完成。

恢复观察追加：核对同版官方 commands.ts 的 hasPromptRequest，新增只读 inspect，使用原 user/message.source.rpcId 证明原请求已入库；日志缺失不能证明请求没进入实时队列。真实原 session-f833ddc7 再查存在/原请求匹配/terminal，60 events、10 模型工具调用（原 raw 11 含 renderer 内部读取），没有重新推理。修正 terminal 为最后 turn/end 晚于最后 turn/start，避免旧结束事件掩盖新轮次。Worker 只对 inspect/poll 最多三次观察重试，start/activate/cancel/restore 超时不重发。新增两项观察单测及六项重试单测；尚未完成现场恢复与时间门槛。

检查点已接入 PostgreSQL（迁移 0003）及 Worker 准备/激活/发送/观察/核验阶段，旧执行者、预算回退和审计长度回退拒绝。后端 17/17。新真实任务 `2f2e7edc-26e3-4561-af1e-bcee472c3bf6`、session `session-f833ddc7-c056-4203-8965-3d45ecf0afa5`：SUCCEEDED，Flash/off，11/30、17723 token；数据库检查点与结束后的原始账本/两产物独立重算一致、无未返回调用。尚未做故障恢复与长时间验收，P3 未完成；默认分支保持已验收 P2。

补充当前 P3 开发记录：方案 `8268dc1` 已先提交。新增只读检查点证据模块，检查原账本前缀、连续预算、未返回调用和已有产物 SHA；文件存在不能自行解除 UNKNOWN。新增六项反例/连续性测试，后端合计 16/16。该模块尚未接入 Worker 持久恢复，未做进程故障或 1/8 小时验收，不算 P3 完成。当前 API/数据库在线，单次验证 Worker 已退出，没有后台持续模型任务。

## 2026-10-02：P1 可核对日报通过，下一项 P2

- 新分支方案提交 fd392f3 后实现；首次冻结 20 组不同输入，17/20，三例仅 Markdown 尾部多一个 LF，被拒绝且原样保留。修正方案先提交 a09e45b，再加 opt-in 五工具 preset 与确定性排版工具。内部读+写各自扣预算、独立审计；旧 A1 工具权限不扩张。
- 新完整 20 组输入/期望逐字节核对与首轮相同，20/20 SUCCEEDED，模型调用 189、含内部读取 raw 209；每任务 9–12/30。两轮均实际 DeepSeek 4.1 Flash / off，保留所有失败成本；total token 327775→295128，原 turn 时长合计 153.772→135.342 秒，不把此单次对照称 P4 完成。
- Python 独立验收 12/12、核心 59/59、官方集成 29/29、VM Python 123/123；App 恢复原三个 A1 任务，账本哈希不变。说明、命令及限制见 [P1 总结](docs/stages/p1-summary.md)。P2/P3/P4/P5 尚未完成，C3/第二人继续暂缓。

## 2026-10-02：单人真实 TextEdit 任务收口

- 新模型任务真实输入、保存、result.txt/读回与预存期望独立一致，最终 `real_textedit_20261002_006` 为 SUCCEEDED；12 模型调用、1 错误、一次输入、两次有独立新观察的 Save。业务 14 raw，结束后在线 verify 的观察被 Driver session 生命周期拒绝，合计 15/30；HTTP 409 原样保留，没有 guest 验证报告。最终依据原始保存后新 AX/PNG、当前完整文件及原始轨迹只读核对，不声称结束后重新截图成功。
- 001–005 五次失败、错误文件和预算全部保留，修正只作用于新 opt-in TextEdit bridge，不改期望或原 C0/C1/C2 registry。10 项实际 HTTP 拒绝通过、停止后派发 0；独立证据收集 PASS。详见 [真实应用总结](docs/stages/real-app-summary.md) 和 [实施方案](docs/stages/real-app-design.md)。
- executor/本次 TextEdit 已退出，VM/Driver 保留；App 恢复 A1，原预算仍 10/30、30/30、1/30。核心 59/59、官方注册 26/26、Python 123/123。同步 README/设计/计划/接入说明，不提交或推送。只完成一个受控真实应用任务，不是广泛泛化、C3/第二人或 O0。

## 2026-10-02：A1 本地验收完成，第二人继续暂缓

- 用户确认继续后启动原隔离 VM，原 NAT/VNC 57593 保持；mvpagent 登录，SIP enabled、无 virtiofs，Driver daemon 自身两权限 true。十个 guest 源、C0 adapter 和 fixture 与原基线 SHA 相同；未修改 SSH/TCC/SIP或共享。
- 新 `a1_c0_mul12_34_20261002_001` 官方真实模型独立 SUCCEEDED，20/30 raw、17 模型调用；实际按钮、新 408 显示、result.txt/读回及独立期望一致。八项实际 HTTP 认证/角色/不开放 shell/停止后请求拒绝，仍 20，零新派发。
- 新 `c2_budget_a1_20261002_001` 真实 30 raw、28 新快照/PNG；两独立进程 1188→1482 预算仍 30，七拒绝、停止后零派发 PASS。新 `c2_inflight_a1_20261002_001` 实际返回 hold 后 stop 约 0.000308 秒、在途记录/拒绝/单次返回/接管后新观察通过，6 raw。两者是无模型安全诊断、业务 UNVERIFIED，不声称官方取消或业务成功。
- 宿主独立读回原 VM trace/报告/PNG 哈希和新官方 session，私有 `a1_vm_audit_20261002_001/verification.json` PASS。对应 executor/两诊断 fixture 已退出，VM/Driver 保持运行；App 正常恢复 A1，原三预算仍 10/30、30/30、1/30。
- 最终核心 59/59、官方注册集成 25/25、Python 103/103、原业务证据前缀 SHA 和 git diff --check 通过。同步 README/计划/接入/验收表及 `docs/stages/a1-summary.md`；按用户最新范围 A1 本地部分完成，第二人项暂缓未验，C3 跳过未完成。未提交、推送、发布或创建 PR。
- 下方过程中的 VM stopped、C0 回归或第二人阻塞等均保留当时事实，以本节最新范围/实际证据为准。

## 2026-10-02：用户确认暂缓所有第二人验收

- 用户澄清并确认：C3 继续跳过，所有第二人验收（包括 A1 的独立新增工具）暂缓，先完成 A1 本地部分。更新主计划、方案、README、接入说明、业务记录和验收表；保留第二人要求/交接清单为未验，不标通过，也不继续以参与者缺失阻塞本次本地收口。
- 本次剩余 C0 真实安全回归不随第二人暂缓而取消；最近只读检查 VM stopped，尚无启动确认。本轮仅调整文档范围，没有修改代码、运行配置、账本或 VM，没有提交/推送。
- 以下过程记录中的“第二人待完成/阻塞”保留当时事实，以本节最新用户范围为准。

## 2026-10-02：A1 审批预检与运行时统一

- 后续文件边界复核新增真实 A1 注册集成：21 类绝对/父路径、跨任务链接、最终内部/外部链接写入、列表逃逸、类型/二进制/大小、覆盖/额外 overwrite/root 参数、保护审计和目录/NUL 路径均拒绝，稳定错误码一致；两正常加 21 失败共 23 次派发与结果，原两个任务文件不变。官方集成现在 25/25，核心再次 59/59、Python 再次 103/103；无模型测试不替代 VM。
- 再次核对原业务 session/audit 字节前缀与独立报告 SHA，一致且未替换历史。原三个官方会话均 terminal、预算 10/30、30/30、1/30；Lume 再查仍 stopped。新增 `docs/stages/a1-acceptance-audit.md` 逐项保留主计划要求，明确 C0 新 VM 回归及第二人扩展没有证据，不登记 A1 完成。
- 新增只读 `a1-task-config.mjs`，启动预检与实际 policy service 复用；重复 session/run、真实或符号链接别名重叠根、重复/别名账本、审批或任一任务审计进入模型根均拒绝。五项核心反例核对不创建账本、不改配置；原策略限制不放宽。
- 新增同版真实注册集成：缺失/非法 JSON/重复 session/权限过宽四种审批配置对所有任务与模型请求拒绝、无派发或文件副作用；已批准的 fingerprint 在实际 policy 卸载后仍拒绝。核心 59/59、官方注册集成 24/24，git diff --check 通过。
- 确认所有官方会话空闲后正常退出 App，重新构建五插件/配置/启动，原三个任务恢复且预算仍 10/30、30/30、1/30；统一预检通过。没有重发业务请求、修改旧账本或 VM 配置。
- C0 新真实回归的只读环境检查：原 192.168.64.3 SSH 超时，同版 guest 源核对命令因此失败；官方项目隔离 Lume 的 get 检查明确 VM `mac-agent-mvp-15-6-1-restored` 为 stopped，进程清单无该隔离 VM 执行进程。不能推断端口配置损坏或声称完成本轮 VM 回归；没有启动/重启 VM 或修改 SSH/VNC。需要确认启动测试 VM 后才能继续真实 C0 回归，第二人独立扩展也仍待实际参与。

## 2026-10-02：A1 preset、图片、停止和持久预算核对

- 新只读任务 `a1_preset_20261002_001`：官方首轮前从 `a1-controlled` 切换 `a1-readonly`；实际模型只有 calculate/list/read/CSV 四工具，一次真实读回通过。禁用 standard 返回 not-found，首轮后切回返回 locked；没有绕过官方锁。切换时原业务预算 10/6 不变。首个独立 verifier 错把初始 preset 当作切换事件，按真实 session header 和 create 响应修正，原事件与失败说明保留。
- CSV 原会话真实工具返回图片 3 次、直接图片输入 2 次；随机 PNG 独立像素、受保护答案、颜色产物读回和 SHA 均 PASS，预算 6→9→11。第 12 次派发后用标准官方 cancel API，原轮次 aborted/user；请求取消及确认取消后均没有新派发，不冒充点击 UI Stop。
- 原任务随后新轮次实际派发 18 次至 30/30，第 31 次拒绝；正常 App 重启仍 30/30，新轮次真实调用请求再次拒绝，未清零或替换任务。`stop-budget-verification.json` 核对 30 个连续唯一派发/结果、取消时序及原预算 PASS。当前 App 为 A1，文本/CSV/只读预算 10/30、30/30、1/30，原会话均终止。
- 已提供 opt-in `workspace_text_fingerprint` 插件、schema、稳定错误码、取消及官方图片转换说明，以及不授予权限的等效流程。示例仅编译，不默认挂载或授权；正常/非法参数/越界/预取消/未批准有真实注册表测试。测试发现普通 Error.code 被官方丢失，增加 HarnessError 转换；额外参数显式拒绝，未通过放宽测试掩盖错误。
- 本轮无模型测试：`node --test agent/tests/*.test.mjs` 54/54；`node agent/harness/test-desktop-adapters.mjs a1-policy.integration.test.ts a1-csv-tools.integration.test.ts a0-policy.test.ts a0-policy.integration.test.ts a0-file-tools.integration.test.ts c0-vm-tools.test.ts` 22/22；`python3 -m unittest discover -s tools/mac_vm/tests` 103/103。不代替真实 VM 回归。以下 A1 早期记录保留当时事实。
- A1 未完成：C0 声明安全回归及第二位开发者真实独立新增工具仍需证据，不能由本代理或 mock 代替。C3 仍未做；没有提交/推送，VM/Driver/权限/SSH/VNC 未改。

## 2026-10-02：进入 A1，C3 暂缓（早期过程记录）

- 真实业务批次 `a1_business_20261002_001`：核对官方 API 的 124 个既有会话均无运行轮次，正常退出 App 后备份并切换 A1；原账号/旧会话/VM/端口保留。新文本与 CSV 各自授权 session、工作区和账本，模型实际选择 `deepseek-account/deepseek-flash` / high；实际请求工具清单只有六个审查工具。三文本 **8/30**、CSV **5/30** 通过独立完整字段/来源/输入字节/JSON及Markdown/两产物读回/哈希/官方 call-result与持久派发关联核对。初次文本验收暴露验证器末尾空行错误，按预先派发的“每条记录之后空行”规则修正，原产物与失败说明保留，不另跑模型或改任务数据。
- 新增三文本输入/独立字段验证器与反例测试、`prepare-a1-validation.mjs`；核心测试 **54/54**。期望与私有验证程序不在模型工作区，业务验收报告/原始证据仅在私有 `.runtime`。验证过的 session/audit 原字节前缀冻结，后续生命周期追加不替换原报告。
- 实际重启与续接：两任务预算 **8→8、5→5**，各一次真实 read 后 **9、6**。原 A1 preset 未配置压缩命令，补官方 basic/command-compact；首次 preset 恢复因 compaction 服务缺少 isolate realm 被上游拒绝，保留失败记录，修正为独立 Cordis 分组。重配/重启预算仍 **9、6**；官方手动 `/compact` 实际压缩 16 历史项约 3083 tokens，预算 **9→9**；压缩后真实一次读回 **9→10**，原业务证据哈希完整。独立 lifecycle 报告 PASS，仅覆盖本次重启/压缩，不冒充所有 A1 生命周期门槛。
- 当前 App 为 A1，文本/CSV任务分别 **10/30、6/30**。C3 仍跳过，A1 尚未完成；待 preset 切换、实际图片/取消/预算与 A0/C0 声明安全回归、通用插件/流程示例、第二位开发者独立扩展。未提交或推送。
- 后续接入进展：新增官方 Cordis `cuagentA1Policy` 服务、A1 六工具组合及模型请求 guard；配置按批准的 session 绑定不同且不重叠的目录/账本，所有工具正文要求活跃准入。复用 A0 文件/计算/图片注册函数，原 A0 入口和白名单不变；政策卸载后仍存在的 A1 工具拒绝执行。A1 构建输出在独立 `cuagent-a1-plugins`，未覆盖当前 A0 构建或改运行 App 配置。
- 新官方注册集成测试覆盖双会话目录、外会话/父路径/停止拒绝、实际工具与政策卸载重载、并发 31 请求只准入 30、私有配置改写拒绝和请求侧额外工具拒绝；总计 **19/19**，核心仍 **51/51**。首次重载测试期望 3 次但实际 4 次，检查确认卸载工具的失败请求也占预算；测试明确核对 4 次派发、4 个结果及其中 1 个失败，不删除失败记录、不改策略忽略请求。此为实际官方注册表测试，不是实际模型调用。
- 新增 A1 配置模板、独立构建、离线预检和 `start-a1-desktop.sh`。`node agent/harness/build-desktop-plugins.mjs --a1` 构建 4 插件通过；配置工具对运行中的 App 拒绝切换至 A1。尚未执行真实配置切换/启动，启动预检、真实三文本/CSV、重启/压缩/preset 等仍待验证。
- 本地实施进展：新增 `a1-csv-tools.ts`，使用官方 Desktop 同版工具注册表验证完整统计、输入哈希、13 类违规输入、预取消及 A0 白名单不可绕过。新增 `test-desktop-adapters.mjs` 只运行显式测试清单，不读取账号、不修改 App/profile。
- CSV 核心补齐三个实测边界：有限单元格求和溢出返回 `NUMERIC_OVERFLOW`，`__proto__`/`constructor` 列名仍作为普通数据输出，末尾空引号字段不丢失。新增独立 `a1-csv-verifier.mjs`，逐字段核对 JSON、完整 Markdown、来源字节/哈希和两份完整读回；故意错误统计、假表格、陈旧哈希、截断读回均拒绝。内容正确不自动标记任务 SUCCEEDED，仍需官方实际执行轨迹。
- 新增框架无关 `a1-policy.mjs`：固定授权 session/root/capabilities 身份，30 次写前持久计数，重启/失败不清零，重复 call、停止、会话串扰、权限变化、竞争实例、日志篡改及未完成旧派发拒绝；脱敏参数摘要、结果耗时、产物哈希和拒绝记录。8 项无凭证策略测试通过；尚未接入 App，不将该结果冒充实际插件生命周期/会话验证。
- 当前命令：`node --test agent/tests/*.test.mjs` **51/51**；`node agent/harness/test-desktop-adapters.mjs a1-csv-tools.integration.test.ts a0-policy.test.ts a0-policy.integration.test.ts a0-file-tools.integration.test.ts c0-vm-tools.test.ts` **15/15**；`git diff --check` 通过。均为无模型本地测试，不替代真实三文本/CSV、官方会话/配置生命周期、第二人扩展和实际 A0/C0 回归。
- 原执行层回归：`python3 -m unittest discover -s tools/mac_vm/tests` **103/103**，无实际 VM 桌面动作；不将单元/mock 通过算作重跑 C0–C2 真实任务。
- 下一步接入 A1 专用策略/文件工具与配置启动入口，再准备新三文本任务、真实业务执行及严格轨迹验证；A0 五工具白名单、原 App/VM/端口/凭证/旧账本不变。改动尚未提交或推送，A1 未完成。
- 从干净的 `7e7d42a` 建立 `a1-agent-expansion`，实施前写 `docs/stages/a1-design.md`，逐项保留主计划第 8 节要求，包括插件/会话回归和第二位开发者独立扩展。
- 只读核对 App 仍为 0.2.0-rc.2；源码 CSV 核心已迁移但尚无 Harness CSV 适配。A0 白名单和请求审计仅允许五工具，不能直接开放 CSV 或用旧 Pi 成绩替代。
- 先做新 A1 配置、适配与无凭证测试，再使用新的项目测试目录调用真实模型；原 VM/端口/凭证/会话/耗尽账本保留。不提交或推送，C3 未开始，A1 不提前登记完成。

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
