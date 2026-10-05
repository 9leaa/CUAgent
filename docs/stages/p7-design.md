# P7：三个复杂桌面工作流

2026-10-04用户明确授权助手设计并实施三个工作流。依次做项目周报与交接包、费用核对与异常清单、软件版本验收与缺陷报告，每项另开分支、方案先于实现。首分支`p7-project-handoff`从P6验收提交b113d35建立；这是用户批准的用途方向，不等于实际采用已经通过。P8易用性仍在其后。

## 三项范围与顺序

| 工作流 / 分支 | 输入、操作和交付 | 独立验收 |
|---|---|---|
| 项目交接 / p7-project-handoff | 多份项目笔记、任务CSV、上周报告；归并进展、识别延期/状态矛盾、形成负责人交接，在VM TextEdit保存带章节的周报交接文档 | 每项任务与来源对应、状态数量和日期由独立代码复核；冲突/未知明确列出，GUI保存后重开、读回、下载一致 |
| 费用核对 / p7-expense-reconcile | 测试收据PDF/图片及交易CSV；匹配日期/金额、发现重复/缺票/差额，在经审查的VM表格应用中整理 | 原票据逐项对照，金额用十进制定点运算，不猜模糊OCR；交付对账表及异常/汇总，无报销提交 |
| 软件验收 / p7-ui-acceptance | 固定版本测试应用、需求及数据；表单、非法输入、保存与重开，形成缺陷报告 | 需求-动作-新观察-实际持久数据四者对应；截图/复现步骤齐全，不因页面提示成功而判通过 |

后两项各自在开始前细化输入、应用可用性、工具边界和测试矩阵；不能在当前阶段先给模型开放表格、浏览器或安装权限。应用缺失先报告或另行取得安装授权，不操作宿主个人应用/真实业务数据。

## 首项产品契约

新增独立kind `project-handoff`，与P6的固定lines不同：输入是待处理材料，输出由官方Harness模型基于材料分析，不把代码预先生成的答案伪装成模型工作。首步仅定义不可执行的输入契约，不开放API/Worker路由。

请求包含project、asOf、1–3份notes（id/content）、tasksCsv、previousReport。CSV固定列`task_id,title,owner,status,due_date`，1–20项，task_id唯一，状态为todo/doing/done/blocked，日期严格YYYY-MM-DD；owner空值表示未知，不能自动分配。asOf无时间且不依赖系统当天。所有原文本保留字节意义，不裁剪/Unicode归一化；有界UTF-8、拒绝控制字符/双向文本控制、重复source ID、非法CSV结构及额外权限字段。输入总UTF-8预算32KiB，每笔记最多6KiB，上周报告最多8KiB，CSV最多12KiB；过限拒绝，不截断。CSV字段不执行公式或表达式，后续表格导出另审公式注入。

首版输入细则：project为非空单行≤256字节，note id/task_id为1–64位ASCII字母数字、下划线或连字符；title为非空单行，owner仅空字符串表示未知（拒绝非空纯空白）。多行材料只允许换行/回车/制表符三类控制字符，其余控制/格式/代理字符及Unicode行分隔符拒绝。previousReport可空，表示无上周材料。总预算按所有原字符串字段UTF-8字节之和（含kind、日期和来源id，不含JSON语法开销）；类型化模型冻结且notes/tasks使用tuple，source hashes按notes/<id>、tasksCsv、previousReport独立命名，不解析为文件路径。此步骤不开放API或执行权限。

专业上采用有来源绑定的中间结果和确定性校验；直白说，每条结论要说明来自哪份材料、哪项任务，不能凭空写“已完成”。后续结果契约包含任务进展/交接行动/问题清单、引用原文和源哈希。明确区分已知事实、跨来源矛盾、模型建议；建议不能改写成事实。数字/延期由冻结CSV和asOf复算；笔记与CSV不一致必须列出，不静默选择一个来源。只校验引用存在不足以证明归纳正确，冻结验收集需单独准备人工审阅的语义预期及应检出矛盾，语义不确定保留待确认。

主要桌面产物为一个带三大章节的周报交接文档，覆盖周报、交接清单、待确认问题三项交付；另附机器可读来源/核对索引，不能用三个章节的标题冒充完整内容。初版使用已核验VM TextEdit，正文编辑、保存、重开、完整读回都须真实GUI链路；宿主/可信程序只能存冻结输入、独立期望与原产物验收副本，不代写VM业务文档。后续若要Word排版或独立多文档，另加应用适配及预算验收，不能声称当前已有。

