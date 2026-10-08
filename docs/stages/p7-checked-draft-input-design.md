# P7 已预检正文的显式 GUI 输入（实现前）

2026-10-08，继续 `p7-project-handoff`。007 原会话两次 vm_type 都仅遗漏三个问题编号的六个方括号，导致1263码点正文变为1257。原任务UNVERIFIED/16raw、文件为空；不修补原参数、不恢复原任务、不放宽逐字相等。新方案不是靠继续加强提示词或重复尝试同一版本。

## 契约与不变项

专业上使用绑定原任务的不可变草稿引用；直白说，模型明确选择“把刚才检查过的这一份正文输入这个文本框”，不用再抄一遍。报告内容仍必须由原模型基于完整材料生成；工具不生成进展、建议、引用或验收答案。输入仍经原GUI type_text，不写文档文件，不使用剪贴板，也不跳过观察、保存、关闭重开、正文读回、最终完整报告提交和独立语义/下载核验。

新增可信构造选项 `draft_input_mode`，默认 `literal-text` 保留旧契约；只有显式 `checked-draft-v1` 且已有可信session及 `p7-tool-submit-v1` 才能启用。模型不能通过参数切换模式。新模式仅开放 `vm_type_checked_draft`，替代旧vm_type；未全链接通前不注册、不部署、不运行。

输入参数固定 snapshot_id、element_index、element_token、documentSha256。摘要来自成功预检返回，必须等于当前原有效草稿正文重新计算的SHA；不接受路径、正文替换、run/session或额外字段。有效草稿、输入尚未发生、未开始重开、原新观察/目标白名单、停止/租约和30raw门槛全部保留。无草稿、错误摘要、旧观察、错目标、停止、失权、超预算或再次输入均拒绝；未知副作用不重试。

单次新逻辑调用只产生一次原GUI type_text raw；不是把多个系统动作藏进一次计数。拒绝仍沿HTTP原拒绝计费，不能重复计入一笔已准入raw。审计同时保留显式输入选择（mode、四参数、原used）和原实际type_text文本/目标及attempted_input；记录失败不能继续发GUI。执行成功后原input_once置位；原raw错误/UNKNOWN继续沿既有停止机制。

## 实施顺序和门槛

1. 先实现未暴露的执行端模式与方法，调用原GUI输入实现；无新HTTP路由、工具注册或运行时选择。测试原Task构造绑定、无草稿/错摘要/额外参数/直接旧方法拒绝及原输入账本，不能把模拟测试当真实桌面验收。
2. 独立验收按显式可信mode处理，重新计算原模型预检报告的正文和SHA，将官方选择参数、guest选择记录、实际raw文本、新观察、文件和最终完整报告逐项对应。不能仅核对摘要，也不能从输入记录猜mode；缺少或篡改选择记录拒绝。旧证据默认旧mode，不升级旧失败。
3. 将mode贯通原创建意图→连接→控制激活持久绑定→Task→ready/工具白名单→原会话请求审计→审核上下文及发布；所有层必须一致才开放。独立metadata `inputMode` 仅显式新模式出现，默认旧记录字段和行为不变；最终提交协议保持原语义。
4. Harness新工具schema只含四参数，返回保留原raw结果；新提示要求使用预检documentSha256并保留完整R供最终提交。仍要求模型核对输入后、重开后新观察；不自动把已预检对象当最终报告或业务成功。
5. 新旧全链反例和预算验证通过后固定新候选、部署独立读回、重新查额度和环境，再跑原三类完整业务。007/006及旧队列不改、不补跑；保留所有尝试、用量、截图和人工介入。完整P7和后续P8目标不变。

当前已实现第1步、轨迹/双日志及文件传输核验；原创建、控制激活和正式联合验收等接线未完成前，不宣称新输入链可实际使用。

第2步核验细化（代码前）：trace/exchanges接收调用者明确的draft_input_mode，默认旧模式严格拒绝新增选择事件；新模式必须有且仅有一次选择，紧邻唯一type_text派发之前，位于成功原草稿及其后新观察之后。选择记录增加resolvedText，必须逐字等于独立期望/原草稿；四参数与原观察、attempted_input身份、SHA一致，used严格为整数且等于派发前计数，禁止多字段、旧token、bool冒充整数及错mode。最后仍需原保存/重开/读回/完整submit证据。双日志在新模式仅接受vm_type_checked_draft四参数，不接受旧vm_type或混合文本参数；原输入成功结果也必须一致。此层不认证整个官方会话、不验证图像字节或语义，不能直接发布。

文件/传输细化（代码前）：新模式要求激活时独占保存的私有handoff-input-mode.json，严格字段version=1/inputMode/runId/sessionId/inputSha256，绑定原材料与草稿session；采集、导出CLI及host包解码均由调用者显式传mode，不从记录推断。新文件进入白名单并沿原两次读回/权限/链接/大小限制；旧模式拒绝新绑定，不能降级。新bundle manifest和guest/trace摘要显式记录inputMode，host核对同一mode、原绑定文件、原文档及result字节；包校验仍不冒充完整执行/语义认证。此步只接只读链，真实激活记录写入留待控制端接线，测试中的绑定是合成测试数据而非生产授权。