结果契约细则：结果绑定外部可信runId/sessionId及完整请求规范JSON的SHA（排序键、紧凑UTF-8，原字符串不归一化），避免仅材料哈希漏掉project/asOf变化。每项CSV任务必须恰好出现一次，原title/owner/status/due_date逐字匹配；状态计数、未完成且due_date早于asOf的逾期标志独立复算。每项有模型编写的progress和明确作为建议的handoff，均带1–8项原文引用；问题分conflict/unknown_owner/overdue/needs_confirmation，未知负责人及逾期必须逐项列出。冲突至少两项不同原文引用，但不据此推断其真正矛盾。

引用包含sourceId/sourceSha256/start/end/quote，start/end为Unicode码点下标（不是UTF-8字节），精确匹配未经裁剪的原文切片；拒绝重复引用、伪造哈希/引用/任务ID，单quote≤2KiB。模型描述每项≤2KiB、结果规范JSON≤64KiB，拒绝控制字符与多余字段；此结构上限不是GUI可保存正文上限。校验只返回STRUCTURE_VERIFIED_SEMANTICS_PENDING，semanticVerified/guiVerified均false，不登记SUCCEEDED、不生成GUI文档。语义遗漏/矛盾是否真实仍需独立冻结语义预期及人工审阅，不能让模型自己声明已验证。

## 执行、安全与预算

材料入口实施细则（2026-10-05，先于代码）：先实现独立HandoffDesktopTask，不改变P6默认DesktopTask或生产HTTP工具清单。可信host验证HandoffSubmission后，将完整规范JSON作为固定handoff-input.json传入VM原任务目录；激活时由可信控制侧绑定inputSha256，模型不能设置哈希或路径。模型read_materials一次读取完整有界材料并计原账本一次实际请求；不分页、不隐式多次IO工具、不把读取拆成子任务。每次重验lease/stop/30raw，通过目录fd与O_NOFOLLOW读取固定私有普通单链接文件，长度≤256KiB（JSON转义开销，输入文字仍受32KiB合同），SHA必须匹配可信输入。重复JSON键、非对象、非法UTF-8/非有限数拒绝，成功/失败都写原call_id审计；失败不清预算，重建对象沿原账本停止。读取清除旧GUI快照，之后动作必须重新观察。这个guest能力先本地验证；可信材料安装、独立kind路由、模型工具注册、生成结果与保存重开要完整接通后才允许实际启用，不在现有P6入口偷偷扩权。

材料传输细则：新增独立控制token专用/handoff-input，仅原运行时未激活且lease有效时接受binding/inputSha256/inputBase64三字段；binding逐项匹配run/owner/epoch及版本，拒绝模型凭据和任意路径。host先完整验证输入合同并规范化JSON编码，再检查实时数据库authority及guest租约，单次发送；ACK丢失不重发。guest严格解码、核对SHA/类型/固定输入字段，独占0600且fsync写intent→输入→receipt，部分写入或已有意图永不覆盖；租约过期后不能返回成功。控制请求只为该路由放宽至384KiB，其他仍4KiB；响应只含原绑定、SHA、字节数及STORED，不包含输入或凭据。P7任务激活/模型协议未接通前，检测到该意图必须拒绝原P6 activate，防止把交接材料误送入旧固定正文任务。部署白名单同步新增依赖，但不实际部署或启用。

P7激活细则：独立/activate-handoff只接受inputSha256，重新读取私有预置intent/receipt并核对原binding、状态、字节数与请求SHA；实例化HandoffDesktopTask后，在任何工具监听启动前核对原输入文件SHA/JSON，可信生命周期检查不算模型调用。与P6共享同一独占activation intent及失败revoke，不容许降级到P6、重放激活或换预算。模型协议仅在实际HandoffDesktopTask实例增加零参数read_materials；旧DesktopTask依旧拒绝该操作，模型不能调用两个可信控制入口。host沿原activate的状态/authority/租约时限与单次保护，只在成功预置回执存在时选择新路由。先验本地真实HTTP读取/停止/错误绑定反例，不启动模型；官方插件、报告生成与GUI重开仍需下一步接线才能完成业务。

官方插件材料工具细则：在原c0-vm-tools插件中仅显式caseId=project_handoff且stage=p7、有效p2 UUID与冻结inputSha256时增加vm_read_materials，复用原唯一会话owner、取消、固定VM URL和无重试请求。它与原TextEdit五工具组成当前六工具白名单，旧P6仍五工具；不得混入c2故障策略或省略绑定回退。读取无参数，响应必须精确为materials/inputSha256/used，哈希匹配配置且对材料规范JSON重算相同SHA，预算整数1–30，UTF-8规范材料≤256KiB。不把服务返回的SHA当作原文已匹配；原文内指令只作为材料返回。ready文件新增kind/inputSha绑定，仅新kind校验，不改P6就绪格式。先用安装版官方defineTool和本地模拟transport测试，既不发送真实模型请求也不替换活动profile；profile选择和session/业务报告仍另接。

会话与业务输出细则：P7独立project-handoff preset和kind绑定，不传P6 lines或预写答案。模型先read_materials，自行分析后通过GUI编辑三章节文档；最终回复仅一个符合HandoffResult schema的JSON（不带围栏/说明），作为机器可读索引留在原官方会话，host后续只读提取原末条assistant结果，不新增任意文件写工具。文档是该模型结果的确定性文本投影：项目/日期、周报、交接建议、待确认问题，保持CSV任务顺序，文本字段用JSON字符串表示防换行伪造章节；来源显示sourceId:start-end，完整引用在最终JSON。可信代码只生成独立期望字符串用于核验，不写VM业务文档；先结构/source校验再投影，语义标记仍待核验。当前TextEdit正文仍4KiB，超限必须明确失败不截断，不承诺20项最坏输入都能30raw内完成。

新会话创建前要求私有vm-tools-ready绑定原run/kind/inputSha，工具清单完整包含vm_reopen在内七项；目前插件只有六项，因此必须先拒绝而不能绕过GUI重开。随后才沿原一次create/selectModel/prompt持久意图，严格唯一project-handoff preset与Flash/off；inspect/cancel继续查询原session。P7 profile以显式prepare-handoff选择固定模板，原prepare仍P6；模板迁移移除另一preset，账号及原配置恢复机制保持。schema文件由HandoffResult生成并以测试对照防漂移；schema/提示不能替代运行时验收。先测试准备/会话RPC模拟和投影反例，不切换真实App，待重开工具及业务验证器完成后才实际放行。

来源SHA供给补充：模型不能可靠地心算SHA。插件完整材料哈希核验通过后，从原notes/content、tasksCsv、previousReport的UTF-8字节计算sourceHashes并附于模型工具输出；模型引用使用这些可信计算值。原guest三字段协议及整体inputSha不变，不允许模型提交覆盖摘要；跨语言测试核对单源SHA。

GUI重开细则：vm_reopen只接当前snapshot_id，必须本任务原PID/窗口的新AX正文与私有已保存文件一致且此前确有save动作。冻结原文SHA和独占reopen intent后，仅一次Driver Command-W关闭该窗口；最多三次预算内list_windows确认旧窗口消失，再由可信native回调向原PID/启动时间/固定TextEdit路径绑定的进程发送Open Documents AppleEvent，目标仅该run固定文档，禁止按应用名/默认应用重新选进程或新建实例。native调用使用NSAppleEventDescriptor（本机SDK声明核对）、NeverInteract和有界超时，不执行正文、不修改文件或处理保存/丢弃对话框。ACK不等于重开成功：最多三次同PID窗口清单确认唯一任务窗口，原文件SHA仍相同，清除旧snapshot；模型必须再次observe后才能write_result。重开后禁止继续type/save，结果必须绑定重开前冻结正文；只读材料读取仍计预算。

关闭、每次窗口清单、native打开分别计原raw；最多8次内部请求加后续观察/写结果/读结果3次，重开前至少预留11次（used≤19），不运行时扩预算。每轮等待≤0.1秒、每阶段最多3次查询，不盲重试关闭/打开；任何中途失败停止原任务、保留意图/原状态及UNKNOWN，重建对象不得重放。native打开回调仅可信runtime注入，loopback测试可模拟；旧P6无此工具或快捷键权限。先实现执行器和native适配反例，再做插件注册与独立证据核验；只有代码/本地测试不声称真实VM重开通过。

2026-10-04用户要求清理VM残留进程。检查发现P6只停止工具/桥接、不退出其启动的TextEdit，导致23个已停止测试实例积累；已逐PID关联原trace并持共享锁，备份63份文档/轨迹后正常请求退出，23个全部退出且原文件哈希未变，不强杀。P7真实运行前增加可信生命周期收尾设计：仅退出本任务明确启动且身份仍匹配的应用实例，先核对terminal/零在途/已保存产物，完成独立验收后正常退出并确认PID消失；未保存提示或退出未确认单独告警，不擅自丢弃内容或结束其他应用。收尾不作为模型新工具，不清预算/历史证据。该自动收尾尚未实现，不把本次人工清理称为长期修复。

仍复用官方App唯一循环，deepseek-account/deepseek-flash、reasoningEffort=off。原任务全程30raw，包括来源读取、失败、观察、GUI内部调用及重开；不拆子任务清预算。新来源读取只接受可信配置固定source ID，所有材料在VM专用目录，模型无任意路径、shell、网络或修改材料/证据权限。来源内的“忽略规则”等内容只是数据，不授予工具权限。