控制激活细化（代码前）：可信client在首次绑定原session时一次性选择draft_input_mode，仅checked-draft-v1新增inputMode字段，且必须配套p7-tool-submit-v1；默认旧请求字段不变。控制端只接受完整四字段新请求，拒绝缺session/protocol、未知模式、额外字段及模型凭据。原激活意图和租约检查后、构造Task和监听前，用O_EXCL/0600保存模式记录并fsync文件/目录；已有文件、部分写入或返回未知不覆盖、不重试，沿原撤权路径停止。旧模式遇新绑定文件也拒绝。Task获得可信模式，自动清理的只读核验传递Task原模式；本步不注册新模型HTTP操作或Harness工具、不切换生产创建入口。真实loopback控制测试必须证明0 GUI/0 raw、绑定持久化、重放拒绝和失败撤权。

宿主独立草稿/提交核验细化（代码前）：两入口增加显式draft_input_mode，默认旧模式拒绝新选择事件或工具。新模式在宿主原Pydantic/正文投影重算通过后，独立比较唯一选择resolvedText、documentSha256、目标四参数、派发前used、原type_text成功结果及attempted_input字节/摘要；官方唯一vm_type_checked_draft须在全部原预检响应之后，其参数及成功响应分别等于原选择和raw结果，拒绝混用vm_type、重号/重复响应及前置选择。最终提交核验传同一模式重验原草稿并显式返回inputMode；仍不声称完整会话/GUI/图像/语义通过，不直接开放生产联合验收或模型入口。

会话/联合入口细化（代码前）：统一按可信protocol和draft_input_mode生成精确工具集，新模式必须使用专用提交协议并以vm_type_checked_draft替换vm_type（不是增加任意工具）。原创建意图及session绑定必须同时显式保存inputMode；每步原请求审计也须记录同一模式和工具集，旧模式拒绝新标记。联合入口读取并重验私有guest模式记录，将显式mode传至原会话提取、宿主草稿/提交、只读inspect子进程及请求审计；子进程显式CLI参数沿原文件与双日志检查，不能从证据推断。结果携带inputMode但语义仍待审核；本步只接离线组合，不生成生产创建/审计记录、不开放模型入口。

审核发布细化（代码前）：新增严格v3私有review context，必须显式protocol=p7-tool-submit-v1和inputMode=checked-draft-v1；v1/v2保持原字段与literal-text语义，不推断或自动升级。record_review与prepare_publication均从原context取模式并调用完整联合核验，重算结果必须与原执行验证完全一致。新模式发布准备结果及持久publication intent保留inputMode；原语义FAIL/UNVERIFIED不能发布，审核后模式/原证据篡改拒绝。测试使用真实只读重验和模拟审核声明，不把回执/准备当已写数据库或真实用户采用。

HTTP入口细化（代码前）：仅Task可信checked-draft-v1替换允许操作type_text为type_checked_draft，其他P7/P6工具集不变。仍由原HTTP鉴权/大小限制/串行锁/charge_rejection处理；拒绝计一次原raw，已经派发后失败不双计，停止/失权/30次/UNKNOWN后不发新GUI。参数不得包含text、路径、session或模式覆盖；新操作不获得大请求例外。实测loopback成功和反例，旧P7/P6必须拒绝该操作。本步仅执行HTTP接线，Harness未注册且生产创建未选模式，不运行真实模型。

Harness注册细化（代码前）：仅可信P7 connection显式inputMode=checked-draft-v1且绑定原专用提交protocol/session时注册vm_type_checked_draft替代vm_type，schema固定四参数；执行原样转发到type_checked_draft，不补正文、摘要或身份。ready和每步请求审计保存inputMode，工具白名单仍10项、原session guard/停止/终态保留。工具说明提示使用原预检documentSha256并重新观察效果；同时修正专用提交模式重开说明为12raw预留（旧模式11）。未贯通创建/prompt前不部署；用安装版官方defineTool与模拟HTTP验证注册、schema、原样转发、拒绝和审计。

创建/prompt细化（代码前）：HandoffSessionClient.prepare显式接mode并独占写原desktop-request，未知或旧提交协议搭配新模式在写入前拒绝。App启动与session创建均校验connection/request/ready中的同一inputMode及替换后的精确工具集；默认旧字段不变。新prompt明确四参数选择、原预检摘要、不重复抄正文或直接写文件，保留完整R最终提交及D读回；替换旧vm_type.text指令以避免冲突。测试创建一次性、ready错配前零RPC、旧模式不变及提示仍保留30raw/12raw/完整业务门槛。后端operator/adapter选模式仍待后续贯通，不启动真实App。

后台接线细化（代码前）：operator新增显式handoff-input-mode（默认literal-text），checked-draft-v1只允许project-handoff及专用提交协议。adapter在prepare/原request校验/connection/控制绑定/会话提取/采集/联合验收使用同一模式并生成v3审核context；旧调用字段保持兼容。collector显式mode传原SSH导出CLI和host decoder，原单次intent、撤权/零在途、前后计数与租约复核不变，新intent/receipt保留inputMode。测试通过合成官方/VM记录走真实导出和独立联合验收，SSH/实际App模拟；生产启用须固定新候选、独立部署核对和新准入，不升级旧队列。