模型整理结果与后续GUI写入绑定同task/session/source hashes；新鲜观察、窗口身份、lease/stop/quarantine规则保留，不把P6固定正文核验直接套用动态报告。实施前分别细化结果契约、VM数据入口、桌面保存/重开与后端收集协议。预算不足即保留失败，不跳过重开/核验以通过。初版不承诺所有20项最坏输入均可在30raw完成；正式样本必须先冻结，失败全部统计。

P5目录、冻结源码/计划/数据库不动。开发只跑隔离测试，真实App/VM切换沿原批准窗口、实时额度≥40%、原积分/重置卡政策、空队列和恢复检查；到P5执行时间前停止占用，不提前授权未来日。不自动改VM/SSH/睡眠或清除隔离。P6源回归必须保留。

## 实施与验收次序

数据库发布事务补充（先于代码）：可信本地函数只收TaskService、原task ID与审阅SHA，run路径从DB读取并要求位于私有backend根下、名称为原p2-taskID；不接调用者生成的成功结果。按已有顺序锁desktop Resource再锁Task，拒绝资源占用、非UNVERIFIED、身份/输入摘要/预算不符、未关闭Attempt、未停止原控制文件、已登记产物或缺少原UNVERIFIED终态事件。锁内重跑发布准备，独占写发布意图和三份workspace文件，再以同一DB事务登记全部Artifact、原身份的唯一发布事件及finished/通知；旧UNVERIFIED事件保留，预算/session不改。任何意图后的异常保留原文件并回滚DB，重复拒绝，操作者查询原task/event判断未知结果。下载仍需SUCCEEDED及登记摘要；普通finish明确拒绝project-handoff成功，避免新增下载白名单成为旁路。先隔离数据库/模拟Driver测试，不开放模型或HTTP发布能力。

审阅后发布细则（先于代码）：发布不能只信REVIEW_ACCEPTED字符串。先提供只读发布准备入口，从原run/handoff-reviews/<原review字节SHA>读取review、意图和回执，核对当前OS uid、声明身份、目录摘要及完整回执，重跑原执行组合核验和独立审阅合同，二次读取所用文件不变。只返回经过原VM字节读回核对的document.txt、result.txt及原报告规范JSON和绑定摘要，不落盘、不写DB、不派发。后续发布事务须锁定原Task及desktop Resource，只接受原UNVERIFIED、相同输入/session/run/owner/epoch、已终止Attempt和撤销执行权；私有持久发布意图与唯一事件防止并发/响应丢失重发，保存原失败事件，不清预算或创建新会话。成功产物与新终态事件/通知同事务登记后才能由原下载门禁提供；文件失败或DB结果不明保留原意图，先查询不能覆盖重试。准备回执不等于发布成功，当前先实现可独立测试的重核验和原字节选择，DB事务/下载/生产路由随后接通。

可信本地审阅入口细则（先于代码）：adapter在完整执行核验后保存私有handoff-review-context.json（原输入/session/guest绑定及官方home），不含凭据；guest目录固定为原root/guest/run，不能由审阅文件指定。新增仅本地CLI的review记录入口，当前OS用户需有私有规范目录/单链接普通文件访问权，模型的七工具不提供此入口或host文件权限；身份声明另由CLI显式给定并与review一致，不把声明伪称密码学身份认证。入口重新读取原执行回执/context/独立审阅文件，重跑完整组合核验并与旧执行回执逐字意义一致，然后校验review合同。按review原字节SHA独占新建私有审阅目录，保留原record、意图及最终接受/未通过/拒绝回执；相同记录不重放，保存失败留原目录供核对，不删除或覆盖。记录所有失败，不输出原材料或异常凭据，不修改任务状态/产物/VM/模型；该入口只是后续发布准入的持久审阅凭证，发布仍需原数据库身份/状态及原文件重新核对。当前只处理冻结三组验收标准，未放开任意输入的自动语义成功。

独立语义审阅记录细则（先于代码）：先提供纯校验函数，输入由可信操作者提交的审阅记录、原提交/报告与已独立验证执行摘要及冻结case。审阅绑定run/session/inputSHA/reportSHA/sessionSHA/documentSHA/rubricSHA，审阅者显式标记human或codex及身份、带时区非未来时间；不能接受受测DeepSeek自评为独立审阅。逐个任务progress/handoff、每项issue、每条rubric要求以及全局无编造/建议与事实区分/GUI可读性都须恰好一项PASS/FAIL/UNVERIFIED及非空理由。PASS的语义条目必须引用实际报告文本的精确码点区间（任务项仅该字段、rubric项限其任务/关联问题），不以引用存在推断含义正确。任一FAIL/UNVERIFIED保留整体未通过，不删失败、不自动全选；记录格式通过不等于代码自动理解文本。只有外部真实独立审阅全PASS时返回审阅通过声明，明确独立人工/Codex判断来源、用户采用仍未评估。此模块暂不写DB/发产物或解除adapter门禁；后续可信操作员入口须私有保存记录并重新核对原执行证据，禁止模型工具写审阅凭证。正式三组的rubric限定是验收集范围，不冒充任意用户输入的通用语义证明。

正式语义验收材料（先于代码）：冻结三组独立输入与不发给受测模型的rubric，分别覆盖普通交接、跨来源状态/截止冲突、多负责人依赖/延期/未知负责人。每组保留2–3份笔记、CSV及上周报告；rubric明确应表达事实、必须标注的不确定性、禁止编造的结论、每项交接建议约束，以及期望状态计数/逾期/未知负责人/冲突任务集合。每条语义要求附准确来源摘录，代码仅验证rubric与原材料/数字一致，不以关键词包含冒充语义正确。正式运行前记录三份规范输入及rubric的固定SHA；后续同输入输出的独立审阅必须逐条判定并保留理由，模型无rubric工具通道。所有失败保留，不能换样本/改rubric迎合结果；测试fixture通过不算真实业务或语义验收。受测模型仍自行分析和GUI写入，独立期望不包含可复制的完整报告正文。

官方App启动补充：新增显式start-p7，不放宽start-p6原case。启动前检查P7连接stage/case/run/inputSHA；启动后只接受project-handoff单一preset及完全匹配原run/inputSHA的七工具ready回执，继续核对profile SHA、唯一进程和原启动意图，未知结果不重启。此检查也只验证mock生命周期，不能宣称已切换真实App。

P7任务适配器接线细则（先于代码）：复用P6原准备失败清理、端口选择/guest bootstrap/隧道、显式cutover与实时额度/数据库authority门禁；通过内部固定工厂分别选HandoffSubmission、HandoffSessionClient和HandoffControlClient，旧P6默认工厂不变。P7 profile用prepare-handoff，连接严格增加stage=p7/caseId=project_handoff/inputSHA；worker先续原guest许可后，adapter在切换App前单次预置材料，再沿原stop/apply/start/activate/最终gate/唯一prompt启动，不对未知副作用自动重试。核验从原私有session/prompt/binding提取独立正文，调用可信采集和完整组合核验，核对前后sessionSHA，保存私有执行核验回执。语义门槛尚未实现前明确拒绝返回SUCCEEDED或复制可下载成功产物，也不赋予应用退出的成功凭证；已有恢复路径保存未验清理告警。此适配器先无模型测试，不注册API/队列或执行真实任务；随后接语义审阅、业务状态及生产入口，不能把中间UNVERIFIED当最终产品目标。

P7后端官方会话接线细则（先于代码）：新增HandoffSessionClient复用DesktopSessionClient已有单次start/cancel、只读inspect/poll和原raw预算来源，仅替换prepare合同为重验HandoffSubmission并冻结kind/run/session/cwd/inputSHA五字段；不得把原材料或预生成报告塞入宿主提示。现有官方sessionCommand按kind选择已实现startHandoffSession，继续唯一project-handoff preset、Flash/off和七工具，Python不重写模型循环。准备、错误响应和未知退出都不重放原启动意图，旧P6 prepare仍拒绝P7输入。先通过无模型后端/官方命令合同测试；生产adapter/API、语义门槛与实际VM仍另接，不因客户端已存在宣称业务可用。

P7宿主采集接线细则（先于代码）：复用已批准的私有SSH wrapper和固定commit部署路径，仅执行handoff_export原run/owner/epoch；调用前确认原guest停止、零在途、非零预算及撤销lease，独占持久采集意图防重发。有界传输材料与从原会话得到的独立正文，私有保留原tar；调用后状态/预算/lease必须不变。严格解码后新建guest/<原run>私有证据目录，只按已验证固定名称独占写入，不覆盖或extractall；部分写入/响应未知保留原状态且不能重试。返回目录交已有组合核验，不把传输验证当业务成功。模拟SSH测试验证单次/拒绝/部分失败，当前不实际连VM或启用生产任务。

P7宿主包解码细则（先于代码）：独立纯内存handoff_bundle只接可信SSH采集的原tar、绑定身份、规范材料和独立正文期望。严格未压缩USTAR普通文件、固定名单及最多69成员/64MiB内容，拒绝重复、链接、PAX、目录、绝对路径、隐藏尾随数据和缺失配对state/PNG；不调用extractall。清单必须原kind/version/binding/输入与正文SHA，逐项长度/摘要等于实际字节、固定材料/文档/result一致；guest状态只是来源数据，仍需组合核验重算，不标业务或语义通过。此步骤不落盘、不派发、不解锁；随后采集端独占私有目录按已验证固定名称保存，接原会话组合验收。

P7可信导出接线细则（先于代码）：生产采集先增加独立handoff_export入口，不修改P6 lines导出合同。仅固定VM账户、原run/owner/epoch及已撤销lease可读；stdin只接有界materialsBase64/expectedBase64，后者由host原会话独立结果生成，不写guest业务文件。先运行完整handoff_evidence核验，再只读固定原材料/两预置回执/重开意图/trace/state/PNG/final/document/result，逐项SHA与长度一致且lease前后不变，全部读完后才输出USTAR。禁止导出token、lease或任意模型路径；清单绑定原身份、材料SHA、正文SHA及guest核验结果，session/semantic仍false。同步host/guest部署白名单及依赖，先用模拟真实执行器证据检验篡改/活跃lease/凭据排除，不实际部署；host压缩包解码与adapter路由随后接通。

组合验收细则（先于代码）：host先读取私有原session绑定/prompt/session字节，运行结果来源与结构核验以得到独立正文；固定本地只读子进程调用guest文件核验与双日志映射，不在backend临时修改全局Python模块路径。子进程仅接原guest证据目录/原session文件及有界绑定/材料/正文，输出摘要且绑定sessionSHA。host再按摘要读取原PNG、私有转换记录及官方引用附件，进行图片来源/实际字节核验。P7 llm/stream审计增加原run/session/inputSHA及每次请求实际imageAttachmentIds；每条审计与对应assistant步骤逐一核对此前官方工具图像序列、固定模型/七工具和时间顺序，不能仅凭“有图片”通过。最后重读所有读取过的host输入文件，变化拒绝。输出EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING，明确业务语义未验且非SUCCEEDED；入口只读、不授予许可、不执行/补跑模型、不自动清理应用。生产adapter、下载及冻结语义预期仍另接，模拟组合测试不得称真实验收。

P7有界观察投影细则（先于代码）：官方spill-policy按token预算保留头尾，超限加入[...]，没有可依赖的固定字符阈值。P7的vm_observe改用可独立复算handoff-body-v1投影：原snapshot/PID/window/app/title/截图有效标志/used，以及唯一属于目标AXWindow的AXTextArea完整正文、原index/token/enabled及最多16层原祖先链。移除菜单、重复tree_markdown与无关字段，不改变原索引/token/parent关系，不裁正文；有sheet/dialog、重复索引、歧义正文、失效截图/身份、正文>4KiB或投影>8KiB均拒绝并停止，不放宽spill预算或开放read恢复工具。guest全部原state/PNG/trace保留，Python独立按同一字段契约复算并精确比较官方投影，旧P6不变。8KiB仅是本地输出上限，不能承诺任意官方token配置均不截断；仍须真实原会话验收确认完整保留。

官方附件采集细则（先于代码）：已只读核对安装版attachment-local实现，normalizedImagePath为DSH_HOME/attachments/v1/objects/<SHA前两位>/<SHA>。新增只读受限采集器，只接受原会话与guest双日志匹配生成的观察附件清单，不列目录/搜索别的会话、不接受模型路径或display name。可信home必须本人私有规范目录；逐层目录fd/O_NOFOLLOW读取固定摘要路径，文件本人普通单链接且私有，单附件≤8MiB/总≤64MiB，验证实际SHA/字节数，重复SHA去重但元数据矛盾拒绝。每份证据二次读取并核对文件/目录身份和内容稳定；缺失/链接/变化/未知格式拒绝，不创建替代附件、不调用转换。此入口仅采集原始字节，实际尺寸/视觉语义不由PNG/WebP签名前缀推断；随后交给已有转换来源验证及组合验收。当前阶段不扫描个人home或执行真实模型。

图片转换来源细则（先于代码）：本地官方记录证明saveImage会将PNG转换为WebP，不能要求两种编码摘要相同。P7插件在一次observe返回后，使用同一已收PNG缓冲区交给官方saveImage；获得附件后、返回模型前，独占0600/fsync记录handoff-image-NN.json，绑定原run/session/inputSHA/snapshot/used、输入PNG SHA/长度和输出附件SHA-ID/格式/长度/尺寸。只允许原私有配置目录、固定1–30编号、本人规范目录、无链接及不覆盖；失败立即关闭本地派发并请求原任务停止，不重试观察或转换。记录不包含凭据、正文或任意路径，不新增模型工具或预算。后续可信采集读取附件实际字节，核对官方SHA-ID与长度，并把此转换记录和guest原PNG哈希、official观察附件绑定；该证据证明同次可信转换的输入输出，不声称独立视觉语义/像素无损。先测试原生文件安全和P7官方工具集成，P6不改变。

双日志映射细则（先于代码）：独立映射器先重新核验原guest轨迹，再从原read_materials结果、observation_evidence、输入/保存标记、reopened标记及write/read结果构造有序的七类逻辑调用，不能按总次数相等推断匹配。官方每次工具call/result必须唯一串行且顺序完全一致；材料原文/单源SHA/原used、观察完整state/used及图片附件元数据、输入snapshot/element身份/原文、保存和重开snapshot、write value/最终snapshot、read content逐项匹配。重开的多次内部raw仅归属一次vm_reopen，并核对其末尾used。所有结构比较区分bool/int且拒绝额外参数/多重文本结果。输出EXCHANGES_MATCHED，仍保持sessionVerified与imageBytesVerified为false：来源/终态由原session提取器验证，请求审计和附件实际字节必须在最终组合验收补齐，不能把图片附件ID或长度视为同图证明。

原会话结果提取细则（先于代码）：根据本地保留的官方v4原记录核对实际结构，assistant/message的正文位于data.message.content，最终输出不能从stream碎片、工具返回或任意嵌入JSON猜取。纯函数接受可信采集的原session字节、原prompt请求及run/session/cwd/输入；要求唯一v4原身份、project-handoff preset、非seed/delegation、严格递增seq、唯一原用户rpcId及完全一致prompt正文、单turn completed、Flash/off和完整七工具。所有模型assistant来源必须匹配固定provider/model，工具call/result配对且属于原轮次，最终assistant位于全部工具完成之后，仅含文本并解析为唯一严格JSON对象（拒绝重复键、非有限数、围栏、额外文字）。先完整验证HandoffResult来源/事实与身份，再计算独立正文；输出原session/最终消息哈希、消息ID及seq、结构核验和正文，保持sessionVerified/guiVerified/semanticVerified为false，待双日志逐工具映射、request-audit和VM证据合并后才升级，不把原消息提取冒充完整会话/业务验收。

文件证据核验细则（先于代码）：在P7独立轨迹检查之外增加只读handoff_evidence入口，可信调用者必须先撤销许可并确认零在途，传入原run/owner/epoch绑定、冻结材料字节和独立正文期望。仅读取固定私有run目录内的材料及预置intent/receipt、重开intent、原trace、每次观察的state-NN.json/PNG、final_state、固定文档和result；目录fd逐层O_NOFOLLOW，文件必须本人普通单链接、限定长度，拒绝FIFO/路径逃逸/重复JSON键/非有限数。材料及两份预置回执逐项绑定原身份/SHA/长度；重开intent逐字段等于原轨迹，最终状态等于轨迹核验指定的重开后新观察，文档和读回字节精确匹配独立期望。所有成功观察的JSON/PNG哈希与原observation_evidence一致，PNG签名只证明格式前缀，不能冒充视觉内容/语义证明。单次收集总量≤64MiB，返回前再次读回所有文件及核对根目录身份，变化拒绝；此检查不替代调用者冻结执行和可信传输。仅输出VM_EVIDENCE_VERIFIED并保持sessionVerified/semanticVerified为false，不直接标业务成功或触发应用退出。

独立轨迹核验细则（2026-10-05，先于代码）：P7单独实现纯读取轨迹核验器，不扩大P6验收白名单。外部传入原run、冻结材料及独立正文期望，核对连续1–30 raw、唯一且串行配对的dispatch/result、停止后零派发、无UNKNOWN。材料原规范字节/SHA必须在原read_materials结果出现且先于输入；输入与每次保存必须绑定最近一次新观察、同PID/旧窗口、30秒内且无中间请求。重开严格匹配唯一intent→一次关闭hotkey→1–3次窗口清单证明原窗口消失→唯一native打开结果→1–3次清单确认唯一同PID目标窗口→reopened标记；ACK本身不算证明。每个hotkey必须归属保存或唯一关闭，拒绝遗漏/重复/穿插动作。关闭前新观察与重开后新观察均须对应原文；最终write/read绑定重开后的最新观察及相同正文，重开后不得再编辑。

第一步只输出TRACE_VERIFIED，明确filesVerified/sessionVerified/semanticVerified均false；随后由固定私有文件采集器核对每个截图/状态、原intent/材料/文档/result/final_state及稳定哈希，再与原官方session结果和独立语义预期组成业务验收。不能让轨迹核验单独返回SUCCEEDED或启动清理。测试包括真实执行器配模拟Driver的完整轨迹、篡改顺序/窗口/材料/原预算/停止/中间派发等拒绝；本地模拟不冒充VM现场证据。

### 应用收尾实施细则（2026-10-05，先于代码）

收尾分为可信协调器与实际接线两步，不能只凭“同名进程”退出应用。启动后必须冻结本任务的run/owner/epoch、PID、进程启动时间和固定TextEdit可执行路径；收尾时重新读取相同身份，PID复用或身份查询失败均禁止退出。只有独立验收已完成、许可停止、模型会话terminal、零在途/UNKNOWN且已核验文件SHA不变，才请求一次正常退出。请求前再次检查这些条件；进程消失后复核文件与任务调用数，退出ACK不等于进程消失。最多3秒只读观察、不强杀、不点丢弃、不保存正文、不增加模型工具权限或重置预算。

每个run独占0600持久intent，先落盘再请求退出；重建对象或调用失败不自动重发。回执分EXITED、REFUSED、UNKNOWN，保留失败原因；保存回执失败必须向调用者报错，不能当清理成功。首先实现可注入的协调器及本地反例；随后接VM原生身份/正常退出、启动身份采集和host验收后的可信入口，并覆盖部署白名单、HTTP角色及恢复告警。协调器单测不代表已接通自动收尾。失败任务缺保存/验收证明时只告警并保留应用，不能为清进程丢弃未保存内容。最后在批准窗口做真实VM退出与文件不变验证，再启用P7业务样本。

原生适配细则：固定VM普通账户检查先于任何系统查询/退出；固定osascript JavaScript经AppKit读取NSRunningApplication的bundle、完整executableURL及launchDate（整数微秒）。未找到应用对象不等于进程不存在：另用signal 0核对，权限失败/非GUI进程拒绝，不猜退出成功。正常terminate在同一原生脚本内再次核对全部身份，只发一次请求；无kill/forceTerminate/保存对话框操作，单次子进程限3秒，原stderr不进入回执。该模块没有独立CLI或模型工具注册，只能由后续持锁生命周期入口使用。原生回调有界不等于整个协调器硬限3秒。

启动接线：仅生产DesktopGuestRuntime为DesktopTask注入可信launch observer，loopback测试默认不访问系统。首次launch_app前记录guest墙钟微秒，成功后在任何窗口查询/正文操作前采集原生身份；要求应用启动时间位于本次launch开始至采集完成之间，防止把旧实例误登记为自有应用。独占0600/fsync写owned-application.json，绑定run/owner/epoch/PID/启动时间/可执行路径，记录失败立即停止任务，不能再次launch。部署包显式携带两项新依赖；当前旧部署保持不动。该启动证据仅证明所有权，不自行触发退出，终态核验与收尾控制通道另接。

终态控制通道先接guest：新增仅独立控制token可用的`/cleanup-app`，严格接受sessionTerminal/sessionVerified两个true和document/result/trace三个SHA；这些声明只能由可信host在原官方会话独立核验后发送，不由模型填写。guest必须仍持原共享锁、原对象已停止/零在途/无UNKNOWN且有本次应用身份；再次运行只读GUI证据核验，核对原调用数与host哈希后才进入协调器。整个操作串行于runtime锁，清理不调用Task.stop以免改变已冻结trace。未知结果不重发、不清隔离、不把业务状态改成功；guest回执不是host会话核验的替代品。此路由先通过角色和篡改反例，再接host正式验收路径；没有host接线前生产不会自动调用。

host接线：只有adapter完成原会话与guest两侧验收、私有产物复制和verification回执持久保存，才在原context登记三文件SHA。restore先恢复原Harness配置，再在guest仍持锁时落独占清理意图、单次请求/cleanup-app并保存回执；严格核对run/owner/epoch、原哈希、PID/启动时间/固定路径、状态及非强杀声明，EXITED后才shutdown。清理拒绝/未知沿已有restore异常记录告警并隔离，不重试、不伪称恢复完成；业务成功和清理成功保持分开。没有验收证明的失败任务仅保存skipped告警并保留应用。客户端清理请求单独60秒socket超时（原普通请求仍2秒），查询/ACK未知不重发；跨对象重放由host/guest双重持久意图拒绝。

1. 输入契约及拒绝反例；不接API，不读取用户任意路径，不调用模型。
2. 来源绑定结果契约与独立验证器；冻结正常、中文、状态冲突、未知负责人、逾期、注入材料及篡改样本，覆盖不漏任务/不重复归并/不编造引用。
3. VM受限来源读取、单任务账本、TextEdit文档保存重开；先协议/模拟测试，再后端隔离路由，保持P6旧kind不变。
4. 正式真实样本：普通交接、跨来源冲突、多负责人/延期，所有尝试/原输入/结果/usage/人工介入保存；另验证停止/失权/30raw/引用篡改。失败不替换，不能只列成功。
5. GUI重开、原文件与正式下载独立一致；README/PROGRESS/总结、阶段提交推送。开发通过、真实验收、用户采用分开，再进入第二个分支。

尚未实现真实项目交接；本方案不是验收结果，不代表后三阶段完成。
