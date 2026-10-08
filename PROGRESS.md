# CUAgent 实际进度

## 2026-10-08：已预检正文输入的文件采集与传输

- 在既有技术方案先补文件/传输细则，再实现只读链。inspect_handoff_evidence、build_bundle/导出CLI及decode_handoff_bundle接收可信draft_input_mode；默认literal-text保留旧模式，拒绝新绑定。checked-draft-v1要求私有handoff-input-mode.json严格绑定version、inputMode、run、session和原材料摘要，并沿原权限/链接/大小/两次读回检查；实际文档及result字节仍须完全一致。
- 导出固定白名单包含模式记录；新manifest、guest及trace的inputMode必须一致，宿主重新核对原绑定与文件摘要。输出仍分别为文件/传输核验，不宣称完整会话、图片语义或业务通过。生产激活写入尚未接通；测试绑定为合成数据，不能作为运行许可。
- 新增24项原Task＋模拟Driver文件测试，覆盖完整只读导出/读回、缺记录、身份/摘要/版本/额外字段篡改、公开权限、符号链接、旧模式降级、实际文档/result改变及采集后二次读回改变；宿主反例同时更新文件摘要，仍应拒绝错误模式绑定。相关六组pytest共137项通过，执行层unittest340项通过，原运行中的75项测试亦已确认完成。
- 未注册工具、未部署、未调用真实模型或GUI，未改P5源码和旧失败/队列。下一步接原创建/控制激活及联合验收，再开放HTTP/Harness并固定候选做真实业务验证。README已同步，P7及后续完整目标未完成。

## 2026-10-08：已预检正文选择的轨迹与双日志核验

- 按先行方案补细则后实现：输入意图保留resolvedText；trace/exchanges新增可信draft_input_mode参数，默认旧模式拒绝新事件。新模式要求唯一选择紧邻原唯一type_text派发、原成功草稿后新观察、四参数严格绑定目标和原摘要、展开正文等于独立期望、used整数等于派发前原计数。检查文本框原窗口祖先及循环/缺失/bool索引，原保存/重开/读回/完整submit和18raw重开准入门槛保留。
- 新模式双日志仅接受vm_type_checked_draft四参数和对应原成功结果，拒绝旧vm_type、额外text、错误摘要/目标/响应；显式返回inputMode，仍声明文件/会话/图片字节/语义未独立完成，不直接发布。原默认函数结果形状保留。
- 新增32项测试，原Task+模拟Driver生成完整17raw链并匹配合成官方日志；另有真实原账本30raw含最慢关窗/开窗查询和最终提交。覆盖选择缺失/重复/错mode、展开正文/摘要/计数/目标/顺序/父链篡改、草稿/提交缺失和重开后显示改变；相关后端五组98项通过。模拟图像和合成会话不是真实模型/GUI验收。
- 文件证据导出、host独立草稿门槛、原创建/控制激活/ready/工具集、审核发布上下文尚待传递同一可信模式。未注册新工具、未部署、未调用模型或修改旧任务。README同步，P7及后续完整目标未完成。

## 2026-10-08：显式已预检正文输入的执行端（尚未开放）

- dd7ed43先提交技术方案。Task增加可信draft_input_mode，默认literal-text不变；checked-draft-v1必须同时绑定原session和p7-tool-submit-v1。新type_checked_draft仅接受snapshot/element身份及documentSha256，重新算原有效正文摘要，不接受模型正文、路径或身份覆盖；调用原RealApp GUI type_text，不写文档文件。
- 原预检有效性、唯一输入、停止/租约/未知/原预算、目标和观察检查保留；显式模式不能通过旧type_text方法绕过。先记选择意图再GUI，审计失败不发动作；原一次raw计数不变，失败/拒绝仍由后续HTTP原规则处理。方法未进入HTTP或模型白名单、构造模式尚无运行时接线。
- 新增21项测试，含原raw路径只派发一次并逐字输入、文件未直接改变、摘要/参数/观察/权限/预算反例、UNKNOWN不重发和构造绑定；新方法与草稿/预算/提交Task/HTTP五组共72项通过，既有执行层340项通过，git diff --check通过。全部模拟GUI、无真实推理或部署；旧失败和队列未改。
- 下一步按可信mode接独立选择记录/原raw/官方参数核验，再贯通创建、激活、ready、审核及Harness入口。未完成前不开新实机候选，不能把执行端方法测试当产品闭环。README同步，P7及后续目标保持未完成。

## 2026-10-08：预算候选007部署、实机输入不一致及收尾

- host/guest均固定f068af24221c8aed089565207554ceaf78409220，独占新VM部署目录；25文件与manifest由VM独立重算摘要一致。私有候选清单冻结356源码哈希和原normal/conflict/dependencies输入/rubric，未修改006或旧失败。原VM经已有授权凭据正常解锁并见Finder；未更改认证、共享、睡眠或SSH配置。
- 新独立API18126及三原始任务创建完成；只执行normal 8f2bca49-baa2-417b-922d-96e15ef902f2，官方session-cce3c5e2-58a6-4100-a847-cefc5420d116、Flash/off。执行前真实额度83%剩余、普通额度可用、积分原值、两卡均available，记录绑定原任务且5分钟有效；没有未来许可。
- 原会话completed但任务UNVERIFIED/16raw、DESKTOP_VERIFICATION_FAILED。材料1、定位7、有效预检1、首次观察3、两次输入拒绝和两次再观察共4。没有180秒超时停止，也没有真正输入、保存、重开、result或提交。原会话及guest双记录显示输入请求均不同于预检document：1263码点被重写为1257，首差异在882，两次仅漏掉[N1]/[N2]/[N3]的6个方括号。独立离线比较回执不修改任何原证据；不能将其自动补正后计成功。
- 用量available：input15044、output25668、cacheRead148992、cacheWrite0、total189704，monetaryCost未知/null；无重复累加缓存。另两例维持QUEUED/0raw，本批不再派发。
- 原操作器撤权并恢复配置，无隔离。随后确认原TextEdit PID/出生时间、原任务终态与共享资源空闲，停精确基础Worker并持共享锁，通过原VM菜单正常Quit；本次锁内VERIFY成功、原0字节及空文件SHA不变，未发生清理超时。恢复Worker22845；新就绪回执确认配置恢复、P5源码不变、无TextEdit、无隔离、桌面资源空闲。
- 此结果证明定位次数下降，不证明预算问题已经完整实机验收；当前新问题是模型重复抄写投影时改变正文。下一步先设计减少重复抄写的受控输入契约，保留原完整模型报告、GUI输入、逐字核对及独立语义/发布门槛；不靠更多提示重跑相同版本碰运气。README同步，P7及后续目标未完成。

## 2026-10-08：新协议完整收尾预算及原账本回归

- 按先行方案0041b11实施：handoff_task.reopen仅显式p7-tool-submit-v1要求剩余12raw（used≤18），覆盖重开最慢8次、观察/写/读/提交各1；旧协议仍11raw（used≤19），原30上限、停止/租约/失败计费不改。拒绝发生在持久意图与关闭动作之前。
- 新协议提示说明草稿成功时至多已用11、常规首次GUI到保存后观察7、最多9次引用定位的规划上界；失败或额外观察占原额度。允许实际支持陈述的原引用复用，禁止省业务、漏冲突、伪造区间、扩大证据或藏匿实际请求计数。默认旧提示不添加这段规划。
- 新增4项原Task＋模拟Driver测试：新18/旧19准入，关窗和开窗均第三次查询才确认，完整尾部恰用至30；新协议真实调用submit_handoff成功后禁止后续请求。新19/旧20拒绝，无Driver、原生重开或意图文件副作用。测试前段为合成有效草稿/已保存状态和原账本padding，不冒充完整真实GUI或业务验收。
- `python -m unittest discover -s tools/mac_vm/tests -q` 340项通过；预算/提交Task、HTTP、联合证据、草稿六组pytest共92项通过；`node --test agent/tests/handoff-prompt.test.mjs` 5项通过。git diff --check通过，无模型推理、未部署，不更改006任务或P5。README同步，尚须新固定候选及三组实机业务验证。

## 2026-10-08：候选 006 真实失败及预算修正设计

- 解锁原 VM 后新建并执行冻结候选 006 普通交接，host1d492b0/guest454da53、Flash/off、p7-tool-submit-v1；真实新额度检查剩余85%，普通额度可用、积分保持原值、重置卡未使用。该读数只用于本次已结束窗口，不授权未来调用。
- 原任务 STOPPED/24raw；材料1、引用定位14、草稿预检1、首次观察3、输入1、输入后观察1、保存1、保存后观察1、重开拒绝1。原预算23时已不满足重开要求的至多19；180秒期限发出停止。无重开意图、result读回或submit，不能称新提交协议实机验证通过。原usage不可用且计数为null，未填零；另两项仍QUEUED/0，不补跑失败样本。
- 人工清理三次等待均超时，原超时及Worker恢复记录保留。Screen Sharing坐标通道通过移动本地查看窗口后可用，VM TextEdit正常退出；后续独立只读回执确认无TextEdit、2465字节及原SHA不变。该复查未持人工清理锁，不冒充锁内自动清理验收。最新就绪回执确认基础Worker20613存活、资源空闲、原配置恢复、P5源码哈希不变、无隔离；未改VM安全/SSH/睡眠配置。
- 新协议重开后还需要最后一次submit，原11次预留未包含它。先写docs/stages/p7-budget-planning-design.md，明确新协议12次预留和进入GUI前的raw规划、保留旧协议及全部业务要求。仅完成源码核对、原始失败分析、收尾复查和方案，未实现预算修正、未新增真实推理或重跑测试；前次664项是历史测试结果。README同步，P7未完成。

## 2026-10-08：候选冻结、完整回归与宿主锁屏阻塞

- 本次实际尝试Screen Sharing显示名和com.apple.ScreenSharing均返回cgWindowNotFound；应用清单确认进程存在，不据此声称VM掉线。宿主ioreg只读核实hostConsoleLocked=true、console screenLocked=true；上一就绪检查VM也锁屏。没有输入宿主密码、绕过认证、修改睡眠或重启服务。
- 运行全部backend/tests/test_handoff*.py及test_desktop_deploy.py，共664项通过，1条既有Starlette弃用警告；使用随机隔离测试DB，未派发真实模型或桌面动作。此次覆盖超过此前局部新协议回归，但仍不等于业务验收。
- 私有p7-submit-candidate-006/manifest.json已独占0600冻结：host1d492b010567401adaa57c6ebe2204c9a54e6916、guest454da530408b0200348812aad452bc9822d9e122，355份源码哈希、三组原输入/rubric摘要和部署回执摘要；guest源码两版本无差异。状态FROZEN_NOT_QUEUED、taskIds为空、modelRequestsStarted=0，未开新API或重复创建旧任务。
- 当前真实执行需要宿主及VM正常解锁、重新读取账户额度与实时准入，再创建新协议候选的原任务并跑三组。未授予未来quota许可；旧失败与旧剩余队列保持原样。README同步，P7及整体目标保持未完成。

## 2026-10-08：新协议guest部署与预设完成指令冲突修正

- 只读就绪检查：基础任务空闲、resource无owner、配置恢复、P5冻结源码哈希不变；原worker99106存活，VM普通mvpagent/VirtualMac2,1、无隔离告警或TextEdit进程，但锁屏。旧002–005剩余各两项QUEUED/0raw保持原状，没有重跑或升级。
- 固定454da530408b0200348812aad452bc9822d9e122，通过原SSH安装器独占新目录部署24个Python文件及许可证共25项；在VM重新计算每个SHA及manifest摘要与宿主包一致，私有p7-submit-deployment-006/verified.json保存结果。仅文件部署，servicesStarted/modelRequestsStarted均0，没有GUI、解锁、配置切换或quota授权。
- 随后全链审查发现persona高优先级仍无条件要求最终JSON，与新增tool提交冲突。339458a先写修正方案，现persona按原任务显式协议区分新工具提交与旧JSON，新prompt明确p7-tool-submit-v1且不得切旧版；不从可用工具猜协议。增加静态提示一致性和真实固定编译后profile/插件测试。
- 使用CUAGENT_TEST_BUILD_TOOLS指向既有固定esbuild依赖，node --test agent/tests/*.test.mjs共145项通过、0跳过；只在测试临时home构建，不修改实际App配置。git diff --check通过，tools/mac_vm对部署commit无差异。宿主提示变更需列入后续新候选冻结；真实三组业务仍待VM可用及新账户核对，P7未验收。

## 2026-10-08：生产单任务入口与新审核版本贯通

- 71bc058先写方案。desktop_operator增加显式--handoff-protocol，默认legacy-final-json，仅project-handoff可选p7-tool-submit-v1，未知/错kind在IO前拒绝；原指定任务launch意图记录新协议，保留原额度、未尝试QUEUED、共享锁和实时门禁。新协议不是自动升级开关，既有005失败及剩余任务不使用它。
- HandoffTaskAdapter构造选择协议，prepare_session钩子将其传给原会话prepare；新连接从0600创建请求获取可信session并核对run/cwd/input/版本，控制端bind使用同一协议，verify核对原意图后显式提取及联合验收。新结果写v2审核上下文，旧写v1；两者仍抛HANDOFF_SEMANTIC_REVIEW_REQUIRED，不直接发布。P6默认prepare路径不变。
- 六组pytest共103项通过：新旧adapter原Task/模拟Driver完整证据、v1/v2审核和清理摘要、创建缺失/篡改/公开权限、原单目标数据库执行与协议选择、旧任务不被选中及P6回归。测试使用既有独立Postgres连接，每项新建随机测试数据库后清理；App/SSH/VM边缘仍模拟，无真实模型。首次运行1项fixture None参数错误及15项未加载测试DB环境导致setup失败；修正fixture并加载既有私有环境后完整重跑通过（保留原Starlette弃用警告）。CLI help和git diff --check通过。
- 下一步核对整个新协议生产链、固定候选源码与部署清单，再按原授权/额度/VM限制执行新三组业务。尚无新实机结果，不把模拟链当P7完成；README和backend命令说明同步。

## 2026-10-08：显式新会话创建、App就绪与提交提示词

- a2a523c先写方案。HandoffSessionClient.prepare支持显式protocol，默认仍旧；新版独占desktop-request包含新版本，不覆盖旧请求。startHandoffSession仅接受既有字段或额外的正确新协议，新版ready必须绑定同session/protocol/完整十工具，任何错配在RPC前拒绝。App启动门槛使用同一清单并核对session/protocol，未知协议在启动前拒绝。
- 新prompt保留完整业务来源/引用/GUI保存重开读回/30raw要求，增加submit预算；最终report传完整对象，紧邻成功read_result，工具结束本轮，失败或未知不重发。旧最终文本JSON要求仅留旧协议；同一显式版本控制白名单，不从现有工具猜测协议。
- 新增Python原始请求版本/0600/禁止覆盖3项；相关Python30项通过。新增Node新提示词、五种会话创建/错配/禁止重放及四种App就绪测试；完整agent/tests共142通过、2原跳过。全部使用模拟RPC/App，未真实启动App、部署或请求模型。
- 生产operator/adapter尚未选择新协议，后续须将可信版本贯通连接生成、控制激活、联合核验和v2审核上下文，再固定新候选验证；既有005失败及剩余旧队列不改协议。README同步，P7/后续路线仍未完成。

## 2026-10-08：Harness提交工具与官方终态接口

- d90f862先写设计。新增handoff-submit.ts，完整report schema保留现有$defs并注册vm_submit_handoff；c0-vm-tools仅可信新协议+固定session连接开放第10工具，新ready记录包含协议/session，旧P7/P6工具集不变。首次owner必须等于可信session，模型不能传参切版本。
- 提交HTTP前即pending，官方单调guard阻止并发/后续工具；传输门禁、agent/pre-step及llm/stream阻止绕过工具体或继续请求模型。核对VM响应身份/协议/摘要形式/原预算后调用官方concludeTurn；不可变tools/result核对同一execution的原value/content，只有最终成功才committed。HTTP失败、丢失、取消或外层管线改错均锁止并stop，不重试、不清预算、不修改官方循环或启用子Agent/PTC。host仍负责完整报告/摘要/来源独立验收，局部终态不证明业务成功。
- 用安装App的同版ToolRuntime运行14项集成测试（VM响应模拟），涵盖成功终态、并发、后续工具、丢失、错身份/协议/预算/摘要、错误语义标志、取消、外层失败与后置输出替换。首次fixture遗漏辅助测试工具的必需output声明导致14项失败；补齐fixture后完整重跑14通过。c0适配器12项通过，含新连接/十工具/固定owner/后续工具体及新模型请求拒绝。Node agent/tests回归132通过、2原跳过，git diff --check通过。
- 仅本地构建与安装版无模型registry测试，没有真实GUI或账户推理；生产adapter/desktop-session/prompt仍旧协议，下一步显式贯通新创建记录和审核上下文后再冻结部署。旧失败与P5不变，README已同步；完整P7/后续路线未完成。

## 2026-10-08：控制端首次激活协议与原始证据贯通

- 0fcb2ff先写方案。bind_draft_session在首次激活前一次绑定session/protocol，默认旧协议；只有显式新协议才发送protocol字段。VM独占激活意图之后、Task创建之前，独占写入0600 handoff-submission-protocol.json，绑定version/protocol/run/session/input，原记录冲突不覆盖、失败撤权且禁止重放。
- guest导出、host bundle和联合核验都要求新提交原协议记录；严格规范JSON比较拒绝布尔版本、降级、错session/input、多字段或缺失，原文件权限和收尾重读复用已有检查。旧激活不新建协议文件，生产adapter仍默认旧协议。
- 真实loopback控制请求覆盖模型凭据拒绝、首次成功、重复激活/再绑定拒绝、缺session/错协议及既有文件保护；模拟完整链覆盖导出和联合验证，篡改后即使同步manifest摘要也拒绝。七组相关pytest共122项通过；tools/mac_vm/tests unittest 340项通过，均无真实GUI/模型推理。新增反例测试首次3项因误用manifest顶层files失败，改成实际guest.files后全部重跑通过；未修改原运行证据。
- Harness注册/结束本轮门禁及生产会话版本贯通仍待实现，未部署或请求模型，不能称P7业务完成。README同步，冻结P5及旧失败保留。

## 2026-10-08：显式Task协议与HTTP提交入口

- 990e2d9先写设计。Task可信构造参数submission_protocol默认legacy-final-json，新协议必须绑定session；submit_handoff自身及HTTP允许操作集都检查显式新协议，旧P7不因代码升级扩权，P6原白名单不变。模型参数不能切换协议。
- P7提交信封允许既有512KiB上限以容纳JSON转义，规范完整报告仍64KiB；其他操作原32KiB限制不变。原task锁、身份、停止/租约、30raw和拒绝计数复用；终态后拒绝请求不增加raw派发。
- 新增9项真实loopback HTTP测试（模拟GUI生命周期）：成功提交、重复/后续动作、无读回、改报告、注入协议参数、超大报告、错误凭据、停止/撤权及旧协议直接方法/HTTP均拒绝。相关61项，独立证据/导出/审核47项，共108项通过；执行层340项通过。
- 真实控制端激活尚不传新协议，Harness尚未注册第10工具；新入口未部署或实际派发。旧失败与冻结P5保持原状，P7仍未完成。

## 2026-10-08：新协议独立审核与发布准备入口

- ab9455a先写方案。新增共享review_protocol严格解析私有审核上下文：v1仅旧字段/旧协议；v2必须额外且仅有protocol=p7-tool-submit-v1，不接受布尔版本、未知值或静默回退。record_review和prepare_publication使用同一版本重新核验原执行证据及原execution完全一致。
- 新增9项完整模拟组合：正常来源、原Task/模拟Driver/模拟模型及合成审核声明，经v2重新验收、审核登记和只读产物准备通过；上下文缺失/未知/降级/多字段、审核FAIL/UNVERIFIED和审核后版本改变均拒绝发布。原产物字节不变，未改数据库/实际发布；合成审核不当作真实语义通过。
- 新旧审核/发布41项、联合验收与旧适配32项，共73项通过。实际任务创建/模型注册尚未同步新协议，未部署或派发；P7及后续完整目标仍未完成。

## 2026-10-08：新协议原始意图绑定与离线联合验收

- a179215先写方案。verify_handoff_execution增加显式protocol，默认旧协议；新协议要求原私有desktop-request.json及desktop-session-binding.json完整匹配可信run/session/cwd/input和p7-tool-submit-v1，不从模型内容推断版本。原记录加入结束前重读，沿原文件身份/权限/大小校验。
- 提取和请求审计同版10工具，接host独立提交核验并与提取报告逐字canonical匹配，再联合原guest trace/exchanges/export、图片字节和原审计门槛。返回显式protocol/submissionEvidence，但仍仅EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING，不宣称语义通过。
- 新增9项联合测试：原Task/模拟Driver/模拟官方会话的18raw链经真实只读子进程通过；原意图缺失、公开权限、摘要/版本变化、旧工具审计、guest session不符和默认旧协议误用均拒绝。相关32项及会话/证据/导出/人工审核旧链70项，共102项通过。
- 生产创建、HTTP/Harness工具和人工审核新协议上下文仍待同步；没有模型调用、部署或旧任务升级。P7业务和后续计划未完成。

## 2026-10-08：显式版本化官方会话报告提取

- 4f620cf先写方案，extract_handoff_result增加可信protocol参数，默认legacy-final-json保持原最终纯JSON路径；只有p7-tool-submit-v1允许第10个vm_submit_handoff工具。仍核对原未委托/未seed会话、cwd/prompt/RPC、单轮completed、Flash/off、完整声明/调用/结果配对。
- 新协议报告只取唯一原模型提交声明的完整arguments，逐字匹配tool/call；提交必须为最后调用/结果和最后模型消息，后续模型请求也拒绝。成功响应严格比对协议/run/session/input、独立报告/正文SHA及整型预算范围；不从普通文本/返回值/流片段猜报告，缺提交不回退旧JSON。
- 新增19项测试：显式协议、身份、参数字符串/重复键/信封、失败/缺结果、预算布尔/越限、提交后消息/请求/工具和旧协议不自动升级。会话/提交证据相关78项，旧联合验收/适配/草稿组合35项，共113项通过。没有调用模型或部署；生产调用点仍用默认旧协议，可信创建意图与协议绑定、HTTP/Harness及新联合入口待接通，P7未完成。

## 2026-10-08：提交轨迹、双日志与导出链

- 85c3fd8先写设计。handoff_trace识别唯一末次submit_handoff，要求原有效草稿/可信session、原参数canonicalJson及重新计算响应一致，成功read_result紧邻提交，提交结果前stop和结果后新派发均拒绝；handoff_exchanges补原vm_submit_handoff参数/响应逐项匹配。旧无提交轨迹读取不变，不把旧业务失败改判。
- 原Task配模拟Driver，保留一次坏草稿、一次有效草稿、GUI保存重开及result写读，再真实调用新提交方法：18raw/13逻辑调用，完整trace/exchange、host独立草稿/提交核验及原导出包读回通过。原17raw无提交链仍通过；两者都不是模型/GUI现场或完整会话验收。
- 部署构建器/VM安装白名单加入handoff_submit.py，为24个Python模块加license共25文件；构建另读installer共26次git show。首次相关测试47通过/1失败为旧25次读取断言，更新为26后48项全通过；执行层340项通过。没有实际部署、服务变更或模型请求。
- 新协议尚未进入官方会话提取、HTTP/Harness与正式联合入口；不得依据局部通过开放工具或宣布P7业务完成。

## 2026-10-08：宿主独立结构化提交证据门槛

- de6c0e5先写设计，新增handoff_submit_evidence.verify_submission_evidence：独立使用host Pydantic/草稿核验，不调用guest提交校验作为真值。唯一提交必须为末次raw且计连续预算，原run/session/input一致、紧邻成功read_result，原helper_arguments/result与官方唯一vm_submit_handoff的完整参数/成功响应逐项一致；停止先于提交完成、重复提交及后续工具调用均拒绝。
- 原Task配模拟Driver完整链17raw产出提交，保留假截图/模拟官方会话的测试性质；返回SUBMISSION_EVIDENCE_MATCHED并明确session/gui/semanticVerified=False，不升级为业务通过。新增20项原生产者/篡改反例，与既有草稿证据和导出组合共50项通过。
- 尚未将新门槛接正式联合入口；通用trace/exchange/export、模型工具注册与官方结束本轮仍待完成。没有部署、模型请求或旧证据修改。

## 2026-10-08：结构化提交执行端与终态门禁

- 24372e0先细化设计。HandoffDesktopTask新增未开放submit_handoff：完整对象校验、可信session及原输入/保存/重开/写入标记、紧邻成功读回，原document必须等于预检正文并保持reopen摘要，result文件重新有界读取且拒绝链接/非普通文件/多硬链接，与原读回及正文+LF一致。
- 走原admit/lease/30raw审计；在提交锁内再次核对stop/lease。原helper_arguments和result通过既有fsync记录，成功后单调终态拒绝后续准入，写失败停止、不自动重试；重启沿原账本恢复预算且保持停止。其他准入调用使旧读回绑定失效。工具尚未HTTP注册或模型可见。
- 新增19项Task模拟生命周期测试，覆盖缺前置、来源报告变化、文件篡改/链接、读回失效、重复提交、停止/撤权竞争、30raw、审计失败和重启。相关59项加HTTP/完整草稿组合16项，共75项通过；执行层340项通过（负例预期输出P7_GUEST_EXPORT_UNVERIFIED）。不是新协议完整组合、真实模型或GUI验收；独立trace/exchange/export、Harness权威结果结束本轮及正式发布仍待实现。未部署、未派发或修改旧失败。

## 2026-10-08：结构化提交获批及首层校验

- 用户明确同意更改最终交付接口；先提交462475f记录实施顺序，沿既有P7阶段分支开发，冻结P5不改。
- 新增guest标准库handoff_submit.candidate，只接受完整report对象；有界遍历/深度/字节校验，拒绝非JSON类型、非有限数、坏Unicode、循环和额外信封字段，按原可信run/session/source重验并与末次有效草稿的canonicalJson、document和摘要一致。不复制草稿冒充模型提交，不做文件写入、GUI、发布或成功标记。
- 新增21项测试，与独立host草稿校验交叉；结合既有guest草稿测试共60项通过。测试覆盖身份/事实/文本变更、草稿缺失/替换、键顺序、大小及异常对象。尚未接HTTP/Harness、预算/停止、持久终态或正式证据协议；无模型调用、无部署，P7仍未完成。

## 2026-10-07：确认官方结构化机制并提出契约变更

- 核查官方公开扩展协议及固定源码639ed015，进一步只读确认安装版subagent-in-process-driver 0.2.0-rc.2具备structured_output、权威结果后提交、concludeTurn和终态工具门禁；这是结构化工具提交机制，不是账户Messages服务端JSON格式保证。没有启动子Agent、请求模型或增加账户参数。
- 新增p7-structured-submit-proposal.md，明确完整原模型工具提交、原身份/预算/停止、双日志及独立语义GUI/发布验收；交付契约由最终文本JSON改为原工具提交，待用户确认才实施。现有代码、严格解析、失败及未派发任务保持不变。

## 2026-10-07：第五批清理完成与最终输出协议调查

- 第二次持锁人工清理经屏幕共享Window菜单选择原Virtualization连接，再使用VM内TextEdit正常退出菜单；未强杀、未重开文档。独立SSH核对原PID58082已退出，原文件1637字节/SHA未变；manual-cleanup-normal-002回执为MANUAL_CLEANUP_CONFIRMED，Worker99106恢复且复查仍存在。首次失败及误输入介入原样保留，不算自动清理通过。
- 只读检查官方安装版0.2.0-rc.2的asar内实际LLM/DeepSeek/扩展包：请求发往Messages端点，原生构造器未提供response_format/json_schema/json_object；thinking=disabled对应off，output_config目前仅用于非off的effort。通用扩展能合并字段，但没有据此认定服务端支持最终JSON约束，且序列化失败可回落无扩展请求，不能直接用作强制安全门槛。
- 新增协议调查及后续实现门槛；未修改适配器、解析器、模型或P5，未新增真实推理，未派发005剩余任务。旧UNVERIFIED不改判，P7业务及后续阶段仍未完成。

## 2026-10-07：第五批实测与清理异常

- 屏幕共享窗口恢复后，使用原测试账号正常解锁；坐标点击报windowNotFoundAtPosition，改用已绑定滚动区聚焦及输入。独立readiness确认解锁、无TextEdit、P5原配置/源码/空闲状态不变。实时Codex剩余89%，普通可用、原余额62494.0260570000、重置卡仍未用；新的私有quota记录只绑定005 normal。
- 固定07badd8 host/guest，原normal b754ec2d-e4b4-44e4-a028-2886e04fc342、session-47d2e3ef-8d1e-41ee-bb46-57179728f052，Flash/off。25raw：材料1、引用定位2–8、有效草稿9、观察10–12、输入13、新观察14、保存15、观察16、再次保存17、观察18、关窗19–20、一次原生重开21、新窗口确认22、观察23、write/read24–25。旧窗口1028变为1037，原文档1637字节SHA578be8b206e5330bfcd682103ac82d56da59d3147dd17fc2f766cead321765c6。
- 最终消息在JSON前添加英文总结/引导句，严格JSON第1行第1列失败；不剥离文字、不修补原会话，状态UNVERIFIED/VALIDATION_ERROR。本批停止，conflict0580f3bd和dependenciesdc752fc3仍QUEUED/0raw，不替换失败样本。usage输入17734、输出6746、cacheRead188160、cacheWrite0、总212640，费用未知；session SHA9280b3f310823b5b2fd556c406bfd34061b584a129782eb75ff3acfdf1c2ff02。
- 原执行已撤销/关闭、配置恢复、无quarantine，Worker98900恢复。随后持锁人工清理：Dock坐标点击失败，聚焦TextEdit后super+q未退出而输入q；首次独立核对原PID58082仍存在，清理失败，finally恢复Worker98987。随后Escape/BackSpace撤回误输入字符，未保存；再次独立检查原文件1637字节/SHA未变、PID仍在。该人工介入留档，不算自动清理成功；原窗口仍待正常退出，不继续派发任务。
- 私有normal-guest-diagnosis-001.json、offline-failure-001.json及manual-cleanup-normal-001保存原轨迹、严格失败与清理前后检查；未改历史模型证据。后续先完成窗口清理，再研究正式最终输出协议，不能只反复换样本直到碰巧成功。P7完整业务及后续阶段未完成。

## 2026-10-07：第五批固定候选部署与准备

- 6e80682先提交candidate-005方案。host/guest固定07badd89219a79cf5a18543077ec37a8b0bcf563，新的commit命名VM目录安装24个包文件，独立SSH读回每个SHA及manifest摘要完全一致；只解析源码，没有启动guest服务、GUI或模型。原部署保留，私有回执p7-draft-deployment-005/verified.json。
- 按原prepare流程在新隔离p7-handoff-005/18124初始化API（PID98370），冻结源码摘要、原三组input/rubric及部署摘要。normal b754ec2d-e4b4-44e4-a028-2886e04fc342；conflict 0580f3bd-c79a-4d1c-9d4f-2e676974618c；dependencies dc752fc3-804c-48d4-a882-93ea5f381f71。均QUEUED/0raw，未建模型会话、未请求模型，旧四批失败/未派发身份不变。
- 前后readiness均确认P5源码未变、配置恢复、基础队列空闲、资源空闲、无host/guest隔离、Worker96131存在、无TextEdit。12:11:21Z后检回执readiness-a59796918f5c48a89ced619c12ba1843。P5下次仍10月8日04:10Z，不提前授权。
- VM当前锁屏；CUA两次选择ScreenSharing均cgWindowNotFound，inventory能看到应用运行但不能得到可操作窗口。没有盲发按键、用shell模拟GUI或改变锁屏/安全设置。需要恢复可见屏幕共享窗口才能继续解锁与任务派发；届时必须重新核验额度/空闲/源码，不重建此批。当前不代表P7真实验收通过。

## 2026-10-07：第9个工具草稿预检源码入口

- 沿既有draft-preflight设计，P7新增vm_check_draft/raw，HTTP/Harness注册、就绪工具集、官方会话/请求审计白名单统一9项；P6仍拒绝。提示明确输入前预检，使用返回document和同一canonicalJson，拒绝自行修正但不换会话/预算，输入后不能再预检或重复输入。
- 原raw文本65536 UTF-8字节上限不变；为容纳JSON转义后的信封，只有P7 check_draft允许最大512KiB信封，其他操作/P6仍32768。执行端原输入、身份、会话、停止、租约、30raw和拒绝计数不变，没有增加任意路径或系统工具。
- 新增5项真实loopback HTTP测试：合法/坏JSON/恶意参数单次计费，大信封仅限预检，raw超限拒绝，错误凭据零派发、撤销后不派发、30raw上限以及未预检输入拒绝计数。首次5项因fixture名http遮蔽模块而失败，改显式导入HTTPConnection后通过。适配首次10通过/1失败为新增调用后旧计数断言，更新断言并增加停止后draft拒绝验证后11项全通过。
- 新增带拒绝→有效预检的完整组合测试，真实只读子进程串联原Task/模拟Driver、官方模拟会话、图片/请求审计、原绑定及独立草稿核验，17raw/13请求，仅EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING。相关67项、执行层340项、官方安装版适配11项、Node132项通过（2跳过）。没有真实模型调用、VM部署或GUI操作。
- 原失败证据及冻结P5未改；下一步固定候选、核对部署和新鲜额度后真实验收。P7业务、费用对账、GUI及P8仍未完成，源码接通不等于上线或业务成功。

## 2026-10-07：预检绑定GUI输入及保存

- 7190ca0先提交方案。可信session任务在原Task锁内检查末次有效草稿，type_text必须逐字节匹配其document；成功输入后禁止再次输入或重新预检。save要求成功输入、有效草稿和新snapshot，AX正文仅允许沿用既有末尾LF省略规则，不修改模型文本或GUI内容。原观察新鲜度、身份、停止/租约、raw预算继续由原执行链核对。
- 无session旧诊断保持原行为，不冒充新产品验收。预检被输入后调用仍通过原admit计数并拒绝；已有有效缓存清空，不能继续借旧草稿通过。直接方法的GUI前置拒绝不派发Driver，正式HTTP仍需沿原charge_rejection处理。
- 新增6项门槛反例/正例测试，相关92项、执行层340项通过；其中完整原Task加模拟Driver预检—输入—保存—重开—读回17raw链继续通过。部分门槛单测mock父方法，仅证明拦截及状态，不算真实GUI操作。
- 未注册新模型工具、未部署或发模型请求。下一步HTTP/Harness及提示/白名单注册、完整请求审计和固定候选实测仍待完成，P7及后续目标保持未完成。

## 2026-10-07：草稿完整轨迹及证据运输协议

- 按e7f99a0已提交设计继续：原trace允许check_draft，但要求可信session、唯一原参数/结果、原raw序号、最后有效草稿正文一致，且所有预检早于GUI输入。guest重放仅验证协议响应，不能冒充独立语义判据；宿主仍用前一提交的Pydantic门槛独立核验。原官方exchange匹配新增vm_check_draft参数及完整响应。
- guest检查及导出在存在预检时强制读取私有handoff-session-binding.json，核对run/input及原session；宿主只读inspect再次绑定同一文件摘要。tar白名单及解码同时加入该条件必需文件，不带预检的旧证据不要求此文件；运输验证不宣称官方会话或语义通过。
- 部署源码和安装器同时加入handoff_draft.py，现在23个Python模块加许可证，共24文件；构建固定提交读取连安装器为25次。首次相关测试45通过/1失败，原因是旧构建测试仍断言24次；更新固定清单对应断言后通过，没有修改预算或业务门槛。
- 新增11项协议测试，原Task生产审计加模拟Driver完整GUI链：坏JSON拒绝后有效草稿通过，12个逻辑调用/17raw；完整trace、官方exchange、宿主独立草稿门槛、guest证据导出及tar读回均验证。缺失/公开/错误身份记录、改草稿/响应/错误分类/计数/官方参数均拒绝。相关179项、执行层340项通过。
- 未注册HTTP/Harness新工具、未部署VM、未发模型请求，原P5及所有旧失败保持。下一步补GUI输入保存门槛和工具注册，再固定候选实测；完整P7及后续目标仍未完成。

## 2026-10-07：独立草稿双日志与最终报告核验

- e7f99a0先明确方案。新增backend/handoff_draft_evidence.py，不调用guest预检函数作独立判据；使用宿主原Pydantic/事实核验/正文投影重算有效草稿，逐字段比较响应、原raw摘要、规范JSON和正文。原trace要求唯一有序dispatch/参数/结果、原raw计数、原run身份和GUI输入之前完成；官方原参数字符串及完整响应一一核对。
- 宿主也拒绝的旧草稿可保留为失败反馈，但最后一次必须有效；最终严格报告与已通过草稿canonical JSON完全一致，原GUI期望正文逐字节一致。拒绝原因分类未宣称独立重算，仍待guest协议核验。语义/GUI标记继续false。
- 组合入口读取并冻结原trace，有预检时强制读取0600身份记录并运行新门槛，核对下游inspect返回的同份trace摘要。原session工具白名单和guest轨迹尚不接受新工具，不能因此提前获得整个执行验收通过。旧无预检路径保持。
- 新增19项真实Task草稿审计加模拟官方exchange测试，覆盖会话/input/最终报告/正文/摘要/布尔计数/原草稿/孤立重复或迟到记录/伪造官方响应/末次拒绝等；相关133项测试通过，执行层340项通过。未操作VM、未部署或调用模型，P5与历史失败不变。
- 下一步接齐guest轨迹/收集/官方exchange协议以及输入保存门槛，再注册工具并冻结候选实测。P7完整业务、费用对账、GUI验收和P8仍未完成。

## 2026-10-07：草稿可信身份与原Task准入

- 按既有p7-draft-preflight设计推进。后端在provision前绑定预生成session，重复绑定及任何激活尝试后的绑定均拒绝；guest控制通道核对session格式，独占0600文件持久记录run/session/input摘要。旧无session的诊断激活仍可用，但不能进行草稿预检。身份不从模型工具参数取得。
- 新增Task.check_draft方法，尚未注册HTTP/Harness或部署包。仅接受有界raw，原材料摘要绑定、原admit/30raw、租约/停止、snapshot失效及inflight清理全部沿用；保存/重开后、无绑定及额外身份参数拒绝。有效和无效草稿都保留原参数/响应审计，错误不修补；有效缓存不代表GUI或语义通过。
- 相关97项与执行层340项本地测试通过，包括真实loopback控制协议、失败计数、额度上限、撤销、停止在途及重启保留计数。首次新增重启测试错误预期可继续执行，96通过/1失败；核实既有fail-closed恢复策略后改为要求停止且原计数不变，未放宽生产代码。
- 未调用模型、未操作或部署VM、未修改冻结P5和历史失败。独立轨迹重算/官方会话比对、已验证草稿与GUI正文及最终JSON一致性、工具注册和固定候选真实验收仍待完成；P7及后续目标未完成。

## 2026-10-07：无新增依赖的guest草稿核心

- a3e8292先补充技术设计。新增tools/mac_vm/handoff_draft.py纯函数，标准库严格解析JSON、重复键/非有限数/深度/长度防护；独立检查完整schema字段、原run/session/input、CSV事实与任务集、状态/逾期、精确Unicode引用、缺负责人/逾期必报、冲突至少两处来源及重复问题。
- 只把模型原草稿规范序列化并投影既有中文正文，末尾LF/4096字节上限保留，超长拒绝不截断；不推断或补齐分析。返回DRAFT_STRUCTURE_VALID仍明确semanticVerified/guiVerified=false。源材料与身份参数只接受受信任调用者的绑定，当前无HTTP入口，不从模型参数取可信身份。
- 新增39项与host原Pydantic独立门槛交叉测试，覆盖有效规范JSON/正文完全一致、Unicode/组合字符/引号/换行、任务重排、错字段/引用/统计/身份、缺失/重复问题、畸形JSON与超长正文；相关125项全部通过。原第四批官方final离线输入新核心，仍在第1002列报JSON_SYNTAX，不修补失败证据。
- 尚未加入部署包或实际模型工具，未安装依赖/启动模型/操作VM。下一步可信会话绑定、原Task准入审计、独立双日志与最终报告一致性仍需实现，完整P7未通过。

## 2026-10-07：引用工具源码入口与全链白名单

- 继独立轨迹/双日志核验后，仅对明确P7连接开放vm_locate_quote；HTTP交由原HandoffDesktopTask计数，Harness走原会话owner、AbortSignal和停止通道。参数原样传给guest，拒绝计原预算；P6访问同操作仍409，不新增控制接口或任意路径能力。
- P7工具清单、App就绪校验、请求审计和最终session验证同步为8工具；缺工具/多工具/旧7工具候选不能混搭通过。提示解释原文定位、码点、重复位置选择和预算，不提供测试答案；预检核心尚未注册工具，当前不派发新实机。
- 新增3项HTTP测试覆盖合法定位、坏参数单次计数、错误凭据不派发、30raw上限、撤销后不再派发；适配测试覆盖另一会话拒绝、实际参数传输与取消后定位禁止。执行层340项、官方安装版适配11项、Node132通过/2跳过、后端session/verify50项通过。
- 初次适配测试脚本因独立工作树缺.runtime/desktop-build-tools报模块不存在，未执行测试；改用已安装的原构建工具路径，在新私有目录编译并用官方Electron Node执行成功，没有安装依赖或修改App/profile。未部署VM、未调用模型，原失败及冻结队列未变。
- 后续完整草稿预检仍需预算绑定与审计、最终报告一致性及部署后真实验证；本地源码接通不代表可验收交付。

## 2026-10-07：引用辅助双日志独立核验

- 按既有draft-preflight方案，guest轨迹允许locate_quote/helper_arguments后，不信任工具自报结果，独立遍历原材料重算Unicode区间、歧义截断、来源摘要、输入摘要和原raw计数；要求唯一参数记录位于同call_id派发与结果之间、重开之前。孤立、重复、缺失或错误工具参数记录拒绝；所有既有GUI/重开/读回门槛保持。
- 官方exchange匹配加入vm_locate_quote的原参数和完整响应，任何篡改仍拒绝。真实Task生产器配模拟Driver的链路验证为11个逻辑调用/16raw，不作为真实模型或VM通过。新增4项测试覆盖位置、摘要、布尔计数、状态、参数、重复/缺失/孤立记录、官方响应篡改及未知/无匹配/多义情况。
- 执行层337项和相关后端62项通过；首次后端命令误写不存在的test_handoff_deploy.py导致未执行，改用实际test_desktop_deploy.py后完整通过。部署构建器/安装器同时加入handoff_quote.py，候选包现为22个Python模块加许可证，旧实际部署不修改；后续部署须使用新固定提交及配套安装器，不能混搭旧包。
- 当前HTTP/Harness仍未开放新操作，未发真实模型请求、未部署VM。下一步工具白名单/协议与完整草稿预检接入仍需实施；旧四批业务失败继续保留，P7及后续目标未完成。

## 2026-10-07：引用定位执行端准入

- d6e0af1先补充接入方案。guest新增无依赖的handoff_quote精确定位，与host核心对Unicode、组合字符、重复/重叠、找不到及未知来源交叉核对，不访问任意路径或调用GUI。
- HandoffDesktopTask.locate_quote沿原admit计一次raw，先清空旧snapshot，原材料摘要绑定、租约/停止检查、在途登记及finally清理不绕过。失败仍计数；成功将有界原参数与完整响应按同call_id写审计；重开之后拒绝，不编辑已完成文档。停止途中已准入的结果可留存，但下一次调用禁止。
- 执行层333项（新增7项）、相关后端148项通过；覆盖30次上限及重启不清零、租约撤销、失败计数、材料篡改、停止在途及host/guest结果一致。没有真实模型请求、部署或GUI操作。
- 仍未注册HTTP/Harness工具，P5/P6旧通道不变；下一步必须补齐工具白名单/部署包及独立guest轨迹重算、官方双日志响应比对，然后接完整草稿预检，不能提前开放或据此宣称P7完成。

## 2026-10-07：草稿预检纯函数核心

- 0b6e816先提交设计，仍在原P7阶段分支。新增backend/handoff_draft.py：只对受信任调用者给出的原材料和身份检查草稿，不读写文件、不派发模型/VM、不注册工具。模型仍自行分析/选择原文；定位仅计算精确Unicode码点区间，重复和重叠位置有界返回、不替模型挑选、不正规化。
- 草稿严格JSON解析、重复键/非有限数/大小/深度限制，原schema、任务事实/计数/引用/run-session-input绑定和既有正文投影均复用。拒绝不修补，错误只给类别与有界字段位置；成功显式semanticVerified/guiVerified=false。有效草稿的canonical JSON只是序列化，不补字段、改事实或代做分析。
- 首次深层JSON测试因运行器的递归上限不同未触发预期错误（80通过/1失败）；加入显式32层检查后，预检/结果/正文/会话/独立审阅相关143项全部通过。原第四批官方消息离线仍在第1002列报JSON_SYNTAX；其首个引用精确定位为[0,24)，原模型[0,42)错误，未改变任何历史证据。
- 尚未注册或部署模型工具，未新增真实模型请求。必须继续接入原30raw、租约、停止、失败计数、原草稿/响应审计、官方会话与guest轨迹独立绑定，才可新候选实测；不能将本地纯函数当不计预算旁路。语义误判仍需独立审核，P7及后续阶段未完成。

## 2026-10-07：第四批原报告失败，文件写读已推进

- 021e7a7先提交方案；隔离p7-handoff-004/18123冻结host8a2cb14源码（checkout021e7a7仅文档差异）、guestdd8b456的22文件独立SHA，三组原输入/rubric未变。派发前实时普通可用/92%剩余、原余额、重置卡未用；原P5空闲、VM解锁无TextEdit、无隔离、配置恢复、官方空闲检查通过。
- normal fa459897-8daf-4e00-8f94-78e7f79dbb50、session-e5574aaf-4742-4378-acd1-934545c452dc，Flash/off。15/30raw完成正文输入、保存、旧窗口1000关闭、单次原生重开新窗口1008、新观察、write_result/read_result。原trace写读严格相差工具追加的一个LF，正文2582字节且自身有末尾LF。本轮没有003的错误值反复提交。
- 最终仍UNVERIFIED/VALIDATION_ERROR：原官方消息严格JSON解析在第1002列失败；独立对照原材料发现首个引用[0,42)多包含了N2文本，不等于模型所写quote。原消息还把历史进展列conflict，未做成功语义审核。未修补模型输出、未放宽校验、不恢复旧任务；conflict5119c614和dependencies60934982保留QUEUED/0raw，本批停止。
- usage输入12167、输出3441、cacheRead75136、cacheWrite0、合计90744，费用未知。私有normal-guest-diagnosis-001和offline-failure-001保存原身份/轨迹与不修改证据的诊断；原session SHA927c4671405b8f63334990ba2d49d0a8ed2ac45dd333af2a28ba9cd4c64a4296。
- 首次鼠标Quit没有退出，独立检查拒绝清理成功并恢复Worker96107；第二次持锁经Dock键盘Quit，独立确认PID57238退出、原2582字节/SHA69aa556b52151a7a0c660ae20b60fcb1c2eeb57af4d230aa26d4de4bb2ef9059不变。Worker96131恢复；readiness-a897ca52确认VM无TextEdit、无隔离、原配置/P5源码一致、资源空闲。两次人工介入分别保留，不冒充自动清理。
- 下一步处理结构化报告生成和引用准确性；不能继续仅换候选重试来挑选通过样本。P7业务验收、费用对账、GUI验收和P8均未完成。

## 2026-10-07：第三批失败收尾与正文契约澄清

- 固定host4f5c7e4/guestdd8b456、Flash/off，normal6723d020-cd36-4d52-b32a-562fb3bc92d6使用30/30raw后UNVERIFIED。旧窗口986消失、单次原生重开成功并出现994；第14raw起write_result被拒，第23raw读取尚不存在的result报错，后续无成功产物。剩余两例QUEUED/0raw，本批停止，不替换失败样本。
- 原session694f01f1的首个write_result.arguments独立JSON解析成功，value是HandoffResult JSON而非GUI报告正文；不是外层语法错误。原正文还缺少投影要求的末尾LF。尚未独立语义审阅，不宣称内容通过。usage输入25749、输出28701、cacheRead668544、cacheWrite0、合计722994，费用未知。
- 首次人工清理等待超时，finally恢复Worker95476；第二次重新核对原PID56753/出生时间及原文件，持锁经VM Dock Quit正常退出。独立确认PID消失、2044字节及SHA68ef338c050d39fb9a6d439447d809020d66bac3386f5356a80d309e055b5d22不变，Worker95572恢复。两次回执分别保留于私有p7-handoff-003/manual-cleanup-normal-001和002，不冒充自动清理。
- 30ef7ca先提交正文契约方案，再仅澄清通用prompt：输入和write_result传相同正文D，最终消息才为对象R；保留投影末尾LF和传输额外LF，禁止二次转义及重复错误提交。执行器、独立期望、预算不变；本地回归与后续固定新候选实机验收分开记录。
- prompt及desktop-session回归19/19通过；不是模型遵循或语义验收证明。没有新增真实模型请求，也没有恢复失败任务预算。

## 2026-10-07：第三批业务候选准备

- 8ebd8df先提交candidate-003方案，继续同一P7分支；完整三组固定材料、独立rubric、Flash/off、30raw、失败停止批次和全部旧失败保留规则不变。
- 旧normal模型把上周与本周不同状态当冲突，原提示缺少时间范围限定。新增通用规则：可解释的时间推进不是冲突，同期同范围相互排斥才列conflict；信息不足needs_confirmation，CSV不改，计划/完成/有限验收不混同。未嵌入fixture答案、rubric、具体任务人物或失败模型输出。
- 强调最终整条消息可直接解析为单个JSON对象，不修改严格解析器接受额外文本。prompt及官方session相关18项本地测试通过；这只核对提示和会话协议，不证明模型遵循或语义通过。下一步固定提交、隔离新批次并以新鲜额度运行。

## 2026-10-07：无模型独立保存/重开链真实通过

- 001缺enabled修正后，完整执行层326项本地测试通过（含8项诊断测试，不累加）。002使用同一固定dd8b456部署和c825813修正序列、新run p2-8421b39a-e28c-4ceb-83d8-f10737393fd0、owner8423da15-d11f-4477-bf82-649f84427dca，未恢复001或原业务任务，未调用模型。
- 原轨迹15/30raw：输入固定中文诊断正文并保存；原窗口973关闭，第11raw单次reopen_document获原生应答，第12raw确认新窗口981，第13raw新观察，第14/15raw写result和读回。原生发送约0.7秒返回，无UNKNOWN或重发。原权限已获用户授权，但不能由本次成功倒推旧业务失败的唯一根因。
- 原67字节文档SHA a66c5666ce5344bf8d8549133f47476f3ace852a06518ea7bba3571a143c3634，result含结尾换行为68字节。guest撤销/关闭、零在途后，通过原handoff_export独立SSH取回原始tar，本地decode_handoff_bundle核对16份证据；查看state-13.png确有中文两行和原文件标题，与AX、固定期望和读回一致。私有p7-native-diagnostic-live-002保留意图、结果、original-evidence.tar、collected及independent-collection.json。
- 首次人工收尾因屏幕共享noWindowsAvailable主动中止并恢复Worker94447，未宣称退出成功；重新绑定原屏幕共享窗口后，再核对原PID56354/出生1791371223653564及原文档，持锁正常Quit，独立确认进程退出和文件不变。manual-cleanup-001失败和002成功分别保留，Worker94516恢复。readiness-76886851c7ca4738b93fd545bfff1a40确认无TextEdit、无隔离、VM解锁、原profile/P5冻结源码一致且资源空闲。
- 本次仅技术链诊断通过，sessionVerified/semanticVerified仍false、业务状态UNVERIFIED；不冒充自动应用清理或P7总验收。下一步冻结新候选后跑完整三组交接业务及独立语义审核、发布/下载验证；原失败和冻结排队任务不重跑、不替换、不混算通过数。

## 2026-10-07：无模型诊断001真实失败与选择器修正

- 固定dd8b456 guest及2d3764b辅助序列、新run p2-0403d6ab-a7c7-4d5c-ad5e-6eab5d0d402e、owner47c79471-f578-4281-9b7c-dd9362d0b257。持原宿主锁及guest共享锁、原30raw准入；材料读取/启动/窗口清单/观察共4raw后ValueError，无输入、保存、原生重开或模型请求。guest closed/stopped且零在途，Worker94196恢复，完整私有意图/原轨迹留存。
- 原真实AX唯一文本框index1缺enabled字段。新增辅助序列要求显式true，既有Task.ui_element则以缺省true并校验窗口归属；8131d9c先记录方案后，只调整辅助筛选与既有规则一致，不改执行器或把缺值伪造成已观测属性。缺enabled通过、false/null/整数/字符串拒绝新增回归；8项诊断测试通过。
- 原诊断停止不重跑；单独持锁通过VM Dock Quit人工正常退出PID56126，出生身份先核对，独立查询确认退出且原空文档SHA不变。manual-cleanup-001回执及Worker94268恢复留存；不冒充自动清理或重开验收。下一步使用修正提交建立独立诊断，不替换001失败或原业务样本。

## 2026-10-07：固定诊断部署与无模型序列

- 按2deae06方案，重新确认VM解锁、TextEdit为空、P5空闲/源码未变、profile恢复及冻结002两项QUEUED/0raw，使用受审安装器把固定dd8b456部署到新目录，不覆盖6cf376c旧目录。不启动模型、服务或任务，不改原队列。
- 私有p7-native-diagnostic-deployment-001保存部署意图、响应及独立SSH读回：22文件摘要和部署manifest SHA全部匹配，result=DEPLOYMENT_VERIFIED。这证明有限原生错误诊断代码已部署，不证明原生重开成功。
- 新增handoff_diagnostic.exercise可信辅助序列，拒绝旧预算/已停/不确定/在途任务，逐步经原task API执行材料读取、新观察定位唯一文本区、输入、保存、关闭重开、新观察、result写入与读回。只用固定无敏感诊断文本，每步由可信调用者续租，总序列180秒；异常即stop，不重发。调用者仍须持宿主锁并在finally撤销/关闭，不提供模型注册或绕过最终准入。
- 新增6项本地模拟测试覆盖顺序、UNKNOWN不重试、旧任务拒绝、歧义编辑框拒绝、读回不符、期限。序列完成仍标业务UNVERIFIED；下一步绑定新的诊断run、实际运行并独立核验原始证据，不能用测试或部署替代真实验收。

## 2026-10-07：授权后旧窗口人工收尾与诊断准备

- 2deae06先提交独立诊断方案，明确新诊断身份/自有文件、不调用模型、不恢复原UNKNOWN或冻结002剩余两例；原30raw与执行层边界不变。
- 首个清理窗口等待VERIFY超时，finally恢复Worker93628；GUI鼠标Quit后独立查询确认原TextEdit55473仍在，原文件2023字节/SHA未变，因此未记成功。原超时和post-timeout-observation.json保留，未覆盖回执。
- 重新核对空闲队列、调度窗口、原任务终态、PID/出生身份和文档后，第二个人工清理窗口精确停止原Worker并持共享桌面锁。通过VM Dock菜单选中Quit后按Return正常退出，独立查询确认原PID消失且原文档SHA64542a1361d168aed19897162a6e7479bb1a62f7529995b6234647363bfa1bb5不变；未出现保存/丢弃确认，未删除原文件。
- 私有manual-cleanup-normal-002保存前后观察和MANUAL_CLEANUP_CONFIRMED，释放锁并恢复Worker93704；新的readiness-f4d99e73094547489738828c4fd7c5cf确认TextEdit进程为空、VM解锁、原配置和P5源码一致、无隔离、P5任务/资源空闲。下一原计划仍为10月8日12:10北京时间；未启动P5 API/调度器。
- 这是人工介入收尾，不是自动退出/重开通过。原normal仍UNVERIFIED/13raw，另两例QUEUED/0raw，未新增模型请求；原生诊断代码尚未部署，新的独立保存—关闭—重开—读回测试及P7业务验收均待执行。

## 2026-10-07：用户确认后完成VM TextEdit自动化授权

- 用户先批准进入流程。原SSH/mvpagent环境仅调用权限查询askUserIfNeeded=true，绑定TextEdit55473及原出生时间；没有发送odoc或重新执行原任务。独占native-consent-request-intent-001保存请求，原后台进程等待系统回应。
- 通过屏幕共享实际核对弹窗请求者为sshd-keygen-wrapper，目标TextEdit。明确告知用户授权可访问该应用文档/数据并执行操作，不限单个测试文件；收到第二次明确确认后才点击Allow。不是凭自动目标续接或泛化历史授权授予权限。
- 弹窗消失，原进程正常退出，permissionStatus=0/askedUser=true/dispatchCount=0。另一个新的只读进程复用原身份查询askUserIfNeeded=false，再次返回0且零发送；私有native-consent-request-result-001及native-consent-independent-confirmation-001保存实际回执。
- 未改TCC数据库、未提权/全盘访问/关闭安全保护，未改变旧任务UNVERIFIED或原UNKNOWN、预算和模型会话；不以权限获准声称重开实机通过。当前解除的是权限阻碍，后续仍须独立受控验证重开和完整P7业务，原失败与冻结批次保留。

## 2026-10-07：原生事件只读预检发现待授权

- 读取VM失败时段03:34:30–03:34:36的tccd/osascript/TextEdit系统日志，log show返回77/Operation not permitted；原返回私有留存，未sudo、未改日志权限。
- 在原SSH/mvpagent环境做不发送事件的原生构造探针：目标描述符、odoc事件、原文件URL描述符和列表/参数均构造成功，options=19、发送方法存在，dispatchCount=0。没有NSRunningApplication控制、没有调用send或open；只能证明当前桥接构造可行，不能证明发送会成功。
- 随后只读核对原TextEdit55473/出生1791369249450752后，查询AEDeterminePermissionToAutomateTarget，事件aevt/odoc、askUserIfNeeded=false。首次CoreServices自动桥接不能调用，保留phase=permission未确认；按实际C签名显式绑定后返回permissionStatus=-1744，未请求同意、零发送。
- 本机SDK AppleEvents.h明确-1744为errAEEventWouldRequireUserConsent；Apple官方WWDC19/接口文档说明此查询用于预检且只有askUserIfNeeded=true才请求提示。当前原目标需要授权，不能把本次预检倒填成原13raw请求的实际错误码，更不能推断完整根因已证实。
- 私有normal-native-system-log-001、normal-native-build-probe-001、normal-native-permission-probe-001/002分别保存脚本/真实返回；原任务、文档、预算、剩余队列及VM权限未改，没有调用模型。下一步需用户确认新增自动化授权范围，再通过真实系统界面核对实际请求者；不直接编辑TCC数据库、重置权限或放开安全保护。

## 2026-10-07：原生重开有限诊断

- b179796先提交方案。原失败只留RuntimeError、stderr被丢弃；核对本机SDK及Apple官方sendEventWithOptions:timeout:error:，接口允许返回NSError与回复，但不能凭约1.1秒耗时断言超时或权限问题。未重发原UNKNOWN操作。
- 新增NativeRequestError固定消息和白名单phase/code；JXA在原identity/build/send/reply阶段返回严格失败信封，Python另区分spawn/timeout/exit/protocol。错误码只收有界整数或null，拒绝布尔、字符串、额外正文及未知阶段；不输出stderr、外部异常消息、路径或凭据。
- 原handoff UNKNOWN仅对此确切可信异常附加经再次校验的诊断，非法/被改写字段省略且仍记UNKNOWN。原单次发送、1秒等待/3秒进程期限、PID及出生身份、固定文件、30raw、停止与新窗口验收规则不变。
- native17项、handoff组合65项通过；完整tools/mac_vm/tests共318/318通过（包含前述测试，不累加）。新增5项测试覆盖有限信封、数值边界/恶意文本、超时无重试、UNKNOWN/停止不变和诊断篡改不泄漏。测试为模拟原生接口/Driver，不是实机重开通过；git diff --check通过。
- 未部署、未调用模型、未重跑失败或推进冻结002另外两例。原TextEdit55473尚待安全收尾，原实机失败具体系统错误仍未知；下一步在明确独立诊断范围内取得原生阶段/错误码并针对证据修复。P7与后续目标保持未完成。

## 2026-10-07：第二批首例关窗成功、原生重开未确认

- 按dcec92e冻结方案，源码摘要不变；实际就绪检查确认原P5空闲、配置恢复、无隔离、下一期10月8日12:10。屏幕共享开始显示旧画面，聚焦后呈现真实锁屏；使用原专用账号正常解锁，SSH独立确认unlocked=true，不改睡眠或安全设置。
- 新鲜Codex查询普通可用、剩余95%、原积分不变、重置卡未使用；独占私有quota绑定normal原ID。仅经desktop_operator启动92c0c77f-9ed7-4422-b094-5724f40f9195，官方session-8bfdf1da-c2ca-445e-88dd-3d98e0b5848b、Flash/off。未重跑首批任务或给其余两例许可。
- 原VM轨迹：第11raw为新观察绑定的关闭按钮click，第12raw窗口清单已无原窗口946，随后记录handoff_window_closed；第13raw为reopen_document，约1.1秒后UNKNOWN/RuntimeError并停止，未出现重开结果或result读回。说明关窗这一步本次真实生效，但重开副作用未确认，不能盲重发或声称完整闭环通过。原文档2023字节，SHA64542a1361d168aed19897162a6e7479bb1a62f7529995b6234647363bfa1bb5。
- 原会话重开及后续共六次工具返回拒绝，停止后无新增raw；最终输出还含JSON外说明，并把历史推进描述当冲突，不能作为通过报告。当前无需越过执行失败去发布或登记独立语义通过。任务UNVERIFIED/DESKTOP_VERIFICATION_FAILED、零成功产物；input11017/output9332/cacheRead163968/total184317，货币未知。
- 原操作员正常退出，restoreConfirmed=true/quarantined=false、guestRevoked=true/closed=true；原Worker恢复为92689。独立readiness再次核对原profile/P5源码一致、资源空闲、VM解锁，但原TextEdit55473仍在，自动应用清理因缺独立验证跳过，不能称环境全部清理完成。私有window-normal、normal-guest-diagnosis-001.json及readiness回执保存原结果。
- 依冻结规则停止本批推进：conflict和dependencies仍原QUEUED/0raw；不补成功样本、不改原UNKNOWN。下一步先核对原生打开实现及实际错误证据，再设计修复和原应用安全收尾。P7、费用对账、GUI验收和P8仍未完成。

## 2026-10-07：第二批独立候选准备

- dcec92e先冻结新版回归方案：host f7ecdf6与guest 6cf376c为同一固定候选，三例间不改代码，任一失败停止当前批次推进；旧三例UNVERIFIED不重跑/替换，报告需同时保留两批全部尝试。
- 核对两个提交间tools/mac_vm零差异；通过原SSH重新读回已安装guest的22个文件和部署清单SHA，全部匹配。未重复部署、未修改VM/锁屏设置。host当前checkout仅比f7ecdf6多方案文档，执行源码SHA单独冻结。
- 私有p7-handoff-002独立初始化数据库与18121 API（PID92131），实际通过/handoff-tasks提交normal92c0c77f-9ed7-4422-b094-5724f40f9195、conflict3f1c614e-6c0f-4b68-82de-4b43937dece4、dependencies51826967-bb01-45ca-b3f5-53aaf594c5b4；输入和独立rubric SHA与原冻结组一致。cohort/submit-intent/response保留，三例只排队、0模型请求，不能算验收通过。
- 本次实时Codex普通可用、剩余95%、原积分62494.0260570000未变、重置卡未使用；此读数只描述准备时状态，未生成未来许可，执行前重新查询。准备时VM锁屏，原P5 Worker91582持续在、配置与冻结源码一致。
- 原18120 API只服务首批3个UNVERIFIED任务，已按原PID86754/完整命令核对后正常停止，数据库及全部证据保留；未结束其他服务。新18121 API承担候选队列，未启动模型Worker。下一步正常解锁VM、核对新鲜门禁后执行新版normal，不复用首批任务/会话/预算。

## 2026-10-07：运行态观察与终态证据分离

- 原会话seq44 vm_reopen后seq45为interrupted-tool-result/TOOL_OUTCOME_UNKNOWN，seq47 interrupted。核对固定官方参考源码repair.ts：此类合成结果及turn/end复用最后真实事件时间；不能从三条相同时间戳推断中断发生时刻或确定是关窗失败。原首次Worker异常未留存，根因仍未知。
- 2d8909f先提交方案。官方持久化使用追加拼接zstd帧，原inspect即使running=true仍读日志，可能因追加未完成/长度变化抛异常。用真实压缩数据拼部分尾帧验证严格reader拒绝，新增live测试在旧实现确实失败；未运行模型或改变原证据。
- inspectDesktopSession严格核对清单数组、唯一session/cwd及布尔running；live时不读取持久化文件，返回evidencePending=true和null计数、terminal=false。Python只接受精确非终态形状；guest预算/在途和原心跳/期限不变。idle后依旧完整读取原日志、提示绑定、终态分类和字节一致归档，坏尾帧/伪造pending成功拒绝。
- 测试覆盖真实zstd半帧、live不读文件、idle坏帧拒绝、修复完整文件后原字节归档、错cwd/重复身份/非布尔及pending假终态。首轮3项旧测试仍要求live promptObserved=true，按新“未读证据”契约改为pending断言，取消及原终态核验仍保留。最终Node27/27、后端session/handoff/worker/adapter/reconcile共84/84通过，git diff --check通过。
- 新代码对原第三例实际只读inspect确认exists=true/running=false/terminal=true/userMessages=1/promptObserved=true/interrupted，未新增请求。不是原失败根因的确定证明，尚未新版实机验收，原三例失败完整保留；下一步冻结新版独立验证批次并保留全部历史结果。

## 2026-10-07：隔离记录留档与原Worker恢复

- 55ff246先提交对账/恢复方案。原scheduler入口revoke实际返回REVOKED；未授予未来许可、未补跑P5漏期。第一次设计提交命令误在冻结P5目录执行，因目标文件不存在未产生提交/改动；随后在P7工作树正确提交，P5源码摘要仍一致。
- 持原宿主共享锁，实际复查原Task为UNVERIFIED/9raw/原owner/epoch、两服务资源和队列空、原P5源码与profile摘要一致、全部官方会话idle且预置等于原恢复回执。独立SSH确认guest共享锁可取得、无guest隔离、TextEdit与原guest无进程、52385/8766无监听、文档原SHA一致；宿主原SSH已退出、19099可重新bind。
- 私有quarantine-resolution-intent绑定收尾/恢复/监听回执摘要。原活动quarantine以无覆盖硬链接留在原run/resolved-quarantine.json，核对inode/字节后移除活动路径，保留quarantine-resolution-receipt；不是删除失败历史或宣称中断根因已修复。
- 独占Worker恢复意图，按原仓库、原环境启动单个backend.worker，PID91582；实际确认进程持续存活并占原共享锁、队列仍空，私有window-dependencies/worker-recovery-confirmed.json保存。未新增任务或模型请求，原三例失败不变。P5 API/调度器未启动；下一步继续P7中断原因及新版完整业务验证，非P7通过。

## 2026-10-07：原第三例监听与应用残留收尾

- 96e1c3c先补监听/隧道收尾方案。既有control/lifecycle客户端24项测试通过；本次不修改模型工具或执行预算。
- 持原共享锁，重验恢复profile SHA、原失败状态、官方会话terminal、原guest绑定/停止/零在途/9raw后，独占记录listener-cleanup-intent，单次既有shutdown确认closed=true，独立SSH核对原guest退出、52385/8766无监听。原SSH88856按完整命令、原转发端口和启动时间核对后正常TERM退出，无强杀。
- 首轮末尾19099重新bind报EADDRINUSE，保留原意图和shutdown响应，没有重发shutdown/TERM。随后只读lsof/ps/netstat未见原监听/进程，再次本地bind确认端口已释放；没有当时TCP状态证明，不能确定归因为TIME_WAIT。新的listener-cleanup-reconciled.json记录此介入与结果。
- 屏幕共享最初呈现旧桌面，唤醒后实际是锁屏；使用原专用账号正常解锁，不改睡眠/安全设置。原TextEdit54663归属owned-application原run/owner/epoch；持锁通过Dock Quit正常退出，无丢弃提示。独立SSH确认TextEdit无进程、文档2642字节与SHA6410950dd01514b1dab06b6f6a2c3e0927d5275b71fd82a33a2ee85f62f34ed3前后一致，私有dependencies-manual-cleanup-001.json保留。此为人工操作，不能计自动清理或关窗重开业务通过。
- 未新建/重跑模型任务，原9raw/UNVERIFIED不变，quarantine保留，旧Worker未启动；下一步对账解除隔离和原Worker恢复条件，P7仍未验收。

## 2026-10-07：原第三例配置恢复

- 4489fba先提交独立恢复方案；新增restore_interrupted_profile，持原共享锁核对quarantine/收尾意图及全部输入SHA、原任务和唯一已结束Attempt、资源空闲、原会话terminal、guest停止/零在途/预算不变。独占恢复意图后复用既有App/profile三步命令，未知结果不重发，失败仅留脱敏阶段。
- 本地新增12项恢复测试，连同收尾/Worker/handoff adapter共53/53通过；Node App/profile19通过、2项可选编译器测试跳过。测试不代表真实业务成功。
- 实际执行原58ff6b1a-fb90-482a-83e7-1f4b60c78bc3恢复：stop-restore、profile restore、start-restore全部确认，独立读回原profile SHA，guest仍停止/9raw/零在途，原隔离字节不变。私有desktop-recovery-intent/receipt及dependencies-profile-restored-001.json保留，不修改原失败/outcome。
- 恢复前所有十个隔离队列及原P5队列空闲、原P5冻结源码未变、无旧Worker；VM已解锁，仍有TextEdit54663。未新建/重跑模型任务，不清隔离、不启动Worker、不强制关闭文档；guest监听/隧道和应用残留仍须后续收尾，不能称环境或P7全部完成。
- 恢复后10:06:24 UTC独立就绪检查确认profileRestored=true、全部队列空、源码未变；VM已重新自动锁屏，TextEdit54663仍在。此检查不触发模型，不改锁屏设置。

## 2026-10-07：原第三例安全失败收尾

最终相关回归：desktop_reconcile、desktop_worker、handoff_adapter共41/41通过；不把模拟数据库测试计作实机业务成功。

- 61c7d02先提交方案。新增desktop_reconcile.finalize_interrupted，只读原会话/guest状态，持原共享flock，重验私有控制和回执、原Task/owner/epoch/run/session/唯一未结束Attempt、过期Resource、单调预算、无产物。独占意图后仅事务登记UNVERIFIED与实际usage、未读通知、Attempt结束和旧Resource释放；不续期、不创建新任务/Attempt、不运行模型、不恢复配置、不移除quarantine。未知提交不重放。
- 隔离数据库12项测试通过：成功仅失败收尾，隔离原字节不变、epoch/Attempt不变；运行会话、在途工具、未停止、预算超限/倒退、错owner/epoch、有效租约、未停止本地控制、既有意图、成功产物均拒绝。原Worker与adapter组合回归另行执行，git diff --check通过。
- 通过新入口实际重新查询原session-24f8909d-58e3-48ca-95b6-1ce8a1f50c75与原guest，原task58ff6b1a-fb90-482a-83e7-1f4b60c78bc3于09:57:33 UTC结束为UNVERIFIED/DESKTOP_INTERRUPTED_RECONCILED，预算9/30、零产物。真实usage input10516/output8310/cacheRead64768/total83594、Flash/off、货币未知；原会话SHA48ba8cda01217b1505a5e9671c7b47f1e51a86d50455a8446df75f1eeb280f6f。
- 私有desktop-reconcile-intent.json与dependencies-reconciled-001.json保存原证据绑定和结果，不覆盖原BLOCKED/outcome/中断会话。配置未恢复、quarantine保留、原P5 Worker未恢复；三例均未达到业务成功，不能当P7通过。下一步按原空闲会话、已停止执行端和冻结profile核对配置恢复与监听收尾，再单独处理隔离保留记录。

## 2026-10-07：第三例隔离与只读对账

诊断改动验证：test_desktop_worker与test_handoff_adapter最终29/29通过，git diff --check通过；仅隔离数据库和模拟adapter测试，不部署、不恢复原失败、不发送新模型请求。下一步实现并验证原隔离任务的证据绑定安全收尾，先结束原状态再恢复配置，不通过删除quarantine或修改数据库伪造完成。

- 正常解锁原VM并经TextEdit Quit菜单清理conflict残留54127，原文档SHA前后均3eba7996664b53bb6ed29de6c7a08a311d1253bff6e95b7ac5977de2a1a1f3f9；独立确认进程退出，无丢弃提示。此为人工清理，不计自动通过。6cf376c部署到新目录，22文件和清单独立读回一致，回执p7-deployment-20261007-003；只冻结剩余原dependencies身份为v3。
- 新鲜实际额度97%、普通可用、原余额未变、重置卡未用，通过原门禁启动task58ff6b1a-fb90-482a-83e7-1f4b60c78bc3/session-24f8909d-58e3-48ca-95b6-1ce8a1f50c75。第9raw为新click，原trace中1791366483.901847派发，6484.480065开始stop时点击仍在途，6485.912222返回accessibility/unverifiable；随后零在途，无list_windows或重开。不能将中断解释为新按钮没有关闭，也不能算关窗验证通过。
- operator88845终止，outcome BLOCKED/quarantined/restoreConfirmed=false，取消只有意图无确认回执，usage原为未知。原P5 Worker88141未重启，隔离文件保留；数据库最后状态RUNNING/9raw。后续只读inspect实际确认原会话running=false/terminal=true/interrupted/原用户消息1条，并按既有采集逻辑保存原session.jsonl；原guest/status为active=true、stopped=true、9raw、pendingCalls=0，active仅指监听线程仍在，不表示仍有业务派发。私有dependencies-review-001.json记录对账。
- 原Worker吞掉首次异常细节，暂不能在读取会话、控制通信、心跳失权等原因中作确定判断。aafe95d先写方案后新增outcome异常阶段与固定大类、started/terminalObserved/authorityLost和独立心跳诊断；不记录异常字符串/外部类名/堆栈，不改变隔离、取消、重试和恢复逻辑。原失败不补造原因。合成凭据异常测试确认私有输出不泄漏；首次新增测试因插入位置误带成功断言失败，修正测试归属后重验。

## 2026-10-07：新鲜观察绑定的关窗修复

- 90e44fc先提交技术方案。HandoffDesktopTask用保存后原观察的唯一左上角AXButton/index/token生成受限click，排除原最小化与缩放控件；截图无效、sheet/dialog、过期、禁用、歧义、非有限几何和错token拒绝。模型工具不增加，click仅在内部closing阶段且参数完全等于绑定目标时准入；finally清除目标，不留通用点击能力。
- 独占重开意图增加按钮index/token；handoff_trace要求原观察一致且唯一click、原窗口消失再固定文件重开，handoff_evidence严格核对更新后的意图字段。旧Command-W轨迹不自动升级通过；内部原30raw/预留11次不变，未增加重试或丢弃对话框处理。
- 首轮312项回归出现4失败/5错误：文件核验仍用旧意图字段、模拟AX列表插入按钮影响原正文位置、dialog反例漏索引。修正生产意图合同和模拟数据后312通过；补充意图index/token、几何和旧hotkey篡改后，最终执行层313/313通过。后端test_handoff_bundle、test_handoff_adapter、test_desktop_deploy合计34/34通过，git diff --check通过。
- 经原SSH只读取得真实conflict的state-08.json，离线新规则准确选中s0000008f:6（原窗口左上角），不执行点击、不修改原文件。该核对只证明旧观察可定位，不能证明实际关窗有效或Driver失败根因已解决。未部署、未派发模型、未改两原失败/第三例队列；下一步冻结新部署并按原门禁验证。

## 2026-10-07：P7修复版第二例与关闭失败核对

- 固定deebd8d的新guest目录独立读回22项文件摘要与部署清单一致，原部署保留。剩余原任务身份绑定在私有cohort-remaining-v2.json/execution-v2.json；首例旧版失败不变，不拼成同版三例通过。
- 首例残留TextEdit53742经人工GUI清理：远程退出快捷键实际误输入q，随后通过Edit→Undo Typing撤销、TextEdit→Quit正常退出，无丢弃提示；独立SSH确认进程消失、原文件当前0字节。私有normal-manual-cleanup.json保留介入，原4raw/UNVERIFIED不变，不算自动清理通过。
- 为原conflict任务9c4d50e1-50f2-469a-be90-572d4aab8677重新核对真实普通额度98%、原余额不变、重置卡未用，经原门禁/共享锁执行。官方session-a565880d-b1dc-441f-9366-efaa399c8ff0、Flash/off；输入8533、输出9603、cacheRead116480、total134616，货币费用未知。
- 原轨迹显示材料读取、首次观察、输入及保存后的观察已经完成。重开意图绑定原文档SHA；第9raw为Command-W，第10–12raw均返回同PID54127、同窗口884、原标题且is_on_screen=true。没有handoff_window_closed或reopen_document派发；随后stop，四次后续工具拒绝，没有新增raw。官方轮次completed不代表业务通过，数据库UNVERIFIED/DESKTOP_VERIFICATION_FAILED、无产物。
- 只读核对安装版Driver的describe hotkey，cmd/w及foreground参数合法；其说明明确effect=unverifiable，需另行核实实际效果。因此不能断言参数拼错，亦未证明是焦点恢复、延迟或窗口拦截。新屏幕截图仍见原报告窗口，没有以手动关窗补造任务成功。
- 原许可已撤销、guest关闭、无quarantine、profile恢复；Worker从87084恢复为88141。应用自动清理因NO_INDEPENDENT_VERIFICATION跳过，TextEdit54127仍在。新的私有readiness-64da95f3fa844b12845e0af107d45b6d回执确认VM解锁、P5无活动任务/共享锁空闲、六个冻结源码摘要未变，P5下一期10月8日12:10。仅dependencies原任务58ff6b1a-fb90-482a-83e7-1f4b60c78bc3仍QUEUED/0raw。
- 本次追加检查未派发模型或GUI动作，未修改执行代码、原失败、预算或验收条件。先定位关闭动作，再设计受限修复及反例测试；不能仅加重试、延长等待或手动关窗后继续原失败任务。P7仍未验收。

P7缺值观察修复（2026-10-07）：61e9ad2方案先行。JS handoffObservation与Python project_handoff_observation仅在value字段不存在时省略value、明确bodyValueStatus=unavailable；现有字符串/空串原样，null/数字/布尔/数组/对象（JS还含显式undefined）继续拒绝。原唯一正文/token/祖先/截图/弹窗/大小检查不变，未读取文件猜正文、未改变预算/执行权限/保存/重开/成功核验。新增缺失与真实空串区分、原state不变、错误类型拒绝，并确认无原生正文证据时body_from_state仍拒绝。

实际验证：Python执行层unittest discover 310/310；官方安装版Electron Node执行esbuild编译的c0-vm-tools.test.ts，11/11；追加验收拒绝断言后投影专项4/4。通过原SSH只读取得首例state-04.json，在新私有目录保存，JS与独立Python投影完全一致且未生成value；二次远端读取字节相同，回执.runtime/p7-missing-body-check-4a9a21ad8b184ab183a31294099a0dae/receipt.json。没有新模型请求、没有修改VM部署/原失败/队列，不能将离线兼容证明算作实机业务通过。接下来核对首例残留应用与部署新固定版本，原两排队样本继续保留身份；全阶段仍未验收。

P7正式首例失败（2026-10-07）：先沿冻结P5原scheduler.prepare将10月6/7两期记录MISSED，下一期10月8日12:10，未补跑/授予许可；finally revoke返回REVOKED。新的week_observer回执仍INCOMPLETE/ConnectError，原API不可用不掩盖。10月4日至7日共四期缺失，不能宣称一周通过。

独立P7服务初始化前18107实际占用，预检在创建目录/库/任务前退出；保留旧监听，改18120并保存准备失败历史。新独立数据库/profile接收normal/conflict/dependencies三组冻结输入，rubric未发送模型；原任务分别d1725fc1-94b1-4263-a607-4042a66335a0、9c4d50e1-50f2-469a-be90-572d4aab8677、58ff6b1a-fb90-482a-83e7-1f4b60c78bc3，禁止换身份补成绩。私有总清单.runtime/p7-handoff-001/cohort.json，guest固定288aba5，host7b70df5仅文档差异。

本次重新查询普通额度剩余99%、余额不变、重置卡未用，为normal保存私有五分钟任务绑定记录，原门禁/共享锁准入。确认P5空闲及未来30分钟无到期、官方App无运行会话后，正常停止原Worker30244。单任务操作员实际创建官方session-bfb29383-fff7-4833-be21-1e41070954d7，Flash/off；读取材料后第一次vm_observe失败：handoffObservation要求body.value为字符串，原VM state-04.json的唯一AXTextArea（First Text View）根本没有value字段。未把不可用值猜为空字符串，未绕过校验。官方轮次error，4raw，input3160/output6141/cacheRead2560/total11861，现金费用未知。任务UNVERIFIED/DESKTOP_VERIFICATION_FAILED，零成功产物；不是HANDOFF_SEMANTIC_REVIEW_REQUIRED。

原执行撤销/关闭已确认、profile恢复且无quarantine，P5 Worker恢复为87084；未验应用按既有规则可能残留，下一例不得未经核对继续。conflict/dependencies保持QUEUED，不派发同类已知故障。下一步先写缺值观察表达的窄范围方案，再同步JS投影与Python独立核验并覆盖反例；不得将缺失、null或错误类型自动当空正文，更不能回填原失败为成功。当前P7未通过，原证据及两次私有准备/输入故障保留。

P7实际VM部署（2026-10-07）：查到原私有real-app-unlock.py使用已有专用凭据；未重跑旧一次性脚本，改经原Screen Sharing连接登录。首次批量/快速键入未解锁，后逐键输入并核对界面、点击登录箭头成功；新桌面截图及独立SSH均确认mvpagent已解锁。不改密码、锁屏策略、共享权限或VM进程。此前直接要求用户接手的判断不充分，当前锁屏阻塞已解除。

本次实际Codex检查剩余99%、普通额度可用、余额基准未变、重置卡未用。运行私有p7-deploy-20261007.py：先核对原P5及九个隔离队列为空、资源空闲、profile恢复、冻结源码不变、无quarantine，再从固定提交288aba5be82b50ddf73062cfb49862817ead4111构建包，通过既有受限SSH/安装器写入全新VM目录。另一次只读SSH对22个文件及清单逐一重算SHA，与host包完全一致，DEPLOYMENT_VERIFIED；回执在.runtime/p7-deployment-20261007-001/verified.json，凭据和原始证据不提交。

未启动P7服务/任务/模型、未停止原P5 Worker、未覆盖旧部署。P5计划nextAt仍为10月6日12:10，已过期记录须沿原调度器保留MISSED、不补跑，然后才能按原切换门禁执行P7。三组真实GUI/语义/下载/清理验收均待，不标阶段或总目标完成。

P7候选部署完整性补验（2026-10-05）：再次只读确认宿主仍锁屏。在不操作VM的前提下，以固定提交2bbc34f4e27d4ba39a7c377da66d095bbd09521d构建22文件/234567字节部署包，调用实际install_package在新私有目录校验/安装；安装清单SHA与build_package一致。随后Python -I -B隔离子进程仅加入该安装目录，21个部署模块全部import成功，退出0/无stderr，证明本候选没有靠工作区补齐部署依赖。原包、安装器、清单、回执均留.runtime，不上传。未调用模型、未部署VM、未重启或停止服务；真实P7三组验收仍须桌面解锁后继续，不将导入通过冒充GUI成功。

P7真实环境预检（2026-10-05 15:54，北京时间）：本轮实际账户检查普通额度可用/剩余65%，积分保持62494.0260570000、重置卡未使用，没有签发执行许可。只读数据库核对原P5及九个旧隔离队列均无在途/排队任务、原资源空闲；正式计划ACTIVE且下一期10月6日12:10，六个冻结源码摘要不变，官方profile与最近恢复基线逐字节一致，host/guest无quarantine。原Worker 30244仍运行。

通过既有受限SSH确认mvpagent/VirtualMac2,1、VM锁屏且没有TextEdit进程；宿主ioreg也报告锁屏，cua读取Screen Sharing返回cgWindowNotFound，不能观察到可操作窗口。本次零模型请求、未创建P7任务、未停原Worker、未修改VM/SSH/睡眠或解锁策略；私有readiness/operator-check回执保留。真实验收暂受桌面可用性阻碍，需恢复可操作桌面后重新预检，不能复用本次额度放行或宣称三组通过。P7及总体目标仍未完成。

P7自有应用清理（2026-10-05）：e7305e3设计先行。adapter完整原会话/guest/图片/请求核验并保存私有回执后，为原restore提供document/result/trace三摘要，但仍抛语义审阅必需、保持UNVERIFIED，不生成成功产物。guest cleanup按实际HandoffDesktopTask选择独立P7核验，重新核对原材料SHA/预置绑定、保存/重开/读回轨迹及预算，再复用ApplicationCleanup原PID/启动时间/可执行文件、零在途/无UNKNOWN/撤销许可、单次正常退出/观察。失败不回退P6、不强制终止、不删除证据，原告警和隔离流程保留。

新清理测试使用真实P7执行器生成的模拟Driver证据及模拟native退出；原文件/预算不变、单次退出、改材料/结果、PID复用、在途/UNKNOWN、host摘要不符均覆盖。首轮fixture owner使用旧worker标签，被生产UUID门禁拒绝；修正测试生成原UUID身份，不放宽生产校验。尚未真实VM退出/部署，三组真实业务/语义审阅未完成，P7仍未完成。

新增清理7项通过，完整guest执行层309/309，handoff全组及旧adapter/worker/deploy组合433/433通过；后端仅已有httpx TestClient弃用警告。README和使用说明同步；旧P5服务/源码未动，未调用实际模型或VM。

P7可信发布CLI（2026-10-05）：cfccb49设计先行。新增backend.handoff_publish_operator，publish/inspect只接受canonical task UUID、私有隔离service profile及publish必需的审阅原字节SHA，复用原profile隔离门禁，不能传任意DB URL/成功JSON。publish只调用已验证的原任务事务，不执行模型/VM；inspect锁定读取原Task及唯一发布事件/Artifact元数据、原意图是否存在，不读为已读通知、不重验文件字节、不授予重试。DB已登记与仅有文件意图分别展示；所有异常输出固定脱敏摘要，提交不明不假称回滚、不自动再发。

新增CLI边界10项，含真实子进程拒绝及错误脱敏，隔离DB补成功前后/事务失败后inspect断言，发布组合45/45通过；唯一警告为已有httpx TestClient弃用。成功路由用mock验证且DB另测，不冒充生产CLI已发布真实业务。未部署、未调用模型/VM、未改变原P5服务；README/命令说明同步。下一步完成P7自有应用清理，再进行真实三组任务及实际独立审阅，P7未完成。

P7显式生产路由（2026-10-05）：a1373b2设计先行。Settings新增默认关闭handoff_tasks_enabled；/handoff-tasks仅接严格HandoffSubmission及幂等键，旧/tasks和/desktop-tasks不接P7。TaskService提交按kind规范校验，claim精确选择日报/P6/P7；三类共用原Resource锁、epoch和停止预算规则。DesktopWorker新增受限kind选择，不另写执行循环；desktop_service serve及desktop_operator worker-once新增显式--kind project-handoff，默认P6，独立服务仅允许选定kind创建与原stop。操作员选HandoffTaskAdapter，仍核验原QUEUED/未尝试身份、quota、切换批准、基线/VM就绪及共享锁，launch意图记录kind，不自动恢复或重试。

隔离联测首次453通过/1失败：新增P7操作员测试暴露desktop_authority仍仅允许P6，导致P7在启动前BLOCKED；修正为P6/P7同样受原任务/owner/epoch/租约/停止约束。保留该失败记录，不降低门禁或将其当模型失败。此次未修改冻结P5源码/服务，未执行真实模型/VM；正式三组业务、P7退出应用清理及可信发布CLI仍待。

修正后新增路由10/10通过，handoff全组加旧queue/operator/service/worker/artifacts组合454/454通过；覆盖三kind共享锁、默认关闭/专用API幂等/类型拒绝、隔离服务POST白名单、实际操作员选择P7适配器并保留UNVERIFIED/恢复、错kind目标不claim、原任务禁止重试。两个CLI帮助实际执行显示新参数；这不代表服务已部署。README/使用说明同步，仅已有httpx TestClient弃用警告。

P7原任务发布事务（2026-10-05）：9e48637设计先行。publish_reviewed_task只接受可信TaskService/原taskID/审阅SHA；锁desktop Resource再锁原Task，拒绝活动资源、非UNVERIFIED/非P7、越界run、未关闭Attempt、原失败事件缺失、已有Artifact、控制未停止、输入/session/owner/epoch/预算不一致。锁内重跑发布前证据核验，独占保存发布意图及三份原字节/报告，原控制二次读回后单事务登记Artifact/唯一handoff_published事件/finished通知。旧失败事件和通知保留且未读，session/预算/usage不改，不创建新Attempt。

下载白名单增加P7三份产物，但普通TaskService.finish明确拒绝P7成功，避免直接调用绕过审阅。文件/DB失败保留原意图和已写文件，DB回滚，无成功下载；同记录不重放。验证使用隔离PostgreSQL和模拟Driver/审阅；真实VM、生产入口/任务路由及正式三组验收未执行，P7仍未完成。

新增16项隔离DB测试通过，覆盖原失败/通知保留、三份实际HTTP下载与权限/未成功/篡改拒绝、11种身份状态反例、文件失败/DB回滚、并发两发布者唯一成功、普通finish旁路拒绝；相关后端461/461，另Worker/adapter/下载/发布组合72/72通过（重叠测试不累加）。唯一警告为已有Starlette TestClient/httpx弃用提示；无真实模型调用、未改冻结P5运行源码或服务。

P7发布前证据准备（2026-10-05）：18807a0先提交设计。新增handoff_publication.prepare_publication，限定原run/handoff-reviews/<原记录SHA>，核对私有普通单链接文件、记录原字节摘要、意图时间/当前OS uid/声明身份、完整回执；重新执行原会话/guest/图片/请求组合验收与独立审阅合同，要求原执行摘要一致且审阅全部通过。精确读回原guest文档和result，对照独立正文，返回这两份原字节与原报告规范JSON及SHA；返回前重读所用发布输入不变。不写产物、不改DB、不调用模型或VM，不把身份标签称为外部认证。

新增19项模拟证据测试覆盖只读成功、篡改uid/绑定/回执/意图/审阅/guest/session/context、额外字段/链接、负面审阅、路径参数和核验期间回执变化。首轮两项测试失败：模拟提取文件未模拟生产0600权限，以及guest失败抛RuntimeError；修正fixture权限和预期拒绝类型后19/19通过，相关后端回归434/434通过。不是实际语义验收；原任务事务式成功登记/通知/下载、生产路由、三组真实样本仍待，P7未完成。

P7可信本地审阅入口（2026-10-05）：d241d3c设计先行。adapter完整组合核验后限定原root/guest/run目录，保存私有原submission/session/binding/home上下文及执行回执。handoff_operator仅本地CLI、无HTTP/模型注册；校验当前OS用户私有规范文件、普通单链接、有界读取与文件身份稳定，reviewer类型/标签由调用者显式给定并匹配原record，回执声明authenticatedReviewerLabel=false，不能声称标签已通过外部身份认证。

读取原review后按其原字节SHA独占建审阅目录，保存原record与当前OS uid/来源意图；随后重跑原session/guest文件/图片/工具/请求组合核验，要求与既有执行回执一致，再校验逐项语义声明，返回前重读context/执行回执/review。接受、明确未通过和合同/证据拒绝均持久留回执，写入失败保留原意图，重复同记录不自动重试。无DB修改/产物发布/VM或模型动作；同机受信任用户边界及下一步发布前重验要求写入backend/README，模型七工具无host审阅写权限。

新增13项测试含真实本地CLI子进程、完整执行组合重核验、PASS声明/FAIL/UNVERIFIED保留、错reviewer/原文件/会话/执行回执/context/缺失/链接拒绝、私有权限/hardlink拒绝、保存失败与不重放；使用三组中normal的模拟Driver/合成报告/合成独立审阅，不冒充实际语义或视觉检查。相关后端415/415通过，README与使用说明同步。成功DB/下载/真实样本仍待，adapter门禁未放开，P7未完成。

P7独立语义审阅记录合同（2026-10-05）：7919772先写方案。handoff_review重新校验冻结case输入/报告事实、原执行报告/会话/正文SHA及图片集合，构建原任务每个progress/handoff、每项issue、每条rubric要求与三项全局检查的精确审阅清单。审阅记录绑定case/run/session/input/report/session/document/rubric/整个execution摘要，human或codex身份声明、非未来带时区时间、全部原snapshot，以及每项PASS/FAIL/UNVERIFIED和非空理由。非全局PASS须有原报告文字精确码点摘录，限制引用当前字段或对应任务/问题；拒绝缺项/重复、额外字段、空理由、错误引用/类型/错图/改报告/改执行证据。已声明冲突任务集合还须与冻结rubric一致，不能靠全PASS覆盖此确定性差异。

返回REVIEW_ACCEPTED或REVIEW_NOT_PASSED并保留各判定、外部审阅身份/摘要、automaticSemanticProof=false及userAdoption=NOT_ASSESSED。纯函数不认证操作者，不证明摘录支持结论、不发产物/改DB/解除adapter门禁；模型生成同形JSON无发布权，后续可信操作员入口必须认证来源、私有保存并重验执行。当前只覆盖三组固定验收样本的审阅合同，不声称任意用户输入都已解决语义验证。

新增29项合成记录测试通过，含明确失败/不确定保留、九绑定篡改、逐项漏审/伪造/时区未来时间/受测模型身份拒绝及冲突集合反例；这些测试不是实际人或Codex完成了原业务审阅。无真实模型/VM调用；README同步，真实三样本、操作员审阅入口、成功下载和生产API仍待，P7未完成。

P7正式业务材料/独立语义标准冻结（2026-10-05）：051f77b设计先行。新增backend/fixtures/handoff-v1下normal/conflict/dependencies及manifest，三组3/3/4项任务、2/3/3份笔记、各有CSV与上周报告，全部为虚构测试项目。普通组区分历史推进与当前冲突、有限测试与全场景覆盖；冲突组同刻完成/联调矛盾、待批准延期、未知负责人并含不具权限的恶意便签；依赖组区分沙箱/生产、预计映射/上线承诺、同人多任务、已完成/当天截止不逾期及待指派负责人。每项有必须表达/禁止编造的要求与精确来源摘录，无预制完整报告正文。

handoff_acceptance只读取三个固定case，重验输入合同/状态计数/逾期/未知负责人、逐任务覆盖、唯一要求ID、准确唯一摘录及跨来源冲突证据，返回来源码点位置和SHA；固定manifest分别绑定文件原字节、规范输入及rubric摘要，变更拒绝。返回ACCEPTANCE_FIXTURE_CONSISTENT且semanticVerified/realExecutionVerified=false，不能把原文存在当报告含义正确。rubric只供外部独立审阅；提交只接受input，整个wrapper被合同拒绝，不经模型工具传出审阅期望。

新增20项本地测试通过，覆盖三组冻结内容/数字边界/源摘录、缺项/伪造引用/布尔冒充计数/缺冲突来源/标准篡改和路径逃逸；无模型/GUI调用，没有执行正式样本或改变旧结果。下一步逐条记录实际输出的独立语义判定并接成功准入、受控API和三组真实VM业务验收；P7尚未完成，README同步。

P7任务适配器/官方App启动接线（2026-10-05）：be9f1a0、fbe8d26先定义方案。P6 adapter提取内部固定合同/会话/控制client/profile/app/连接/预置方法，默认行为不变；HandoffTaskAdapter选择P7输入、官方会话客户端和材料控制客户端。prepare沿原guest bootstrap/端口选择/准备失败收尾，冻结stage=p7/case=project_handoff/inputSHA连接；start重新gate，在切换App前单次预置原材料，再stop/apply/start-p7/activate/最终gate/唯一prompt。材料未知即阻止App切换及prompt，重复start禁止。

App显式start-p7验证固定run、stage/case/inputSHA、原profile apply SHA；启动后要求唯一project-handoff preset和逐字段一致的七工具ready回执，保留唯一进程、版本、恢复及持久不重试约束，start-p6不接受P7连接。verify先从原私有session/prompt/binding提取独立正文，经单次可信采集和完整组合核验后再比较原sessionSHA，私有保存handoff-execution-verification.json。因语义门槛尚未完成，明确抛HANDOFF_SEMANTIC_REVIEW_REQUIRED，供Worker归UNVERIFIED；没有SUCCEEDED或下载产物/成功退出凭证，不把程序核验当用户采用。该中间限制不是最终产品范围，后续需接语义与业务成功入口。

新增5项adapter测试及2项App测试；真实本地组合子进程配模拟guest/会话证明执行证据保留而不误放行。P6/P7 adapter与Worker50/50（独立临时测试数据库，不迁移P5）、相关后端353/353、Node128/128及diff检查通过。外部App/SSH/模型边界均mock，无真实启动/部署/GUI操作；README同步。API/队列尚不注册P7、三组真实业务样本与自动应用收尾实测仍待，P7未完成。

P7后端官方会话客户端（2026-10-05）：1e06f27方案先行。核对现有desktop-session-command按kind选择startHandoffSession及五字段合同；新增HandoffSessionClient，只覆盖prepare并重新校验不可变HandoffSubmission（包括不安全model_copy），规范原输入SHA、固定run/session/workspace和project-handoff写入独占私有desktop-request.json。start/inspect/poll/cancel沿原官方子进程与持久单次意图，Flash/off、唯一preset/七工具校验保持；不传原材料或代码预制正文到prompt，材料仍通过VM受限工具读取。

新增9项测试覆盖私有绑定/不隐式启动/不覆盖、P6及非法额外字段和不安全对象拒绝、原官方命令/错误模型与会话/未知响应不重放、查询按guest实际raw而非模型工具数、取消单次。相关后端348/348、Node126/126通过，README同步；全部临时文件/mock RPC，无真实App/模型/VM调用。下一步连接任务adapter的准备/材料预置/启动/结果采集，再完成语义与真实业务验收；API仍未启用P7，未宣称产品已可用。

P7宿主证据包/可信采集（2026-10-05）：d952abe及dfe8c77分别先定义包解码和单次采集。handoff_bundle只在内存解析未压缩USTAR，严格最多69成员/64MiB、固定文件名单/普通文件/原身份/材料和正文摘要，拒绝链接/目录/PAX/GNU/重复/隐藏尾部/缺配对图片及数值类型替代，不用extractall。返回TRANSPORT_VERIFIED，原guest声明仍须由组合核验重算，不登记业务或语义成功。

handoff_collect限定HandoffControlClient、私有SSH wrapper和固定commit部署路径，先核对停止/零在途/1–30raw/撤销lease，独占采集意图后单次调用guest导出。原tar私有保存，结束后预算/停止/lease不变且包中raw与runtime一致；解码成功才新建guest/<run>/artifacts私有目录，逐个固定文件独占0600写入，最后保存传输回执。响应未知、坏包、已存在目录或部分失败不清意图、不重发，不输出token或改写VM业务文档。

新增19项包测试和11项采集测试：真实执行器配模拟Driver生成原证据，实际guest导出函数→模拟SSH传输→真实host解码/私有落盘→实际组合核验子进程，证明原会话/文件/图片链一致但semanticVerified仍false。活跃/在途/预算/部署拒绝、传输未知、坏包、状态/lease变化、预算不一致、目录冲突及重复采集均拒绝。相关handoff/P6采集/部署/会话/验收339/339通过，git diff --check通过；未调用模型/SSH/VM、未修改P5服务，README同步。生产任务adapter/API、语义预期与三组真实业务仍待，P7不标完成。

P7可信guest导出（2026-10-05）：0a667f7方案先行。新增VM限定handoff_export，与P6导出合同隔离；固定run/owner/epoch且原lease已撤销，接有界严格JSON/base64材料及独立正文期望。先完整核验handoff_evidence，再仅收固定材料/预置回执/重开意图/trace/state/PNG/final/document/result；每份有界普通单链接、SHA/长度一致，二次读取核对字节与文件身份，目录及lease不变后才输出USTAR。清单含原binding、输入/正文SHA和guest结论，不声明官方session或语义通过，不导出凭据/lease，不执行GUI或写VM业务正文。

host/guest部署白名单同步新增导出及两项核验依赖，共21个Python模块，旧P6路径保持。新增6项测试覆盖完整模拟原证据tar/无凭据/只读、活跃或缺lease、核验后文件变化、额外敏感路径、lease变化、有界严格输入及host拒绝。执行层302/302、相关后端27/27、diff检查通过；部署单测首轮因旧固定文件数量20而失败，更新为实际23次取源（21模块+许可证+安装器）后通过。未部署、未调用模型、未修改P5；host P7包解码、可信SSH采集、生产adapter及三组真实业务仍待，README同步。

P7执行证据组合核验（2026-10-05）：方案43b1555先行。新增backend.handoff_verify与只读handoff_inspect子进程入口，绑定原run/session/inputSHA/cwd/prompt；原会话提取报告后生成独立正文期望，核对guest材料/文件/轨迹、逐项官方工具交换、PNG转换记录及官方附件字节。原请求审计增加run/session/inputSHA与实际发送的image附件ID列表；每条assistant消息对应一条请求，检查Flash、七工具和累计原图片顺序，缺失/额外/未知图片引用拒绝。原会话与host记录有界私有读取并在返回前复读，guest核验沿原固定文件采集边界。请求压缩或额外尝试未满足严格映射时拒绝，不删去异常后拼成功。

验证：17项新后端用真实执行器配模拟Driver、模拟官方会话/图片完成跨进程组合链，10次模型工具交换对应15raw与11请求；包含原会话/提示/绑定/请求/截图/文档/附件篡改反例和九类请求审计反例。官方适配补实际图片ID审计及未知ID拒绝断言。相关后端236/236、执行层296/296、Node126/126、安装版官方适配11/11通过，均无模型/VM调用。原成功fixture返回EXECUTION_EVIDENCE_VERIFIED_SEMANTICS_PENDING，semanticVerified=false，不写SUCCEEDED。

边界：入口要求可信控制端已撤销执行并冻结、采集原证据；任意自洽目录不证明SSH来源，PNG/WebP摘要一致不证明视觉或报告语义。生产App/API路由、采集部署白名单、语义预期和三组真实VM业务样本仍未接完；P5源码/服务未改。README同步，P7仍未验收。

P7有界AX观察投影（2026-10-05）：e73335c设计先行。源码核对spill-policy以maxInlineTokens计文本+图片，不存在通用固定字符阈值；新增TS handoffObservation和Python project_handoff_observation独立实现同契约。P7 observe保留原snapshot/PID/window/title/app/截图有效标志/used，唯一目标AXWindow→AXTextArea最多16层原祖先链，只投影原index/parent/role/window label/body token/enabled及完整value，去菜单/重复tree/无关字段。拒绝重复索引、循环/无匹配/多正文、AXSheet/AXDialog、无效身份/截图、禁用正文、正文>4KiB、投影>8KiB；不裁正文或增加恢复工具，失败沿原stop关闭派发。P6输出未改；guest全state/PNG/trace仍保留，双日志核验按Python复算投影而非宽松解析或删[...]。

验证：新增官方投影反例1项、Python3项，更新官方observe集成及双日志独立期望。官方安装版11/11、Node全126/126（真实编译器临时profile）、执行层296/296通过，git diff --check通过。额外只读投影一份旧state-11.json：原62,729字节、168元素→516字节、2元素，完整正文逐字一致；当前TS经esbuild临时编译与Python独立复算deepEqual通过，未修改旧证据或改变旧任务状态。这是数据投影/历史形状验证，不是新真实P7模型会话通过。

限制：8KiB是自有输出上限，不保证任意官方token配置和图片价格都不触发spill；材料读取等其他输出仍需在最终官方会话逐项完整核对。没有禁用官方全局保留策略、运行模型、部署VM或更改P5。下一步组合原session、工具交换、请求审计、附件/guest文件与语义预期并接生产入口；README同步，P7未验收。

P7官方附件只读采集（2026-10-05）：bce148d设计先行。只读核对安装版app.asar内attachment-local的normalizedImagePath/readImageFile，确认objects/<前两位>/<SHA>固定布局及官方摘要语义；新增backend.handoff_attachments，仅接已匹配原观察的附件列表，不遍历目录、不使用display name为路径。本人私有规范home，逐层目录fd/O_NOFOLLOW，文件本人私有普通单链接，O_NONBLOCK拒绝FIFO，按已批准长度限读且校验SHA；同SHA去重但矛盾元数据拒绝，单件≤8MiB、总≤64MiB，二次读取比对原字节及文件/目录身份，根身份再次核对。无文件写入或转换。

新增21项采集测试，覆盖无扫描/重复摘要、恶意ID/额外路径/身份/格式/数量/大小、摘要或长度变化、权限/文件目录链接/hardlink/FIFO/缺失、相同字节新inode和总量上限。首次测试收集遇新增代码括号缺失，修正后相关输入/报告/会话/图片/P6回归219/219通过；git diff --check通过。另从指定旧正式任务原session提取一张image附件引用，通过原项目home真实只读读回92,650字节WebP，SHA匹配原官方ID；这是存储格式探针，不计P7真实业务验收，不改变旧样本状态。

该真实探针暴露后续必须修复的集成问题：旧观察文本长46,409字符，中间包含官方截断标记\\n\\n[...]\\n\\n，无法解析完整JSON。首个探针直接解析观察JSON因此失败，随后仅用原附件引用验证存储读取，没有修复或重写旧记录。当前P7完整state匹配遇此类文本会严格拒绝，不已知放行。下一步实现P7有界、来源可复算的观察投影，只保留任务窗口/正文及必要AX身份并保留原guest全证据；需先核对官方文本截断阈值与投影契约，不允许删截断标记或宽松解析后伪称一致。生产路线/组合验收/真实业务仍待，README同步。

P7图片转换来源与字节检查（2026-10-05）：bbfdb97设计先行。新增handoff-image-evidence，P7 observe把同一已收PNG缓冲区送官方saveImage，成功后、返回模型前独占0600/fsync写固定handoff-image-NN.json。记录原run/session/inputSHA/snapshot/1–30 used、输入PNG SHA/字节和输出附件SHA-ID/PNG或WebP类型/字节/尺寸；规范本人私有目录、无链接/不覆盖、有界长度，记录或转换失败关闭本地派发并请求原任务stop，不重试观察/转换。P6行为不变，无新增模型工具或预算。

backend.handoff_images纯核验器接受可信采集的转换记录、双日志观察映射、原PNG和官方附件实际字节，逐项核对身份、顺序、snapshot/used、来源摘要、附件SHA-ID/长度与格式前缀、官方消息元数据；只允许恰好所需的图片集，单图≤8MiB、总≤64MiB，去重附件按同一SHA复用。返回IMAGE_PROVENANCE_VERIFIED/imageBytesVerified=true，但visualSemanticsVerified/sessionVerified仍false；PNG/WebP前缀检查不冒充解码或独立图像语义证明，实际附件存储读取和最终组合入口仍待接。既有双日志输出补used，防同图不同观察记录错配。

验证：新增2项官方工具测试（包含参数/路径/权限/链接/不覆盖反例及记录失败后stop、后续零派发），18项后端字节链反例。首轮两项因测试临时目录未realpath及模拟session缺requestHeader失败，修正夹具后官方安装版10/10通过；未放宽生产约束。Node完整126/126（实际编译器临时profile）、相关后端109/109、执行层293/293及git diff --check通过。全部模拟附件/临时文件，未部署VM、未启用P7真实profile或发送模型请求，README同步；生产采集/请求审计组合、业务入口与真实语义/GUI验收仍待。

P7双日志有序映射（2026-10-05）：623fe26方案先于代码。新增纯handoff_exchanges，先重新核验guest原轨迹，再从成功材料结果/观察/输入保存标记/重开结束/结果读写构建有序逻辑调用，不相信外部“已验证”标签。官方每个call/result必须原ID唯一串行且与逻辑顺序一一对应；严格JSON区分bool/int，逐项核对材料原字节/单源SHA/used、完整观察state/used、输入snapshot/AX index/token/正文、save/reopen snapshot、重开末尾used、write最终snapshot/value及read完整正文。多余参数/返回文本、错误/重复/缺失/并发错序全部拒绝；重开内部关闭/list/native/list仍计原raw，不拆成模型多次调用。

只读历史官方证据确认观察附件实际mediaType=image/webp、attachmentId为sha256，原guest仍PNG；不能把附件摘要直接当原PNG哈希。当前只验证附件ID格式、PNG/WebP类型、正整数尺寸/长度及每次观察附图，返回attachmentsToVerify清单；sessionVerified/imageBytesVerified/semanticVerified保持false，后续必须结合原附件字节、请求审计和session来源/终态。无读取个人图片或新增真实调用。

验证：新增6项unittest包含逐个10调用参数/返回的篡改、snapshot/token/输入/重开预算/读回、ID/顺序/错误/重复/并发、图片缺失/格式/数值、guest轨迹变化等多组反例。真实执行器配模拟Driver生成15raw，独立构造10次官方工具交换匹配；这是模拟证据，不是当前真实模型验收。执行层全293/293通过（私有backend-venv python -m unittest discover -s tools/mac_vm/tests），git diff --check通过。README同步，未修改VM/P5或活动App；请求审计/附件组合、生产入口及真实业务仍待。

P7原官方结果提取（2026-10-05）：ff3f27c先提交设计。只读本地保留的原官方v4 session结构，确认assistant/message的data.message.content、model source、message id、turn/end与原prompt字段；不根据记忆猜字段，不重新派发模型。新增backend.handoff_session纯提取函数：原字节≤64MiB、严格UTF-8/JSON与唯一递增seq，v4原session/cwd/project-handoff preset、非seed/无delegation、唯一原用户rpcId和提示内容、单turn completed、所有请求Flash/off及七工具。assistant消息ID唯一、固定模型来源；工具声明和实际call参数/名称/ID对应，结果唯一且无错误，最终assistant必须在所有工具返回之后且仅文本。

最终正文≤64KiB、只解析一个完整严格JSON，重复键/非有限数/围栏/额外文字拒绝，不从stream或工具返回猜取。调用既有HandoffResult独立校验原run/session/inputSHA、原任务事实/引用及计数，再调用独立文本投影；保留原sessionSHA、最终正文SHA、消息ID/seq及报告。仅返回SESSION_RESULT_EXTRACTED，sessionVerified/guiVerified/semanticVerified均false，尚未做官方工具到guest逐项映射/request-audit/VM证据合并，不能当业务成功。

验证：新增33项模拟v4证据测试，覆盖会话/提示/preset/模型/工具变化、seq/多轮/未完成、错误call/result/来源、最终消息位置/重复ID、非法JSON/伪造引用与原事实、工具返回或stream内假报告。相关输入/结果/投影/P6会话回归合计180项通过，命令为私有backend-venv python -m pytest backend/tests/test_handoff_session.py backend/tests/test_handoff_result.py backend/tests/test_handoff_document.py backend/tests/test_handoff_contract.py backend/tests/test_desktop_verify.py backend/tests/test_desktop_session.py -q；git diff --check通过。无VM/配置/真实模型变化，README同步；后端生产路由、完整双日志验收和真实业务样本仍待。

P7固定文件证据核验（2026-10-05）：6131f42先提交设计，再新增只读handoff_evidence。可信调用者传入原run/owner/epoch、冻结材料与独立正文期望；原材料字节/SHA与两份预置回执严格对应，重开intent逐字段等于原trace，复用独立handoff_trace检查完整保存/重开顺序及预算。每个观察的state-NN.json与原result按严格JSON类型对应，PNG原字节哈希/长度匹配observation_evidence；final_state必须是轨迹指定的新观察，固定文档==独立正文，result==正文+约定末尾LF。拒绝重复JSON键/非有限数与True/1类型替换。

固定私有目录以fd逐层O_NOFOLLOW读取，文件限本人普通单链接，材料/intent/trace要求私有权限，单文件限长、总量≤64MiB；O_NONBLOCK避免FIFO阻塞。读取前后及路径身份检查，再在返回前重新读取全部文件核对字节、设备/inode/大小/mtime/ctime/mode/link数和根目录身份，同内容替换也拒绝。这个离线检查不能替代调用者先撤销许可、确认零在途及可信传输；PNG仅验签名/哈希，不声称理解图像。返回VM_EVIDENCE_VERIFIED、filesVerified=true，官方session/semantic仍false，不标业务SUCCEEDED、不触发清理，生产接线和部署白名单尚待随后统一接入。

验证：新增10项测试，以真实HandoffDesktopTask配模拟Driver产出的15raw轨迹和16份临时文件核对原字节不变；覆盖材料/账本/截图/状态/最终文件篡改、错误owner/epoch/状态/SHA/长度、重复键/非有限数、丢文件/权限/超长、symlink/hardlink/FIFO/子目录链接逃逸、读取中途变化及相同字节新inode替换。`/Users/zhangchengjie/CUAgent/.runtime/backend-venv/bin/python -m unittest discover -s tools/mac_vm/tests` 287/287通过；git diff --check通过。README同步，无模型调用、无VM部署、无P5改动。下一步原官方会话JSON提取、结构/语义核对及App/后端P7路由；真实GUI业务验收仍未完成。

P7独立轨迹验收第一步（2026-10-05）：25f2db1先提交设计，再新增纯读取handoff_trace，不改P6验证器或其工具白名单。外部绑定原run/材料规范字节/独立正文期望；核对原approval、空文档初始化、唯一launch PID、来源SHA与原文、唯一串行call_id和连续1–30预算、停止后零派发。输入与保存逐次对应最近新观察，重开前新观察必须位于保存之后且正文一致；每个hotkey归属保存或唯一关闭，重开intent/关闭/native ACK/窗口清单/新窗口标记顺序及PID/窗口/SHA严格一致，两个清单阶段均1–3次。所有内部调用留在原账本，原intent前used≤19，重开后只允许读取/观察及唯一写结果，不允许编辑。

所有get_window_state成功结果必须有唯一observation_evidence且同PID/正确阶段窗口；write_result绑定重开后最新、30秒内且无中间请求的观察，读回必须完整多一个约定末尾LF。材料读取也消耗原观察效力；来源JSON按规范字节比较，不用Python宽松True==1相等代替原字节。当前检查不读取截图、固定文件或官方session，也不验证模型语义，明确返回TRACE_VERIFIED及三个false；任何error/UNKNOWN/拒绝轨迹暂不放行，完整保留供后续分类，不过滤失败拼成功。

验证：新增8项unittest、多组源/正文/回执/时间/预算/窗口/观察篡改反例，采用真实HandoffDesktopTask产生原轨迹、模拟Driver/native且只写临时目录。正常15raw通过；12次真实本地材料读取加两个阶段各3次清单合计30raw也通过，验证预留与内部计数；关闭失败/ACK无窗口/正文变化/错误材料、停止后派发、旧观察重用、动作前穿插材料读取均拒绝。执行 `/Users/zhangchengjie/CUAgent/.runtime/backend-venv/bin/python -m unittest discover -s tools/mac_vm/tests` 共277/277通过，git diff --check通过。README同步；私有文件采集、官方最终JSON、语义验收和App/后端P7路线仍待，未部署VM、未切换App、未使用真实模型，P7阶段未验收。

P7受限GUI重开实现（2026-10-05）：1a41bb6细则先于代码。HandoffDesktopTask要求已save、当前新snapshot/原PID/窗口、AX正文与固定文件一致和used≤19；独占0600/fsync原重开意图，唯一Command-W关闭、最多3次预算内窗口清单证明旧窗口消失，再由可信runtime绑定原ApplicationIdentity和固定文档调用native Open Documents，最多3次清单确认同PID唯一窗口。关闭/每次清单/native打开均走原raw审计；ACK不当窗口证明，原文件SHA不变，清除snapshot要求新观察，重开后type/save拒绝、write_result只接受重开原正文。失败停止原任务，native不确定标UNKNOWN，意图保留且不重放，STOP期间不继续派发后续窗口查询。

native以NSRunningApplication核对原PID/bundle/可执行路径/launchDate，再用NSAppleEventDescriptor向该PID发送仅原run固定文件的Open Documents，NeverInteract、AppleEvent1秒/进程3秒超时，无默认应用查找、新实例、强杀、保存/丢弃或任意路径。本机SDK头确认方法/常量；另在host只构造未发送的AppleEvent并查询selector，constructed/sendSelectorAvailable均true、NeverInteract=16，没有发送事件或操作宿主应用。此语法证据不替代VM实际发送/TCC许可/文件窗口证明；真实VM仍未验证。

新增9项重开状态机反例、2项native模拟测试及1项后端真实本地HTTP路由测试；执行层269通过、相关后端43通过、官方安装版8项工具适配通过。覆盖窗口不消失、ACK后无新窗口、文件变化、超时、原预算11次预留、部分意图拒绝、在途停止、重开后无新观察拒绝写结果；P6同时拒绝read_materials/reopen并计拒绝预算。P7插件新增第七工具vm_reopen且参数透传guest约束；没有实际部署或模型调用。README同步，下一步必须接新轨迹/原session最终JSON独立核验与P7 App/后端入口，不能沿用P6旧验证器判交接成功。

P7 profile/session与业务输出协议（2026-10-05）：e7e0dcb及3f178bc两份细则先于对应代码。新增固定project-handoff模板、prepare-handoff入口，双向移除旧P6/P7 preset而保留账户，沿原精确配置备份/恢复，不改活动profile。startHandoffSession严格kind/run/session/inputSHA/cwd与私有七工具ready绑定，缺vm_reopen（当前真实插件仅六工具）时零RPC拒绝；否则沿原一次create/selectModel/prompt持久意图，唯一preset及Flash/off，不重建或重发。P6提示保持原字节语义，inspect/cancel继续使用原session；尚未接App启动和后端adapter的P7路由。

HandoffResult JSON schema固定随源码并与Pydantic schema做一致性测试；P7提示要求模型基于材料生成三章节GUI文档，保存后重开/观察/write_result/read_result，最终仅回复来源JSON。backend.handoff_document先结构/来源校验，再生成独立期望文本（CSV顺序、JSON字符串防换行伪造章节、单源引用索引），不写文件、不调用模型、不判语义通过；超4KiB明确失败，不删减/截断，20项最坏输入可失败的限制保留。材料插件对已核验原文计算sourceHashes供引用，不要求模型心算SHA；原guest协议和原输入绑定保持。

验证：新增11项P7会话RPC模拟、2项profile测试、4项Python schema/投影反例；CUAGENT_TEST_BUILD_TOOLS显式指向原私有只读编译依赖，node --test agent/tests/*.test.mjs全126通过（启用原可选编译测试，不再跳过），所有profile编译在临时目录且原配置字节不变；相关后端144通过，官方安装版适配8通过，git diff --check通过。中文源SHA/多行转义、三章节/任务顺序、错误事实及正文超限拒绝已覆盖；schema和投影不代替语义预期/真实GUI。没有派发真实模型、切换App、部署VM或改P5，README同步，阶段未完成。

P7官方插件材料工具（2026-10-05）：739c199设计先行。原c0-vm-tools仅caseId=project_handoff、stage=p7、严格p2 UUID和输入SHA时加vm_read_materials；旧P6五工具不变，混合/缺失绑定拒绝初始化。新工具零参数声明，实际多余参数仍传guest以保留拒绝预算，读取复用原owner/取消/固定URL/无重试通道。新增handoff-materials重算完整材料规范JSON SHA并核对返回SHA、对象字段与1–30整数预算，拒绝篡改/超长/伪哈希，原文只作为数据输出。新kind的就绪记录携带kind/inputSha，旧P6就绪结构未改；模型请求仍需完整白名单，少工具或越权工具均拒绝。

验证：安装版官方App版本只读核实0.2.0-rc.2；沿test-desktop-adapters同样构建/运行方式，明确从原CUAgent私有desktop-build-tools只读加载esbuild，把当前worktree的测试bundle写入.runtime/p7-material-tools-tests.mjs，以官方App ELECTRON_RUN_AS_NODE=1运行--expose-internals --test，不启动GUI或改profile。旧5项+P7新增3项共8/8（内含多组配置/响应反例）通过；python原canonical独立计算中文/emoji/组合字符/CRLF材料SHA 7fbabfe7c6b1f7ac3eb7f83ad3a0ff3fda3d62fd2ef10c0b92ae1ea439d30f33，与JS断言一致。node --test agent/tests/*.test.mjs为112通过/1既有跳过，git diff --check通过。全部为官方工具定义+模拟transport/本地数据，不冒充真实模型或VM；P7 profile/session与报告生成、语义验收、GUI重开仍待，README同步。

P7专用激活与模型侧材料协议（2026-10-05）：1e7dacd细则先行。独立/activate-handoff严格接受非空SHA，重新读私有单链接intent/receipt并核对原binding/状态/字节数；共享原独占activation intent，在原lease下实例化HandoffDesktopTask，启动工具HTTP前重核输入字节/JSON及租约。任一不确定失败沿原revoke关闭准入；不降级P6、不重放。HandoffControlClient仅凭成功预置回执选择新路由，仍复用原activate单次/实时authority/时限验证；无回执拒绝。生产工厂不可注入替代实现，测试注入仅loopback；输入预置与启动只属可信生命周期，模型首次read_materials计原预算一次。

工具HTTP仅在HandoffDesktopTask实例上添加零参数read_materials，旧P6 DesktopTask仍拒绝且计拒绝预算；任意路径参数拒绝。新增13项后端测试（原19项材料测试一起共32项）及1项执行层P6兼容反例，真实localhost上传→专用启动→模型token读取→撤销→后续读取拒绝；另测错误SHA/owner、缺回执、字节数、材料篡改、公开权限、非法/空SHA不能回退、模型控制权限拒绝。最终相关后端140通过（0.90秒），执行层258通过（1.258秒），git diff --check通过；README同步，无真实模型/VM/部署或P5运行环境修改。官方Harness工具注册、模型报告生成、语义预期与GUI保存重开/导出仍待，不以材料读取代替业务验收。

P7材料可信传输（2026-10-05）：7b27e61方案先于实现。新增HandoffControlClient与guest handoff_input，host严格验证输入后编码原规范JSON、实时检查authority/租约；独立控制token的/handoff-input匹配原run/owner/epoch，未激活且有效lease才接收。guest核对SHA、固定输入对象与JSON合法性，通过原私有目录fd独占0600/fsync保存intent→原输入→receipt，保存后重新检查租约；部分失败/已有意图不覆盖或重发。回执精确匹配绑定/哈希/字节数/STORED；新client也不能绕过guest持久意图。该路由请求上限384KiB，其他控制路由仍4096字节。生产尚未部署；新增材料意图会拒绝旧P6 activate，直至独立P7激活/工具链完成，不能将上传成功称业务执行完成。

新增19项真实localhost HTTP/临时文件测试：host输入→guest原字节→HandoffDesktopTask原预算读取跨层一致；模型403、错误身份/布尔epoch/哈希/base64/额外路径/重复JSON拒绝；ACK丢失无重发、部分意图/旧文件保留、authority失败/租约撤销、写后到期不回成功、超过4KiB合法材料及旧路由限制、原激活意图拒绝后置上传。初轮32通过/1失败仅部署测试旧18次Git读取断言过期，新增两模块后明确改为20次（18模块+license+installer），未放松部署文件集合；最终相关后端127通过，执行层257通过，git diff --check通过。README及部署白名单同步；没有复制凭据、启动服务、操作VM或模型推理。报告生成/语义预期/保存重开与正式验收仍待。

P7 guest受限材料读取（2026-10-05）：f8238d9方案先行。新增独立HandoffDesktopTask，可信构造侧绑定inputSha256，只读原目录handoff-input.json；原lease/admit/dispatch/result/error/inflight账本共用，每次读取/失败计一次raw，不调用Driver或其他程序，不重置30次预算。固定目录fd、O_NOFOLLOW/非阻塞、私有普通单链接文件、256KiB JSON开销上限、原字节SHA及严格JSON解析；拒绝模型路径/哈希参数。读前使GUI快照失效，停止前已准入的只读结果可以返回并记录，停止后不再准入；重建对象保留停止状态及原调用数。host输入语义合同仍是可信预置前提，未声称guest再次实现全套Pydantic合同。

新增10项临时文件/模拟lease测试，包括真实累计30次读取、第31次及重启拒绝、在途停止、原文注入不执行、哈希篡改、缺文件、符号/硬链接、FIFO、公开权限、超长文件、非法UTF-8/重复键/NaN。首轮9项中权限反例产生2个断言错误：现有LeaseGate.private抛ValueError，测试仅接受StopRun/OSError；实际已拒绝，补正确异常预期后全通过。最终python -m unittest discover -s tools/mac_vm/tests为257项通过；没有部署VM、调用模型或改P6生产HTTP工具清单/部署白名单，不把新增类当生产已启用。可信材料安装、独立kind入口、模型生成及GUI保存重开仍待；README同步，P5服务和冻结源码未改。

P7来源绑定结果校验（2026-10-05）：cc3e940方案先于代码。新增backend.handoff_result的结果/引用/问题契约及verify_result，绑定可信原run/session与完整请求SHA；CSV任务恰好一次、事实原值、四状态计数、严格早于asOf且未done的逾期、未知owner/逾期问题集合独立复算。引用按Unicode码点精确切片、源SHA及去重，冲突至少两个不同引用，额外权限字段/控制字符/单文本2KiB和结果64KiB边界拒绝。不读写文件、不派发模型或GUI，不将结构校验映射为任务SUCCEEDED；语义及GUI标记始终false。反例明确证明“真实引用+错误结论”仍需独立语义验收，不能把本模块当业务完成判据。

首轮119通过/1失败：model_copy绕过StrictInt后，model_dump(mode=json)把布尔值转换为数字1，原序列化后重验未拒绝。修正输入及结果所有嵌套模型revalidate_instances=always，先验证原实例字段再序列化；新增5个嵌套copy/construct绕过反例。最终54项结果测试，与输入及P6契约合计125通过（0.08秒）；命令为原backend-venv/bin/python -m pytest backend/tests/test_handoff_result.py backend/tests/test_handoff_contract.py backend/tests/test_desktop_contract.py -q。只跑相关纯本地测试，没有数据库/完整后端/模型/VM验收；README同步，P5冻结目录与服务未改，阶段仍未完成。

P7现场前检与输入契约（2026-10-05）：实时Codex剩余71%、普通可用、积分基准未变/重置卡未用。SSH身份mvpagent/VirtualMac2,1、Driver602仍在，未发现TextEdit；只读AppKit查询实际取得Driver完整路径及launchDate微秒，证明该读取语法现场可执行，不冒充TextEdit退出验证。ioreg显示VM锁屏；原P5 API80171和scheduler81383均不存在、18089无监听，Worker30244仍在。首次schedule-status误用位置参数被CLI拒绝，改为--schedule后实际连接拒绝；没有推断计划已暂停/结束，也未重启服务、解锁策略、部署或调用模型。现场缺就绪条件，先继续离线业务实现，不标整体目标阻塞或完成。

863685e输入细则先于代码：新增backend.handoff_contract的冻结HandoffSubmission/Note/Task，严格1–3笔记、1–20任务、固定CSV列、唯一id、日期、状态、空owner未知、控制字符和UTF-8分项/32KiB总界限，额外字段禁止。原文本不裁剪或Unicode归一化，来源SHA独立命名，CSV公式及提示注入只保留为数据，不执行；返回tuple任务，不生成交接内容或文件。新增37项测试，与旧P6输入契约合计71通过（0.04秒），含中文边界、非法CSV、冻结/往返、来源变化、额外权限和旧类型拒绝；未跑完整后端，不倒填新的总回归数。结果契约/语义核验、来源读取、API与真实GUI交接仍待，README同步。

P7 host自动收尾接线（2026-10-05）：e680fc5方案先于实现。adapter只有在guest/原官方会话独立核验、产物复制与verification持久保存后才登记三文件SHA；restore恢复原Harness后写独占清理意图，控制客户端单次请求并严格核对原身份/哈希/非强杀/退出原因，再复核停止、零在途和原预算。EXITED才shutdown；REFUSED/UNKNOWN/丢ACK保存回执或固定告警并抛出，沿Worker既有恢复失败隔离处理，不改变已核验业务结果、不自动重发。未核验任务保存skipped/applicationMayRemain告警，保留未保存应用。清理请求socket超时60秒，普通控制请求仍2秒；guest原锁和独占意图仍是跨进程保护。

验证：新客户端16项参数化用例、adapter新增4项；首次直接pytest为43通过/2缺数据库环境设置错误，标准入口在独立worktree也因无backend.env提前退出。未复制凭据或修改P5配置，显式将manage.ENV_FILE绑定原私有文件、运行当前worktree标准test；夹具每项新建cuagent_test_UUID独立库，完整后端604通过/1既有Starlette弃用警告（71.04秒）。执行层247通过，含真实本地host客户端→guest HTTP→回执联动（native和GUI证据仍模拟）。git diff --check通过；无真实模型/VM/App操作，部署与现场退出/保存提示验证仍待，P7未验收。

P7 guest收尾控制入口（2026-10-05）：e846ea2细则先于实现，新增runtime.cleanup_application和仅独立控制token可访问的/cleanup-app。严格host终态/核验声明与三文件SHA，原runtime持锁且有捕获的应用身份；重新检查lease停止、零在途/UNKNOWN及原调用数，以固定文档运行只读guest GUI证据核验，再由协调器单次正常退出并复查哈希。不会调用Task.stop改写冻结trace、不释放共享锁/改变业务成功状态、不恢复许可。控制JSON重复字段拒绝，HTTP 200只表示返回清理回执，必须另检查EXITED，不能把REFUSED/UNKNOWN算通过。

新增9项真实本地HTTP/临时文件、模拟native与GUI核验测试；执行层全246通过，后端client/deploy/bootstrap相关26通过。覆盖模型403、可信声明/重复字段409、在途/核验失败/哈希变化/原预算不符拒绝、唯一退出与原trace/预算不变；没有实际VM原生动作。host正式验收后的客户端接线和部署/真实验收仍待，生产未启用自动退出。README同步，P5未改。

P7启动所有权接线（2026-10-05）：9ce45ec方案先于代码，生产DesktopGuestRuntime为DesktopTask注入可信launch observer；原launch_app前记guest时间，成功后、首个list_windows前查询原生身份，启动时间必须落在本次launch至采集期间。独占0600/fsync保存owned-application.json并绑定run/owner/epoch，旧实例、消失、未来时间或已有/部分记录拒绝；记录失败由原observe异常路径stop，不重启、不继续窗口操作，原launch计数保留。loopback默认无原生调用；部署器/安装器白名单同步新增两模块，旧VM部署未改。

新增6项生命周期/顺序反例，执行层全237通过；部署/启动专项19通过。首轮新增生产接线测试误绑定VM地址，236通过/1错误，改为仅测试服务器使用loopback后通过，生产网络门禁不改。该轮全部为临时文件/本地socket/模拟系统响应，未运行模型或VM原生查询。实际退出控制入口与host核验后调用仍待实现，不宣称自动清理已生效；README同步，P5原运行环境不动。

P7原生收尾适配器（2026-10-05）：实施细则5a4103c先于代码，新增desktop_app_native，只允许固定普通VM身份检查后调用系统osascript/AppKit。读取同PID的bundle/完整可执行路径/launchDate微秒；缺AppKit对象时以signal 0确认进程确实不存在，查询/权限异常不当退出成功。正常terminate在同一脚本内核对启动时间和固定TextEdit身份，单次子进程限3秒，无强杀、名称匹配退出或保存/丢弃操作；超时/非零/格式异常只返回固定未确认错误、不重试。没有模型工具/CLI注册，也未接任务生命周期和部署清单。

12项新增模拟系统协议测试通过，执行层全231项通过；覆盖宿主拒绝先于系统访问、PID/类型/路径错误、进程仍在但AppKit查不到、权限错误、重复JSON字段、超时和退出ACK不等于消失。未运行真实osascript/VM调用，不能据模拟响应证明原生API现场可用；实际启动身份采集、可信持锁接线及真实正常退出/未保存告警验证仍待。README同步，P5环境未动。

P7应用收尾协调器（2026-10-05）：沿既有p7-project-handoff分支，细则5938768先于实现。新增desktop_app_cleanup，显式绑定原run/owner/epoch、TextEdit PID/启动时间/固定可执行路径及独立核验的document/result/trace SHA；要求terminal、stopped、verified、零在途/UNKNOWN。退出前复查，退出后文件/调用数/状态不变才确认EXITED；身份变化、退出未确认、查询失败、未保存/未核验均保留REFUSED或UNKNOWN，不强杀、不自动保存/丢弃、不清预算。每run独占0600/fsync意图和回执，部分意图、对象重建、未知响应禁止重发，持久化失败显式抛错，错误原文不进入回执。

新增21项本地单元/反例全部通过，执行层全219项通过（命令：原backend-venv/bin/python -m unittest discover -s tools/mac_vm/tests）；使用真实临时文件验证私有权限/持久防重发，其余应用/身份/状态回调模拟。只读退出轮询最长3秒且最多13次，各OS回调超时需下一步原生适配器落实，不能称整体墙钟硬限3秒。尚未接启动身份采集、原生退出、host独立验收后的控制入口或部署白名单，因此生产收尾行为未改变，未做真实VM验收。接线必须持续持原共享锁，回调只由可信执行端构造，模型不能提供“已核验”标志。P5原目录/服务未改，没有新增模型或VM操作；业务契约、三个真实工作流和P8仍待完成。

VM残留进程清理（2026-10-04，用户明确要求）：SSH进程清单与VM原trace匹配23个TextEdit实例，均对应已停止测试，bridge.lock可取且无quarantine。清理前这些实例RSS合计2722MiB（共享页可能重复计入，不等于实际释放内存）；持原共享锁，先在VM私有process-cleanup-20261004-001备份63份业务文档/轨迹，再逐PID核对bundle并正常请求terminate。23个全部退出、无force、原文件哈希零变化；复查无TextEdit及匹配的Python/Node测试进程。CuaDriver、系统服务、SSH、原Calculator/Terminal保留；P5原Worker/API/scheduler仍在线。根因是Task.stop/guest close只撤销派发/关闭桥接、不退出测试App，P7已补收尾方案，自动化尚待实现。

P6阶段收口（2026-10-04）：逐项核对设计六类门槛及11份原审计/轨迹，新增[p6-summary](docs/stages/p6-summary.md)。同版三例006、日报兼容及历史停止/到期/失权/拒绝证据范围分别列明；核心许可/运行时/HTTP/执行控制四文件与c448ae2现场版字节一致，Worker准备失败和初始窗口等后续差异由当前测试覆盖，不称全部现场在最新版重跑。重新执行后端584通过（1既有警告）、执行层198通过、Node112通过/1跳过/0失败，原失败及未知usage不改写。

限定为已有安装、单人受控TextEdit任务接入服务的P6工程验收通过；没有宣告通用桌面、C3、用户实际采用或P5一周通过。README/后端说明同步当前范围，阶段代码保留P6分支，不升级P5运行环境。P7实际业务需用户明确应用/输入/交付物后才另开分支写方案，P8仍待；总目标继续。

P6旧日报实际兼容（2026-10-04）：先有7fd9464方案，入口修正9e5f3f3先于执行；daily-report-compat-001独立库/API18107，原task 6b09fa22-40ef-42e3-8f14-f6912324dbf4，session-72beec86-d10f-463a-8eeb-f6390c2efac5。新版backend.api.create_app（关闭desktop开关）/P6 Worker，诊断程序显式绑定原安装PROJECT，只复用87份逐字节一致的旧agent/Worker源；唯一不同的旧agent文件c0-vm-tools不在A1依赖/build范围。未改产品执行源码或P5冻结文件，不声称新worktree已具备独立安装能力。

真实普通日报SUCCEEDED/10raw/12008token（输入1929、输出607、cacheRead9472、cacheWrite0，货币未知），原请求Flash/off。独立核对冻结笔记正文和两行CSV、数量2/总和6/均值3，原完整工具/会话审计和报告验证通过，正式report.json/report.md下载与产物SHA一致；无continuation或重发。执行前新额度剩余74%、普通可用、余额未变、重置卡未使用。

准备失败完整保留：三次POST /tasks使用了desktop_service.serve，被其DESKTOP_ONLY_SERVICE门禁拒绝，数据库始终为空、未有模型调用。最初误归因为笔记标题的私有记录已追加纠正；另外两次本地笔记检查确有标题/固定三节缺失，错误原稿保留，补齐后才冻结正式输入。按新方案精确停本次私有API29878，以同库普通API30032启动，保留同一幂等键；未修改桌面专用门禁、未更换失败模型样本。

P5 Worker29613→30244，API80171/scheduler81383仍原身份；App前后空闲、原profile及base-tasks字节一致、原基础账本未变、P5六项冻结源一致、独立任务资源释放且无恢复告警，0600介入回执保存。本步证明已安装环境的旧日报兼容，不是VM桌面任务、C3或用户实际采用。P6同版业务三例及此兼容门槛已有证据，仍需逐项总审查/总结后判定阶段；P5真实168小时与P7实际用途仍单独待完成。

P6正式三例006（2026-10-04）：按0e448fa方案冻结host/guest 0e448fa983d0ecba200b32d8d23e7c6986331a5f，guest manifest 3673bd7d65a0579851c3fb40e2d182311b8450313f62868ab56dddc2eeb3ee81，独立API18106。英文a2bbc72d-93a5-466e-8bc9-5d89aa123f20、中文00e85989-305b-444d-ac15-b35e306b3136、混合7a16dc0b-b9da-44e4-99d9-9dfd53d2b745全部SUCCEEDED，实际调用12/12/11，token分别481161/479505/400096，总35raw/1360762token，费用未知；全部原会话Flash/off。

正式客户端下载document/result逐字节匹配冻结要求；独立SSH重读原VM文件/轨迹，与原guest bundle哈希一致，许可停止且停止后零派发；官方会话与guest账本独立核验通过，三张原PNG正文视觉核对一致。本组三例均未触发输入拒绝恢复、缺结果读取恢复或初始窗口等待，不将旧证据复核/单元反例算作本轮现场覆盖。原001–005失败和未执行样本不改成功、不补跑。

P5 Worker27659→28951→29301→29613，API80171/scheduler81383身份仍一致；原profile逐字节恢复，六项P5冻结源码和本轮P6冻结源码重核一致，私有介入回执0600保存。此为同版业务三例通过，不代表P6全阶段或P5七日通过。下一步按新方案做旧日报最小实际兼容，再汇总安全门槛、历史失败、版本范围与交付限制；用户实际采用仍未评估。

P6初始窗口有界就绪（2026-10-04）：沿4441300实施前方案，仅DesktopTask首次observe增加单次launch身份核对、原PID最多3次list_windows、每次原许可/停止/身份/预算门禁；窗口须唯一同PID/应用/完整标题且明确可见，异常结构/多匹配/失权/停止/预算不足即停派。两次最多1秒等待，查询前后检查5秒观察截止；原Driver单次超时不改，不保证方法墙钟≤5秒。找到后继续原截图/AX与原文件哈希链路，不激活旧窗口、不删文档或重启应用，旧C0/RealAppTask实现不改。

6项专门测试（含11个子场景）验证延迟出现、原PID/一次launch、全部查询计数、缺失不复活、错误/隐藏窗口、歧义/结构/迟到、停止/失权/进程身份与真实admit耗尽30预算；执行层全198项、后端全584项通过，既有Starlette警告1项，git diff --check通过。无新模型/GUI/部署，本步不能断言005混合例具体系统根因或修复版现场已通过。下一步冻结新版真实回归，再做日报兼容及P6总验收。

P6输入拒绝恢复核验（2026-10-04）：按4441300方案实施，real_app_verifier增加默认关闭的allow_rejected_input，P6显式启用；仅完整配对、明确refused、早于新观察和唯一真实输入的rejected_type_text可接受，真实输入失败/UNKNOWN及重复编辑仍拒绝。host逐项对应官方vm_type和guest拒绝/真实输入的顺序与错误状态，至少一次新官方观察，成功正文/快照/哈希严格核对，分别报告恢复拒绝次数；不删错误行或清预算。39项host专项、16项guest专项（含8个子反例）、执行层全192项、后端全584项通过，既有Starlette警告1项。

只读复核005中文：独立SSH复制原state/PNG/trace/document/result到新私有目录，四份原文件SHA与原失败审计完全一致；新guest/host规则均通过，13raw、1次输入拒绝恢复，原PNG正文人工视觉核对一致。原数据库任务保持UNVERIFIED、未补产物交付、未重发模型/GUI或部署VM。初始窗口就绪问题仍待实现，之后才冻结新版真实回归；P6未验收。

P6正式三例005（2026-10-04）：冻结65f62146e2403aa458e5193f08a87091656c5fac，host/guest同版，manifest 8fbaedcfdc3612494f344b8eed45cf61491431650f689d4bf0abfbbac11cea5f，独立API18105。英文cf7a1bc2 SUCCEEDED/13raw/576132token，中文46e09510 UNVERIFIED/13raw/581694token，混合45eef8c2 UNVERIFIED/2raw/4182token；总28raw/1162008token，费用未知。英文原文件/下载/官方会话/guest截图与停止后零派发独立通过；失败同样SSH重读原轨迹/文件并保留未通过状态。

中文首次vm_type的snapshot_id误填s00000079:1，被原执行层拒绝；新观察s0000007a后唯一真实输入，原document/result字节正确，但business whitelist及host仅一次vm_type契约不支持此恢复。混合例launch返回原PID30824，首次list_windows没有本任务可见窗口，只有历史标题；原执行停止，后两次模型观察请求也拒绝，预算仍2，无正文/result，不能猜具体系统原因或补跑。三例实际控制口19099/19100/19099，第二例原首选占用时成功改用固定范围内19100；旧004失败不变。P5 Worker26552→27079→27422→27659，API80171/scheduler81383未动，原配置恢复与六项冻结源一致。本轮1/3，不是验收通过；已写拒绝后恢复核验及初始窗口有限只读等待方案，尚未实现。日报旧runner依赖原安装目录，兼容验证需先核对使用源与当前P6一致，不能在空worktree运行时盲切App。

P6启动前失败现场诊断（2026-10-04）：方案2643fcd先于执行，执行源码90af0cf；独立prebootstrap-failure-live-001原任务573ada6f-558b-4695-ae4d-3e8e0feaffb6。正式worker_once/实时额度75%/原共享锁，真实profile.prepare后在端口选择入口注入一次EADDRINUSE（不声称占满端口），原adapter/证明/Worker结束FAILED、0raw、session空、usage未知、无产物/新隔离。回执明确guestNotStarted=true、guestRevoked=false、cleanupConfirmed=false、profileUnchanged=true、restoreRequired=false。独立SSH核对原guest目录与launch日志不存在、共享bridge锁可用、无guest隔离；App前后会话空闲、原profile及P5六项源SHA一致。P5 Worker25312→26552，API80171/scheduler81383未动，私有介入回执0600保留。该受控故障证明安全收尾，不是业务成功；正常新版三例、日报兼容及P6总结仍待。

P6启动前失败终态（2026-10-04）：按05a1e2f先行方案，为PreparationClosed增加明确closed/not-started状态。adapter只在profile.prepare返回后、bootstrap调用前的本次端口预检失败注册原task对象；回执独占保存失败则不注册。独立复核原binding、严格布尔、全部启动/切换/隧道/清理意图缺失（断链也拒绝）及原profile-plan/before/当前配置一致。Worker仅在心跳确认退出、原执行权仍有效、正常finish后免新隔离，结果FAILED或STOPPED，usage未知；guestNotStarted与guestRevoked/cleanupConfirmed分开，不伪称未启动guest已被撤销。旧隔离/失败不动，bootstrap未知/失权/DB异常仍保守隔离。

验证：首轮相关90项通过；新增真实adapter＋Worker＋独立PG组合测试首次因测试误用submit的tuple返回值出现2项失败，修正测试后后端全574项通过（1项既有Starlette弃用警告），git diff --check通过。组合测试仅模拟生命周期命令和外部边界：明确未启动可收尾，profile改变则隔离；不是现场App/VM诊断。未新增模型调用、未修改P5环境，API/Worker/scheduler原进程仍在线。下一步冻结现场零模型诊断及新版真实业务回归，再做日报兼容与P6总审查，P6未验收。

P6控制端口选择（2026-10-04）：按030ae9d先行方案实现，生产19000–19999首选端口仅遇EADDRINUSE时有界环回选空闲口；最多1000次、其他错误立即抛出。bootstrap前0600独占记录原binding/首选/实际端口，client与SSH一致；原二次绑定检查和身份核对保留，后续竞争不选第二次、不重启guest。底层范围外只查指定端口，生产配置范围不变。33项专项、后端全546项通过（1项既有Starlette弃用警告），git diff --check通过；含真实本机监听占用且监听不受影响、范围耗尽/环回/非法参数/权限错误/启动顺序/后续失败无重试，非真实VM新版验收。P5六项冻结源SHA重新匹配，API80171/scheduler81383/恢复Worker25312在线；004介入记录单独0600保存，不提交.runtime。启动前失败的自动终态衔接、冻结新版真实回归及日报兼容仍待，旧失败不变。

P6正式入口三例004（2026-10-04）：host/guest冻结5c54fda，manifest 99c75f256de921be749cc961022193ca755aa60956e38720fb2867f74910156a，独立服务18103。英文f0983af3、混合f6a01972各SUCCEEDED/11raw，实际token分别397404、396955，费用未知；独立SSH重读原文件哈希、停止后零派发、官方会话/下载一致。中文add9b64c在tunnel-port-preflight报errno48，未尝试guest启动，0raw/session为空/usage未知；原过期执行权收尾为BLOCKED/OWNER_LEASE_EXPIRED，不改成功。核对原guest目录不存在、配置不变、VM共享锁可用后，隔离可恢复归档，未重跑失败。P5 Worker依次23877→24872→24970→25312，API80171及scheduler81383未改。本轮2/3，P6未验收；先提交固定范围控制端口选择方案，再实现测试，启动前失败的自动安全终态另待补齐。

P6读取缺失结果恢复规则（2026-10-04）：按593b981先行方案修三层契约。guest要求唯一成功write_result前的read_result仅允许真实FileNotFoundError，错误后必须有完整新观察；写后全部读均成功且内容一致，至少一个最终读回。real_app_verifier新增仅P6显式启用的allow_missing_result_read，原默认仍拒绝该失败；所有原调用/error保留并计数。host新增官方/guest全部读写顺序匹配、逐个read的唯一原结果及错误类型核对，不以通用官方错误文字或数量代替guest证据，报告recoveredMissingReads。

验证：相关48项/26子测试通过，随后补强“无新观察”反例避免由调用计数错误先行拒绝；执行层全190项通过，后端全532项通过，仅既有Starlette弃用警告。反例覆盖早期成功读取、PermissionError、UNKNOWN、重复/缺失结果、无新观察、写后读失败、缺最终读回、官方/guest状态或顺序不一致和额外官方调用。旧默认TextEdit仍拒绝新增只读失败，未修改budget/lease/执行工具。

原003中文任务的全部观察PNG/state、trace/final_state/文档/result通过SSH只读复制到新的missing-read-rule-review，四份先前留证原文件SHA完全一致。新规则本地inspect_guest_evidence为VERIFIED/11raw，原官方会话核验sessionVerified=true/recoveredMissingReads=1；原最后中文截图已查看，三行正确。原数据库再次确认仍UNVERIFIED/11raw/零产物，未重新prompt、未修改VM原证据或部署新guest；P5六冻结源码/profile不变。此仅离线同字节规则复核，不倒填003的2/3结果；README、后端及VM说明同步，新版真实回归、旧日报兼容及P6总结仍待完成。

P6同版三例003（2026-10-04 09:32—09:39北京时间）：按ae47829事前方案冻结host/guest ae47829e7eebad991e0d522099430a1a72a1064b，guest新目录manifest d0bff038220a37a09fb1b37ffaf282082f31729a251dfa592b7b27026f4c0f49，不覆盖c448ae2。独立API18102/PID22754和新数据库，旧002服务保留；三项先经正式client/API提交冻结，每例新查Codex77%/积分不变/卡未用和私有绑定记录，原Flash/off/30raw，未重复派发。

01 task31ae6a79-8975-4d11-9a69-2cf6ba2447d7/session-6b686777-370a-492d-9827-8533ab2ecd30成功，9raw/7官方工具/248513 total tokens。02 task33077a36-ea8b-486e-9fdb-5f9c3f9fddec/session-2e5ab1c0-eb8a-481e-baf0-dc9cb6749bd3为UNVERIFIED，11raw/395441 total；原GUI文档和result字节匹配，但raw8的read_result真实FileNotFoundError，raw9新观察、raw10首次写、raw11读回成功。原guest desktop_evidence:130把早期失败读也纳入“所有读晚于write”，且旧business verifier禁止非观察error、host仅允许写结果错误；先记录三层契约差异，未修改原任务/账本。03 taske5400ccb-5da0-4001-8129-735d2e82e01b/session-3749f523-e245-4ee8-a684-1f5e9ed79cc1成功，11raw/9官方工具/397544 total。三例合计31raw、1041498 token，货币费用未知；003整体2/3，不能称验收通过。

成功两例正式下载SHA/字节及独立SSH原文件、PNG/state、停止许可/停止后零派发、官方会话模型/工具/图片审计均通过，原最后截图已查看，英文和混合三行正确；标题仍显示Edited，实际保存文件另行逐字节核对，不把标题当文件证据。成功例frameworkNotices均0，不称真实触发了提醒修复。失败例新增failure-02-audit保留原文件SHA/错误和停止后零派发；原中文document SHA3bc9288cec7208b4007aed65e901562e0922a50df7d980bfd2e9a687bbdb46b9/result SHAdbf3373912d3a6ca40198e8ed6eefc5f4a632071d88ff417eb4db815176a5c31，与预定内容一致但不发交付产物。审计脚本一次无害Python正则转义SyntaxWarning留存，无验收异常或重跑。

每例恢复P5，Worker22627→23148→23452→23877，原API80171/scheduler81383未动；原profile与六冻结源码核对，无隔离。私有周观察目录记录全部切换和失败，不算用户实际采用。README同步，先补“写入前缺文件只读失败”方案再改代码；新版真实回归、旧日报兼容及P6总结仍待，目标保持未完成。

P6真实准备失败收尾诊断（2026-10-04 09:26北京时间）：按ea5d76e事前方案，在独立prepare-cleanup-live-001服务库/私有目录创建原任务7c57cfe0-c694-46f6-bb5e-ee33e25f8a97；host执行5be7615，guest沿用c448ae2和原manifest。当前Codex剩余77%、原积分不变/卡未用，任务/profile绑定私有记录五分钟内使用；P5空闲、下一正式计划12:10、六源码SHA/原profile一致，App会话空闲、VM已解锁。原P5 Worker20401单次TERM退出，API80171和scheduler81383未动。

原bootstrap真实启动guest PID28118（owner0b498e8c-d8d1-41d9-8059-6cab4bea89ba/epoch1）后，诊断程序只在tunnel.start前持有自己19097端口监听制造实际bind冲突；原tunnel.start抛errno48，未替换清理/Worker/guest响应。adapter实际通过SSH到guest loopback撤销并关闭，failure回执stage=tunnel-start/cleanupConfirmed=true；Worker独立核对原配置和清理证据后，原任务FAILED/DESKTOP_PREPARATION_FAILED、0raw、无session/产物、usage unavailable，无quarantine，profileUnchanged=true/restoreRequired=false。该故障为明确程序注入，不证明002原异常原因。

独立SSH读回原guest ready/停止lease，确认只有启动/许可文件，没有激活意图/trace/业务文件；原PID已退出，实际独立flock确认原guest共享锁可用。关闭自己注入socket后，原配置和P5六源码再次核对，App仍空闲，恢复P5 Worker22627并确认存活；P5私有周观察目录新增本次介入记录，不将程序读取算用户采用。原诊断失败和全部证据留.runtime/prepare-cleanup-live-001，不重建/补跑。此次无模型请求，未知用量不填零；不改变旧002失败、VM权限/网络/睡眠。README同步，仅提交脱敏记录；新版同版本三例、旧日报兼容核验及P6总结仍待完成，P6未验收。

P6准备失败有证据收尾（2026-10-04）：先提交395a7b4方案，再新增PreparationClosed只读证明及Worker分支。只有当前adapter原任务对象、本次清理已确认，且私有原guest启动/ready/cleanup意图与回执匹配run/owner/epoch、无App/profile应用/会话启动意图、当前profile与原before/plan SHA及字节一致才可返回证明。拒绝缺失、公开权限、链接、布尔冒充epoch/计数、额外清理字段、错误阶段及配置变化。Worker先停止并确认心跳线程退出，任何lost标记拒绝；再用原owner/epoch刷新停止态DB控制，由正常finish结束FAILED，已观察用户停止则STOPPED。无guest续权、App恢复动作、session登记或业务产物，用量仍unknown。

outcome使用profileUnchanged/appSwitchAttempted/restoreRequired明确区分“配置未变且没有切换、无需恢复”和“已执行恢复”，保存原profile SHA；不笼统声称整个环境没变化，准备文件及未启用插件副本仍保留。仅此正向证明路径避免创建新隔离；未知/失权/DB失败继续quarantine，不删除既有标记、不恢复P5，不改旧002失败。

验证：首轮相关59项通过；全后端523项通过（既有Starlette弃用警告）。随后最终状态字段细化按当前代码复核相关61项通过，含真实独立PG的FAILED/STOPPED、错误证明、缺失、过期owner、finish异常以及prepare期间心跳失权；没有真实VM/App/SSH或模型调用。git diff --check通过，P5原工作树干净。README和backend/README同步；真实VM故障收尾与新版固定业务回归、P6总结仍待完成，不将此本地验证当阶段验收。

P6准备失败收尾第二步（2026-10-04）：先提交050ed55细化方案，再新增desktop_prepare_cleanup/desktop_cleanup_protocol，复用原DesktopControlClient及bootstrap回执校验。adapter仅在已收到合法原ready后，遇到后续准备失败才关闭自有隧道并单次SSH清理原guest；固定普通VM身份/解释器，控制token只经有界stdin，未激活/无有效许可/零raw/零在途才撤销和关闭。原异常仍抛出，回执只保存固定字段，未知响应不重试，清理意图与确认独占0600。bootstrap未知或自有隧道关闭不明不启动后续清理；不按PID杀进程、不renew/activate、不自动重启P5或清除隔离。

验证：51项相关测试通过，包含真实本机loopback控制HTTP、原身份/有效许可拒绝、revoke或shutdown响应丢失不重试、非法回执/字段类型/额外字段、凭据仅stdin、私有意图与确认、原异常保留及清理失败。全后端497通过，仅既有Starlette弃用警告；使用原Python和独立cuagent_test_UUID数据库，不迁移P5库。开发时测试插入位置错误导致2个NameError、参数名request被pytest保留导致一次收集错误，均修正后重新执行；上轮时钟边界失败本次未复现，未修改相关生产或测试，不能算已修复。git diff --check通过，P5原工作树干净，无真实SSH/VM/模型操作。

本步仍保守保留Worker quarantine；cleanupConfirmed只说明原guest关闭确认，不等于App恢复、任务成功或可恢复P5。清理证据到有执行权的非成功终态衔接、真实VM失败收尾、新版同版本业务回归仍待完成；旧002状态和证据不变，P6未验收。README和backend/README已同步。

P6准备失败定位第一步（2026-10-04）：沿134ddff方案新增check_tunnel_port，adapter在bootstrap前保守检查固定loopback端口；隧道启动时仍再次检查并由SSH实际绑定/核对身份，不开启SO_REUSEADDR、不占用其他服务、不绕过冲突。新增私有desktop-prepare-failure.json记录阶段、固定错误类别、整数errno、启动意图/guest回执是否存在及cleanupConfirmed=false；不写外部异常文本/参数，原异常仍抛出，Worker隔离保持。覆盖真实本机监听冲突在guest启动前拒绝、监听不受影响，以及profile/bootstrap/tunnel三阶段含假凭据错误脱敏；14项专项通过，无真实VM或模型请求。

本轮全后端473通过/1失败：既有test_database_remaining_lifetime_caps_monotonic_deadline返回103.000536，超过断言103；该夹具以应用utcnow设置过期时刻，生产读取数据库clock_timestamp，存在跨时钟边界敏感性，尚未据此改生产/放宽测试。单独复核执行权模块11项通过，原失败保留，不能称本轮全量全绿。guest启动后失败自动清理、清理确认到Worker终态的契约仍待实现；本改动仅提前拒绝和留可追踪证据，不声称完整准备失败恢复。

P6结果快照修复（2026-10-04）：按134ddff先行方案，仅改desktop_evidence及对应测试。final_state保持原write_result时捕获的界面，要求它为写结果前最后一个完整观察、与write_result间无其他派发且≤30秒；仍晚于全部Save。write_result后仅允许成功的observe/read_result，所有成功观察必须一一具有原PNG/state哈希记录，后续观察额外核对正文/PID/window，不忽略尾部证据、拒绝再次编辑/保存或观察失败。新增7项测试含写后读前观察、读后观察、改正文/窗口/PID、缺记录/改图、尾部写动作、结果快照来自写后或过期。首轮测试因新增方法插入原用例中间出现NameError，修正测试布局后执行层全188通过；后端全470通过（既有Starlette弃用提示）。

将002首例VM原trace/final_state/文档/result及账本引用的原PNG/state只读采集到新的私有snapshot-rule-review；四份已留证文件SHA与原失败复核一致，新核验vmStatus=VERIFIED/12raw。此仅离线规则复核，原数据库任务仍UNVERIFIED，无新模型调用、无产物登记、未部署新guest。P5六冻结源码SHA不变。本机独立随机loopback端口复现连接关闭后无SO_REUSEADDR的bind返回errno48，但002第三例原异常缺失，仍不能定因；准备阶段预检/失败回执及安全清理留待下一步。

P6 cohort002真实执行（2026-10-04 08:39—08:49北京时间）：宿主已解锁，助手经原屏幕共享和既有测试凭据解锁VM，SSH确认IOConsoleLocked=No，不改锁屏策略。每例重新查询Codex剩余79%、原积分不变/重置卡未用，使用任务/profile绑定私有记录，原冻结host c2d74a3执行源码与guest c448ae2不变。三例未重建、无重复prompt。

01 task726fe85f-7219-47a1-a9c3-0eb7baf6c897/session-6fd59ec2-50d4-41c3-8ee8-9195e5820f05为UNVERIFIED，12raw、475241 total tokens，无交付产物；原文档/result逐字节正确、停止后零派发。SSH只读运行原核验器定位desktop_evidence.py:119：write_result时保存的final_state仍为s0000005a，read_result后多一次observe产生s0000005b，违反“最后观察”要求；不是额外用户prompt问题。原证据和失败保留，不重新归类成功。02 task8a18161f-c28d-4993-9556-a176280fad4e/session-ac22cdf3-c713-477f-99b5-5a45ee6b1675为SUCCEEDED，13raw/11工具、575847 total tokens；中文文档72字节/result73字节下载与原输入一致，独立重读VM原文件SHA/账本、官方Flash/off策略、PNG正文通过，本例frameworkNotices=0，不能称提醒修复已被真实触发验证。

03 task3797c39e-bc69-4b44-8a11-9c0822ab21a3在prepare阶段隔离，0raw/无session、usage未知；已取得guest私有回执但没有隧道/create/prompt/profile-apply意图，原异常未保存，端口复用仅待验证假设。在原共享锁内核对全部App会话空闲、profile原字节未变，经SSH原控制端口核对guest PID/绑定、inactive/modelPort=null/0raw/零在途/无activation意图，再单次revoke和shutdown确认closed。原DB执行权过期后正常claim清理为BLOCKED/OWNER_LEASE_EXPIRED，不领取替代任务；已审查quarantine移动到私有failure-03-recovery留存，非删除。P5 Worker依次6662→19426→19843→20401，原API80171/scheduler81383保持；完整独立汇总1成功/1未验证/1阻塞，不计P6通过。新增技术方案先于后续修复，无新部署或替代cohort。

P6提醒修复版002准备（2026-10-03 23:37—23:40北京时间）：方案c2d74a3先提交；旧001第三例通过原API停止并查询确认STOPPED、0raw、无session/产物，前两例保持成功/失败历史。确认旧P6 API5661身份后TERM关闭，保留原库与私有证据。公开init/serve创建独立002库，API7756使用18100；client提交原三组正文，冻结host c2d74a3854408896cf9f7ff82fe711c08a017bd1、guest c448ae2、全部执行源码与正文SHA及任务ID。新三例分别726fe85f-7219-47a1-a9c3-0eb7baf6c897、8a18161f-c28d-4993-9556-a176280fad4e、3797c39e-bc69-4b44-8a11-9c0822ab21a3，查询均QUEUED/0raw/无session，未调用模型、未生成额度许可。

前检宿主/VM ioreg均IOConsoleLocked=Yes，CUA屏幕共享cgWindowNotFound，桌面枚举亦无可见窗口，无法用已有测试凭据解锁VM；未尝试宿主密码或改变锁屏策略。原P5 Worker6662/API80171/scheduler81383仍在线，数据库活动任务0/资源owner为空，原计划ACTIVE/下次北京时间10月4日12:10；六冻结源码SHA、原App profile字节不变，无host quarantine。私有0600 preflight-001.json保留本次状态与旧任务停止介入；本次没有P5停启。待宿主桌面恢复后继续同一002任务，不新建替代样本，P6与总目标未完成。

P6官方提醒分类修复（2026-10-03）：先按966a9f9方案区分用户prompt与已审查框架notice；ba25d33另明确取消attempt的未知用量保护。新增P6专用JS/Python分类器及共享desktop-notices.json：只认五工具、默认3/5/8阈值、kind/form/summary、固定提示全文及前序已完成同名同参数调用链，拒绝来源/文本/计数/顺序/配对伪造和重复提醒；真实额外用户消息仍计数，原rpcId与唯一prompt条件不变。详细提示按UTF-16的500单位预览与原模板核对，原会话所有行保留；未改P5冻结daily-report-runner或关闭官方插件。模板来源参考639ed015的repeat-tool-reminder，MIT完整许可及THIRD_PARTY_NOTICES同步。

真实旧失败只读复核：原session-a62d893b-e7cf-48cc-b5f0-39834e0861c5在新分类下正确识别userMessages=1/rawUserMessages=2/frameworkNotices=1，仍为aborted/user。原JSONL完整SHA be9a0447d0128cb08d6de594cd64964393f6e327b9af7406b71e1e09bb49fda9不变，经正式inspect归档与恢复前快照逐字节一致；Python分类相同。原task仍BLOCKED/11raw/无产物，未prompt、未恢复执行。由于末尾assistant/attempt无完整usage，P6用量读取新增保守拒绝，保持available=false/null，不把此前消息合计当完整消费。

验证：跨语言正常/恶意来源、缺结果、不同参数、未知工具、重复/逆序、Unicode截断及第二条用户prompt反例；真实zstd归档完整保留提醒，Python独立验收报告提醒计数。后端全量470项通过；Node首轮112通过/1可选编译跳过，随后显式原固定build-tools全量113通过、零跳过。仅既有Starlette弃用提示，git diff --check通过；再次核对P5六文件SHA未变，README/后端说明同步。该修复尚未经新版本真实三例，repair-entry-cohort-001原失败与未执行样本不变；不能将离线分类修正冒充业务恢复或P6验收完成。

P6正式入口repair-entry-cohort-001（2026-10-03 23:03—23:15北京时间）：方案7373f07先行，执行源码bb812b6/冻结host7373f07、guest原c448ae2。真实desktop_service init/serve新库/18100，原API进程5661；公开client先提交并冻结全部三例ID/输入SHA/源码SHA，再逐例新查Codex额度80%、积分未变/卡未用。第一例task 0cea134f-9a59-4b84-8395-9daed13ac097，session-97898c76-e148-4bf1-86fa-e96553333e1e，SUCCEEDED，11raw/9官方工具、392188 total tokens；公开CLI下载document/result逐字节符合原输入，独立重读VM全部原文件SHA、观察PNG/state及账本前缀、官方会话策略再次通过，停止后零派发。P5 Worker3522→6135，App原字节恢复。

第二例task 33af564e-6abe-438a-b008-501ab5495b39，session-a62d893b-e7cf-48cc-b5f0-39834e0861c5，11raw后触发隔离。原会话9次工具中最后三次vm_observe相同参数，官方repeat-tool-reminder产生source.kind=repeat-tool-reminder/form=notice/summary="vm_observe × 3"的user/message（seq61），不是第二次prompt。P6按user/message总行数≤1校验因此拒绝并取消；终态归档又因“terminal evidence must belong to the one original prompt”拒绝。原prompt唯一、取消后aborted/user，guest撤销/零在途、原账本停止后零派发已独立核对。未补prompt、未改成功；完整usage仍unknown，原9条assistant消息及末尾assistant/attempt原文私有保留。

在原共享锁内独立确认所有官方会话空闲、原guest已停止/零在途后，调用既有App/profile恢复及guest shutdown（closed=true），核对原profile完整字节相同；确认原隧道PID6192身份后关闭，仅将该任务的已审查host quarantine移入私有failure-02-recovery留存。按原执行权过期清理将旧任务置BLOCKED/OWNER_LEASE_EXPIRED，无新领取/产物；P5 Worker恢复6662，API80171/scheduler81383未停。第三例bae7cc9c-0df2-4958-9911-638298ac8717仍QUEUED，零raw/无session，未执行。原P5六个冻结源码SHA未变，原三例旧失败与本cohort分开保留。独立partial audit结论为1成功、1失败、1未执行，不能记3/3或完成P6。下一步仅修P6对已审查官方提醒的消息分类，先反例测试再新版本回归，不关闭安全提醒或修改冻结P5源码。

P6单任务执行入口（2026-10-03）：方案a8c9d73先于实现，新增backend.desktop_operator worker-once。任务/私有profile原SHA/新鲜Codex额度严格绑定，五分钟内普通额度≥40%、积分基准不变且卡未用；真实触线在原共享运行目录持久锁止，禁止靠重置或换独立服务解除。原P5停止锁同样拒绝。原共享锁内先准入再按精确task ID领取，旧默认claim不变；无任务/非排队/已有attempt或启动意图拒绝，不换样本、不自动续批。LiveGate查真实PG原队列/资源/临近计划、旧Worker进程、SSH只读VM身份和解锁状态，原adapter在准备/切换/prompt前重复核对；启动器不自动停启P5、部署或解锁，仍需已授权窗口。独立操作意图/拒绝/结果留0600回执，模型执行仍是原Flash/off和30raw链路。

验证：新增31项，隔离PG精确领取/前置拒绝零attempt、共享锁内准入、同任务单次组合、绑定/过期/40%边界/持久停止、P5在途/资源/临近计划/旧Worker和锁屏拒绝。SSH/VM/App边界在本轮模拟，不能称新入口真实模型通过；现有原adapter重复gate测试另保留。初跑一项新计划夹具缺last_commit，被数据库NOT NULL拒绝，修正夹具后后端全量451项通过（仅既有Starlette弃用提示）；CLI帮助及git diff --check通过。现场只读确认原build-tools为0755公开依赖目录，按当前用户所有且无组/他人写权限验证，不更改其权限；App home仍要求私有。P5原API80171/Worker3522/scheduler81383未改，本轮零模型/VM调用。README/后端说明已同步。下一步经正式独立API/CLI/worker-once冻结新修复版三例并实际验收，保留全部原失败；P6及总目标均未完成。

P6独立队列服务入口（2026-10-03）：方案f695d41先行，新增backend.desktop_service init/serve。显式私有baseline-env、全新cuagent_p6_service_UUID库及独立token，迁移仅新库；根目录必须独立、私有且不覆盖已有目录，失败保留初始化意图。serve固定127.0.0.1/18100–18999，端口占用拒绝，禁止日报/批次/定时/resume写入。client新增显式--desktop-service，省略仍走原环境/18089。新增12项测试，含真实临时PG创建/迁移、真实uvicorn进程/HTTP/独立CLI提交、重启保留原ID、同键去重、排队停止零raw/session、错误认证/配置/权限/链接/重复字段/占用端口拒绝；临时数据库和进程由测试仅清理自身实例。专项28项、后端全量420项通过（既有Starlette弃用警告）；git diff --check通过。未启动常驻P6实例、模型或VM，P5原API80171/Worker3522/scheduler81383仍在线。README与命令说明同步。此交付为完整入口的队列侧，受控单任务Worker启动器和同版三例仍待接通；P6未验收，不把QUEUED当业务成功。

P6桌面提交CLI（2026-10-03）：先提交方案d218371，再新增desktop-submit --spec --key。普通UTF-8 JSON有界读取，拒绝链接/目录/FIFO、重复字段、未知字段、非法正文和非法幂等键；仅单次POST原/desktop-tasks，未知响应不重试。新增客户端经原FastAPI/独立PostgreSQL测试，覆盖中文、同键同任务、改正文冲突、排队停止零调用、默认503和本地拒绝零POST。后端全量404项通过；随后补4项非法/缺失键反例，提交CLI专项16项通过（全量404执行时尚无这4项，不冒称全量408）。仅既有Starlette弃用提示。README及后端示例同步；当前客户端仍固定18089，未启用生产桌面API或启动新Worker，未调用模型/VM，P5服务不改。独立服务启动入口、同版完整三例及P6验收总结仍待完成。

P6真实HTTP拒绝与数据库失权（2026-10-03 22:17—22:24北京时间）：先提交a21a29d/63eee5f两方案。系统curl只读探测可收到VM SSH响应，随后原生产模型HTTP GET405确认连通；不修改网络/TCC或推断旧EHOSTUNREACH根因。boundary-live-003原run p2-85bfc346-bf7e-40dd-b2e7-34034dc60e34，c448ae2 guest，真实观察3raw→缺参输入拒绝4→旧snapshot保存拒绝5→新观察6；无type_text/hotkey派发，原两个state/PNG及完整调用配对核对，revoke后observe409/预算6不增，直接guest renew拒绝，不以客户端预检冒充。guest关闭、P5 Worker恢复3328。原001/002连接失败保留。

authority-live-001在数据库创建/Worker停启前因VM仍锁屏拒绝，零派发；重新聚焦屏幕共享并用原测试凭据解锁，保留该前置失败。authority-live-002独立数据库/API提交task 458ee3e4-ad5a-4f27-910c-f727553ac374，真实TaskService领取及DesktopExecutionControl经SSH授予原guest；一次实际观察3raw后，仅在诊断库把desktop资源expires_at改为已过期。未经替换的refresh由数据库拒绝，自动localRevoked/guestRevoked，原HTTP observe409且仍3；原owner heartbeat/authority和重建control都拒绝，guest sequence仍2。正常claim清理登记BLOCKED/OWNER_LEASE_EXPIRED，resume拒绝、无产物/无官方session；未调用finish假成功。独立重读数据库、原PNG/state/终止后trace前缀和许可一致，零停止后派发。guest关闭零在途，P5 Worker恢复3522，API80171/scheduler81383保留，原DSH配置SHA与此前一致。两诊断均零模型调用，Codex剩余82%、积分未变/卡未用；不冒充官方模型取消或完整Worker失权故障。后端执行控制/Worker34项通过（隔离临时PG），HTTP11项本地测试通过。P6完整同版三例与实际可用入口仍待收口，不能把已有跨版本结果拼成3/3。

P6真实VM自然到期（2026-10-03 22:11北京时间）：方案5d65408先于诊断实现dc5eeb7。新增desktop_expiry_live，沿用prepare_guest、原bridge.lock、DesktopTask/Driver及生产许可门禁，不增加模型能力或改网络权限。助手经原测试凭据解锁VM；最新Codex剩余82%、积分基准不变、重置卡未用。独立确认P5队列/App空闲后临时停止Worker2406并持原宿主锁；guest运行c448ae2已部署源码，执行前重新核对manifest及所有文件SHA。run p2-f482c002-c4de-41fe-8466-ee7c304555eb实际launch_app/list_windows/get_window_state共3raw，snapshot s00000049；许可于1791036690068ms自然到期，1791036690108ms尝试observe在派发前拒绝，预算仍3。原controller及同文件重新构造的controller续期均拒绝、stopped持久为true；runtime关闭且零在途，P5 Worker恢复3122，原DSH profile字节不变，API80171/scheduler81383保留。私有expiry-live-001的原trace SHA83911cdb743230589451248ed81253827a4d74526798fe2c115d2a74979dec6c、原state/PNG与观察摘要、完整三对调用及到期/停止后零派发独立核对通过。零模型调用、无正文输入/保存（仅原桥接创建空测试文档），业务UNVERIFIED；这是VM最终门禁及持久许可诊断，不冒充HTTP/App/DB失权全链路。新增4项诊断反例，本地执行层181项通过；原失败保留，拒绝边界及完整同版业务回归仍未完成。

停止修正后回归：后端392项通过（独立临时PG库），VM本地177项及36子测试通过；只有既有Starlette测试客户端弃用提示。P5只读复核活动任务0、原profile逐字节恢复、API80171/scheduler81383/Worker2406在线。

P6真实停止（2026-10-03 21:57北京时间）：方案d2ca8cb→实现0f22590；同目录原STOP_REQUESTED仅在原会话terminal、guestStopped、零在途、撤销确认与DB原owner/epoch仍有效时finish STOPPED；缺证明/失权仍隔离。23项Worker测试通过，另修异常后不能沿用旧terminal标记恢复。stop-live-001独立PG/API创建排队任务并停止，session=null、budget=0；运行任务96a428f3-5f49-4ed6-82a2-bbac5481f273，首次观察3raw后API于1791035821.1804512返回STOP_REQUESTED，guest于1791035822.912292记录stop，约1.73秒；全轨迹3raw且stop后无dispatch，原官方会话aborted/user，最终STOPPED无产物、无quarantine、恢复成功。完整usage缺失保留null，原第一段已报告907 token，不据此估算完整消耗。宿主0f22590/guest c448ae2，P5 Worker恢复2406。真实失权、拒绝边界及完整同版业务回归未完成，不将这次停止测试替代业务成功。

P6修复版后两例与诊断失败（2026-10-03 21:45—21:51北京时间）：c448ae2已部署并经bootstrap校验源SHA。formal-02 task a6c62d4b-6b7d-4b9e-9d14-3276ba271305、session-466fd59c-f4e3-4755-b894-6d01a077f8fc，中文正文通过，11raw/9官方工具、381031 total token。formal-03 task fcf3d0c1-5f13-45a7-a337-111586f46faf，混合文本通过、382833 total token；两例独立核对和API下载均通过，Flash/off，原profile恢复且P5 Worker1981在线。formal-01失败未改，跨版本结果不拼成同版3/3。boundary-live-001的Python直连报No route to host，002的Node直连亦未确认；两次shutdown均closed且rawCalls=0，未重发原请求、未改网络/隐私权限，不算真实边界通过。增加真实本地HTTP/模拟Driver的旧snapshot拒绝反例，与lease相关19测试/10子测试通过。真实停止、失权、拒绝边界和完整同版业务回归仍未完成。

P6真实闭环与正式首例失败（2026-10-03 21:38—21:44北京时间）：807c18a的live-005原task 482c1796-5465-41c1-99f2-01e1441228da、session-84203498-e434-49bc-8641-705b7a77099c通过；9次官方工具/11raw，独立VM与官方会话核对、ASGI下载SHA均通过（不是部署新HTTP服务），375305 total token，Flash/off。App/profile/guest/隧道恢复成功。固定formal-01 task f859f7bb-4791-4a88-8a7e-9a00bafdbe50为UNVERIFIED，14raw、617445 total token；观察s0000003e→拒绝输入→沿用旧观察Save，guest verifier第115行拒绝。原失败不覆盖、不重跑，formal-02/03未执行。方案38287ec后仅P6拒绝路径清空snapshot，保留原计数/审计；176执行层测试及36子测试通过。P5原Worker恢复为1026；待新版本真实拒绝边界、正式用例及停止/执行权验收，P6与总目标均未完成。

P6修正回归与当前边界（2026-10-03）：后端386通过（独立临时PG库）、VM本地174及36子测试通过、Node99通过（真实本地编译，无模型）。补官方V4元数据身份反例、格式恢复/语义变化拒绝、preset存在但工具未就绪拒绝；TextEdit请求必须五工具完整才进入provider。live-004在任何VM部署/停Worker之前被VM锁屏检查拒绝；进一步ioreg确认宿主zhangchengjie和guest mvpagent均锁屏，CUA屏幕共享返回cgWindowNotFound，因此无法通过已授权VM凭据自行解锁。未读取宿主密码、未改锁屏/睡眠策略。P5 API80171、scheduler81383、Worker93912在线，活动任务0，原profile逐字节相同，计划ACTIVE且下次2026-10-04 12:10北京时间。live-003用量另存核对记录303 token，旧unknown/失败不覆盖，恢复隔离标记仍保留供后续持锁复核。P6三组正式用例/真实停止与执行权测试仍待运行；未用mock冒充完成。

P6真实首次失败与恢复（2026-10-03）：按追加授权自行解锁测试VM，保留known-hosts权限/共享锁目录/guest旧空锁等前置失败。live-003首次真实Flash/off请求输入267+输出36=303 token，VM raw=0，UNVERIFIED，不替换为成功。App重排YAML使原严格字节恢复拒绝；在App已停、语义一致和摘要复核后保存原现场字节、恢复原profile，关闭已撤销guest及其隧道，恢复P5 Worker93912和原preset。修正V4首行元数据解析（原unknown不覆盖）、语义等同格式恢复、profile范围插件安装和五工具ready门禁；Python19、Node17相关测试通过。修复后真实验收未完成，公开API默认关闭，七日P5计划未取消。

P6真实窗口授权与现场阻断（2026-10-03）：用户明确回复“允许”临时停旧Worker、切换App测试并恢复，不取消P5调度。实时Codex额度used15%/remaining85%、ordinaryUsageAllowed=true，积分仍62494.0260570000、1张重置卡仍可用，未使用；另通过官方DSH界面只读查询API余额¥13.20，确认两种额度不可混用。官方RPC列出241会话且running0。真实SSH只读检查身份mvpagent、hw.model=VirtualMac2,1、CuaDriver serve PID602在线；ioreg显示IOConsoleLocked=true且mvpagent会话CGSSessionScreenIsLocked=true，故前置失败停止。没有停止P5进程、部署VM、切换配置或调用模型；用户需解锁VM桌面后重查再执行，既有窗口批准不需重复索取。P6真实验收仍未完成。

P6桌面用量统计（2026-10-03）：方案459ce9a先于实现。验收核对发现adapter未交付usage，新增desktop_usage只读私有原session归档、固定run/session/cwd、64MiB限制与单终态/序号检查；全部assistant用量字段须非负整数且总量一致，保留模型路由与原文件SHA，缺失/异常明确available=false、token=null、费用未知。adapter提供usage，Worker成功/UNVERIFIED向既有finish写usage；UNKNOWN只在私有outcome保留，不为了记账改变停止/锁/隔离决策。新增10项原会话合成测试和3项隔离PG生命周期测试，相关29/29通过、git diff --check通过，无模型/VM/App调用。真实环境切换批准仍未收到，P6未验收；没有以记账结果代替额度检查或GUI验收。

P6 SSH标准输入修复（2026-10-03）：方案9528da9先于实现。新增desktop_ssh.create_ssh_wrapper，私有规范root/known-hosts/可执行askpass，独占0700脚本；固定/bin/sh与/usr/bin/ssh、VM身份、严格主机密钥、禁止更新known-hosts、认证超时，保留stdin。凭证文件只引用路径，不读取或复制；保留旧P5 vm-ssh。DesktopAdapterSettings改为显式known_hosts/askpass，prepare生成本次wrapper，bootstrap/隧道/collect共用该路径。5项新增测试覆盖真实子进程1MiB二进制往返和完整参数/环境、路径含空格引号、真实ssh -G离线解析确认固定主机/认证/stdinnull=no、重复创建及不安全路径拒绝；相关42/42通过。未连接VM或启动模型/App，部署调用者需先用生成器生成私有wrapper再传deploy_guest；真实门禁/切换窗口/端到端仍待完成，不称P6验收。

P6执行适配器组合与全阶段心跳（2026-10-03）：方案5181431先于实现。新增DesktopTaskAdapter，显式路径/部署版本/切换批准与必需的实时外部门禁；组合profile准备、guest bootstrap/隧道、空闲App切换、实时DB授权、唯一官方会话、撤销后可信证据采集及独立核验，交付只复制已核验VM原文件。恢复原App后可信shutdown关闭guest再关闭自有隧道；shutdown需控制角色、已停止及零在途。Worker在prepare前启动心跳，终态撤销后切换为仅DB续期，核验期间保持host停止标志且不再续guest，finish与心跳互斥；准备期间停止禁止启动。Python全量528/528及36个subtests、Node96/96通过；随后新增关闭权限/在途拒绝和准备时停止反例，相关23/23通过。1项既有Starlette弃用警告。全部为本地HTTP/模拟边界/隔离PG，无实际模型/VM/App切换，P5原工作树干净。额外只读发现原vm-ssh将stdin重定向/dev/null，部署与导出依赖stdin，必须另建受审查的新传输方案，不能直接复用或修改P5脚本。外部真实门禁、真实SSH传输和VM/App验收仍待完成，桌面API默认关闭、P6未验收。

P6官方App有界生命周期（2026-10-03）：方案794c182先于实现，新增desktop-app模块/命令，复用官方RPC不重写循环。stop两次核对所有会话running=false，保存原preset清单，核对唯一官方PID与ps可执行路径，意图先落盘仅TERM一次；10秒观察未确认则失败，不强杀/重发。start要求无原App、版本0.2.0-rc.2、明确home与本次profile回执及当前SHA；P6仅私有绑定连接/审计路径，恢复验证原A1 tasks并从activate前快照取原预置，显式open环境并清空另一模式变量。先存启动意图，45秒RPC窗口内精确preset/唯一进程/profile哈希才回执，忙碌/错preset不视为网络等待，失败不重启。新增6项系统命令/RPC模拟测试覆盖完整启停恢复、忙碌/错PID/版本拒绝、TERM超时与启动错preset不重放；Node全96/96通过（含原profile真实编译临时测试），git diff --check通过。没有实际终止/启动App、没有模型/VM/P5环境操作；上层共享锁/旧领取者停派与整体adapter仍需接通，真实端到端未验收。

P6独立profile事务（2026-10-03）：先提交方案a7edc38，再新增desktop-profile模块/命令。显式root/home/build-tools，不沿用旧脚本.runtime推导；读取已有工具依赖不改它，固定esbuild 0.28.1、仅构建c0-vm-tools和desktop-tool-scope至私有run，按原real-app模板合并受控条目、保留不相关配置，原/候选字节和SHA独占保存。prepare不改official home；apply/restore要求官方App进程不存在（pgrep仅退出1视为已停），profile目录独占锁，固定home/run/目标路径、核对原/候选/插件SHA，外部修改拒绝覆盖；意图fsync、临时私有文件原子替换、回执保留，restore原字节，不自动启停App。构建期间原配置改变也拒绝。8项新增测试含真实固定编译器读取原依赖、临时配置构建/切换/恢复，以及运行中App/外部改动/锁/跨home/插件变化拒绝；Node全量90/90通过、0跳过，git diff --check通过。原P5工作树仍干净，未触碰其配置/服务/凭证或实际App；上层生命周期、整体adapter与真实端到端仍待完成，P6未验收。

P6会话独立策略验收（2026-10-03）：核对旧real-app控制脚本、start-c0-desktop/configure/build后确认其绑定原.runtime，不能直接在独立P6运行或误改P5；现有会话查询也只证明终态，不能代替模型策略验收。先提交方案e1acff7，再新增desktop_verify。私有有界读取绑定/原prompt/原JSONL/请求审计，核对唯一原用户提示与completed终态、严格顺序/配对、全部header Flash/off与五工具精确范围；唯一vm_type正文及snapshot/SHA和guest输入对应，Save snapshot序列对应guest记录，完整result读回匹配。只允许与guest rejected_write_result数量一致的写结果拒绝，其他工具错误拒绝；observe有图片且请求审计有imageBlocks>0，不将图片存在说成模型正确视觉理解。返回sessionVerified报告但无整体成功状态，guest GUI/PNG/文件和可信来源仍为独立必要门槛。新增13项合成反例，相关26/26通过，git diff --check通过；没有实际App/RPC/模型调用。真实格式、图片关联和整体profile/adapter仍需端到端核验，P6未完成，P5未改。

P6 guest启动准备（2026-10-03）：方案4aafa76先于实现，新增宿主backend.desktop_bootstrap与独立VM bootstrap脚本。宿主固定身份/commit/manifestSHA与私有路径，先独占启动意图，再单次SSH/Python传送审查脚本，输出≤4KiB/25秒；新凭证回执仅0600写guest-private-receipt.json。guest先普通mvpagent/VirtualMac检查，私有manifest与逐文件SHA复核，再独占新建P6Launch/run.log并Popen固定desktop_guest入口；不构造Task、不授权GUI/模型。最多10秒等待原ready/私有token，绑定run/owner/epoch、自有PID、loopback控制口、固定模型URL；缺/部分ready只读等候，未知不重启也不猜PID杀进程。宿主再次校验回执字段及token角色分离，错误原件保留、意图阻止重发。9项新增测试覆盖模拟guest就绪、源码篡改零启动、超时不重启、私有凭证保存及五类异常回执；相关40/40通过、git diff --check通过。未实际连接SSH或启动VM服务，完整adapter/profile/官方会话独立验收与交付仍待组合，P5未改。

P6 Python官方会话适配（2026-10-03）：方案5a3e7db先于实现，新增DesktopSessionClient，私有root/home/cookie及固定run/session校验，显式可信Node与仓库固定desktop-session-command.mjs；prepare只独占保存请求/正文，不复制凭证或激活profile。start/cancel各写Python侧意图与回执、单次有界进程调用；start严格同session/accepted/Flash-off，inspect严格exists/running/terminal/原prompt唯一性，poll融合guest实际rawCalls/pendingCalls，取消只报告请求不宣称终止或回滚。13项新增模拟官方命令测试覆盖冻结输入/固定入口、重复启动/未知响应、错模型/身份、终态字段/布尔混淆、guest预算与取消不重放；相关21项通过，后端全量327/327通过（1项既有Starlette弃用提示），git diff --check通过。另以真实Node只读导入DAILY_MODEL确认Python常量与官方适配一致，未发RPC或调用模型。整体生产adapter仍需组合guest启动/profile切换/会话验证及交付，P6未验收，原P5工作树干净、环境未改。

P6固定源码部署（2026-10-03）：方案53f6e06先于实现，新增backend/desktop_deploy与独立guest desktop_install。已核对14个VM模块的本地导入闭包，另携带Cua来源许可证；打包仅git show显式40位commit文件，不读脏工作树，≤1MiB、逐项base64/SHA。安装器独立先核对mvpagent/VirtualMac/home，再验证完整白名单/大小/SHA并compile语法（不执行）；最后独占新建CUAgent-p6-commit，0600/fsync文件和清单。已有/部分目录拒绝重用，不删旧版本。宿主写独占部署意图、固定SSH/Python单发、限制4KiB回执/45秒，核对目录与清单SHA，未确认不重试；run_bounded默认32KiB输入不变，仅部署显式上调至1MiB。新增10项测试含真实临时目录安装、不执行源码、无效包零写入、固定commit读取、单次回执/不重放及宿主拒绝；相关63/63通过，git diff --check通过。没有实际VM写入/SSH连接/模型调用，真实部署及执行adapter仍待接通，P5未改。

P6可信SSH采集代码（2026-10-03）：方案99158a0先于实现。新增desktop_collect，固定已记录guest Python路径、CUAgent-p6-40位commit部署目录和desktop_export.py，身份来自控制客户端，正文来自DesktopSubmission；不接受任务自定义命令/路径。采集前后检查stopped、零在途、许可已撤销/不变、rawCalls不变；启动意图独占fsync，不重复采集。SSH包装器私有规范路径，-F /dev/null、禁额外转发/agent/X11/连接复用；无本地shell，远端固定argv shlex.quote。选择器双向非阻塞I/O，stdin≤32KiB、stdout≤65MiB/45秒，stderr不输出；异常TERM后限时KILL自有进程，完整传输0600独占保存guest-evidence.tar后再调用decoder，拒绝包保留原件，不落业务产物。新增8项测试含真实本机32KiB往返、输出超限/超时/非零退出及模拟SSH的固定命令、不重放、危险路径/在途拒绝、失败包留存、采集后状态变化。相关53/53通过、git diff --check通过；没有真实SSH/VM/模型调用，不等于通道或GUI验收。生产部署版本核验、官方会话与交付adapter尚待接通，P5未改。

P6后端证据包校验（2026-10-03）：方案170495d先于实现，新增desktop_bundle.decode_guest_bundle。仅处理可信收集通道提供的≤65MiB原tar字节，≤65个普通文件/单项≤8MiB/总内容≤64MiB，manifest≤64KiB；不落盘解压或执行内容。严格文件白名单、去重、无链接/特殊文件/PAX、完整零填充尾部；核对原run/owner/epoch及严格整数、冻结输入SHA、精确文件集合与各项SHA/大小，文档/result逐字节匹配，截图/状态成对。返回内存快照且sessionVerified=false、不含整体status；明确任意自洽包不证明来源或GUI，可信SSH与官方会话验收仍为必要条件。新增22项测试涵盖格式兼容（调用实际guest write_bundle）、身份/正文/摘要/布尔混淆、越界/重复/秘密文件、截断/附加内容、链接/特殊项、超大header及PAX拒绝；相关45/45通过，git diff --check通过。无真实SSH/VM/模型调用，P5未改；下一步需将实际采集/会话/交付接入adapter。

P6 guest只读导出（2026-10-03）：先提交方案d9aa154，再新增desktop_export.py。CLI先require_vm、绑定p2-UUID/owner/epoch，固定C0Evidence目录，stdin最多32KiB且只接受受控lines正文≤4096字节。许可必须固定绑定并已stopped，guest独立验证要求完整调用/PNG/文件轨迹；导出只接受trace/final_state/state-01..30.json/png/固定文档/result。二次O_NOFOLLOW有界读取与核验SHA/大小一致，原字节总≤64MiB，完成全部校验后才输出普通文件0600的USTAR及无凭证manifest；复查lease不变。没有解压到任意目录、没有业务文件写入；manifest明确sessionVerified=false。新增5项测试使用合成证据和真实内存tar，检查凭证排除、原字节、未撤销/缺许可、核验后篡改、额外路径及输入契约；执行层174/174通过，git diff --check通过。没有真实VM/SSH/模型调用，后端接收、实际adapter及完整验收尚待完成；P5未改。

P6控制隧道管理（2026-10-03）：方案883b121先于实现。只读核对原vm-ssh固定mvpagent@192.168.64.3、StrictHostKeyChecking和专用known-hosts；新增GuestControlTunnel校验私有规范wrapper/run、固定client绑定与端口。独占持久启动意图、单次Popen，-F /dev/null不继承用户SSH配置，仅-N/-T、显式127.0.0.1双端转发、ExitOnForwardFailure、禁agent/X11/ControlMaster复用。先检查端口占用，10秒内只读lease identity探测并确认子进程存活；错误身份立即失败，不以端口打开冒充guest就绪。错误/关闭只TERM自有句柄，2秒后必要时KILL，再2秒未确认报告失败；不替代远端revoke。新增6项模拟子进程测试，包含真实本机端口冲突、持久意图拒绝重启、身份不符、超时强制关闭、私有路径/链接拒绝。相关23项通过，git diff --check通过；本机ssh -G只读解析确认选项位于目标参数之后仍正确生效，无真实SSH连接/VM部署/模型调用。生产adapter、可信收集与端到端尚待完成，P5未改。

P6 VM命令入口（2026-10-03）：方案ebf9228先于实现。新增desktop_guest.py，身份检查require_vm位于所有写文件/监听之前，要求显式审批、p2-UUID/ownerUUID及正epoch；固定home/C0Evidence及原bridge.lock，新run独占创建。独立随机模型/控制token以0600写入，不接收命令行secret；ready仅绑定/控制端口/固定模型URL/PID，不含token，stdout固定就绪标记。准备不构造Task/不授予许可，SIGINT/SIGTERM/一小时上限撤销关入口；DesktopGuestRuntime若关闭时仍在途，会fsync持久quarantine，新P6实例拒绝且不自动清除。旧C0不识别该标记、SIGKILL/系统崩溃不在此保证内，生产禁止混跑旧版。新增5项测试核对宿主拒绝先于写入、参数/授权边界、真实loopback准备与私有输出、不复用、期限/异常清理、信号处理恢复；另扩展在途重建隔离测试。执行层169/169、后端相关17/17通过，git diff --check通过。测试替换VM身份检查，未构造真实桌面Task、未部署VM或调用模型；P5原工作树干净，生产adapter/隧道/可信收集与真实验收仍待完成。

P6后端guest启动/查询（2026-10-03）：先提交方案610f695，再扩展DesktopControlClient.status/activate。状态严格检查binding、布尔类型、端口、预算/在途数及调用数不回退；启动先读未激活零调用状态与有效guest许可，再实时authority确认执行权。对象内一次尝试且POST不重试，ACK要求当前执行权和保守guest期限仍有效、active且未停/零调用；未知结果交由Worker撤销/隔离，guest持久意图防跨进程重放。新增10项参数化用例覆盖真实loopback grant/activate/status/revoke、身份、缺许可、无效authority、丢ACK/迟ACK、异常状态与回退；Driver/环境模拟，无模型/VM操作。后端全量267通过（1项既有Starlette弃用提示）；随后补缺许可反例，相关客户端17项通过。git diff --check通过，生产adapter/launcher/可信收集和端到端未接通，P6未验收，P5环境未改。

P6 guest运行生命周期（2026-10-03）：先提交方案84c7b24，再新增DesktopGuestRuntime。构造仅持私有、显式共享bridge锁并绑定run/owner/epoch及独立token；不构造Task或开放模型端口。控制HTTP显式附加runtime后支持GET /status、空POST /activate，默认旧控制工厂行为不变；activate先独占fsync意图再检查许可、构造DesktopTask、启动模型服务，失败撤销并保留意图，跨重建不可重放。revoke持久撤销后stop，不等待Driver；状态区分端口活动、停止、真实调用数与在途数。close撤销/关入口后只有零在途才释放锁，未知状态保留锁待核对。6项新增本机HTTP/模拟环境测试覆盖grant→activate→原工具→status→revoke、无许可持久拒绝、凭证隔离、共享锁、绑定失败及在途保锁；执行层164/164通过，git diff --check通过。没有生产launcher、SSH部署、真实模型/VM操作；尚需后端客户端/实际adapter接入。P5原工作树仍干净，运行环境未改。

P6只读guest证据核验（2026-10-03）：方案6306d99先于实现。DesktopTask.observe在返回前绑定原state/PNG的SHA/大小、snapshot及实际调用序号，原响应与文件不一致或记录失败即stop。desktop_evidence独立读取私有固定run，拒绝链接/特殊文件/超限/任务混入、非有限或倒退时间、重复/不匹配/未完成调用、停止后派发和并发dispatch；验证账本引用的state/PNG原字节与哈希、当前输入/Save的观察来源、最后Save后的新观察和result完整读回，再复用旧业务核验器，复读trace检查收集期间变化。固定文件路径由序号构造，总读取≤64MiB；不构造Task、不发GUI、不生成业务文件。返回vmStatus=VERIFIED且sessionVerified=false，不能单凭此登记整体成功；源必须由未来可信收集通道提供，不防VM拥有者伪造整套记录。新增5项测试含多种合成反例，执行层158/158通过、git diff --check通过；原P5工作树仍干净，无真实模型或VM动作，官方会话绑定/Flash-off及端到端尚待接通。

P6模型工具HTTP（2026-10-03）：先提交方案2b249c8，再新增desktop_tools_http，复用原POST /与op/args协议，固定VM接口/宿主来源或显式loopback测试模式；仅接受DesktopTask，模型token不得与控制token相同，无verify/renew/通用Driver入口。32KiB有界正文、2秒读取、拒绝重复JSON字段/认证头/长度头、分块及额外字段；认证失败不耗预算，认证后的拒绝沿用审计与30次总预算，已经派发失败不重复计数。stop绕过任务串行锁，最终准入仍逐个内部请求检查许可。新增10项本机真实HTTP+模拟Driver测试，覆盖中途撤销、在途停止、预算耗尽、协议/凭证边界、中文最大正文透传；执行层完整153/153通过，git diff --check通过。未修改旧桥接、插件或P5原工作树（仍干净），无VM/模型调用；可信launcher、SSH通道、Worker实际适配与真实验收仍待完成。

P6官方会话证据与命令入口（2026-10-03）：先提交方案33bd977，再新增desktop-session-evidence/command。显式私有home与受控sessionId定位唯一原compressed文件，拒绝链接/重复/越界、只读有界读取≤64MiB，固定zstd 1.5.7解压≤64MiB/10秒，原JSONL字节保留；原prompt匹配且唯一用户消息/terminal才独占归档，已存证据变化拒绝覆盖。start/inspect/cancel CLI只调用已有官方会话模块，不部署/激活/授权VM；错误仅固定代码，不泄漏凭证。新增5项Node测试使用真实zstd压缩/解压合成事件，验证原字节、拒绝路径、非终态/错请求、旧证据不覆盖及命令参数；无新模型或真实App调用。后续Python adapter需接此命令、VM证据及配置激活，P6仍未验收；P5未改。

P6官方会话协议模块（2026-10-03）：方案15d6f97先于实现，新增agent/harness/desktop-session.mjs，复用日报runner的模型常量和observedSession解析，不改日报执行器。RPC固定127.0.0.1:19387、显式私有cookie、禁止重定向与副作用重试；start要求空闲App、唯一real-app preset、目录支持Flash/off，固定run/session/cwd和输入，create/model-select/prompt各先独占写意图再调用，响应另存。inspect核对原session/cwd及prompt request；cancel只针对running会话且单次意图，idle不取消。6项新增协议模拟覆盖成功/取消、create确认丢失、选模不符、prompt确认丢失、preset不符及越界输入，Node全77/77通过。没有HTTP实际连接到官方App、没有模型费用、没有profile切换；真实会话证据读取及VM/Worker适配仍待接入。P5源码和运行环境未改。

P6桌面Worker编排（2026-10-03）：先提交方案cdb814c及未知状态隔离细则70fa665，再新增独立desktop_worker。必须显式指定共享锁，锁后才领取desktop类型；准备run/session/control绑定，初次许可后独占写入并fsync启动意图，start只一次。3秒独立心跳，poll检查terminal/rawCalls/pending，最多300秒观察，停止/失权拒绝成功。终态且无在途、许可撤销确认后才独立verify并登记产物；取消前先关闭许可。未知状态不finish释放资源，写共享锁旁quarantine并阻止后续P6领取；配置恢复失败独立告警并隔离，不把业务成功当环境恢复成功。10项模拟adapter+隔离PG测试覆盖完整编排、准备/启动/撤销/在途/预算/停止六故障、验收失败、恢复失败及锁争用；全后端258/258通过（1项既有弃用提示）。追加启动意图持久写入后单独重跑Worker测试。尚无真实adapter、VM隧道或模型执行，不能声称生产可用；旧P5 Worker不识别新quarantine，真实切换仍必须停旧领取者，P5环境未改。

P6交付链路最终后端回归248/248通过（1项既有Starlette/httpx弃用提示）；没有真实桌面业务成功声明。

P6类型化产物交付（2026-10-03）：检查Worker发现finish/下载/通知硬编码日报文件，先提交方案c379b71，再补artifact_contract、桌面两产物完整性/kind/session/正文/状态检查、按类型下载媒体及CLI文件选择。通知改为只列已登记且符合类型的文件。首轮245通过/1失败：旧通知测试仅强设成功未建Artifact却期待两链接；补齐合成登记数据，并增加缺产物不生成链接反例，不修改生产证据。新增桌面交付合成测试覆盖缺项/额外项/跨类型/错会话/错SHA/错正文/链接/停止并发、下载后篡改拒绝；不是GUI真实性证明。无模型或VM调用、生产API仍不开放桌面提交；P5环境未改。

P6数据库authority联动（2026-10-03）：方案2da1553先于实现；TaskService.desktop_authority在短事务锁定资源/任务，校验运行类型/状态和同owner/epoch/task绑定，用数据库clock_timestamp计算剩余许可并保守映射monotonic截止。新增DesktopExecutionControl协调heartbeat、guest查询、新查authority、单次授权；异常后对象永久关闭、host许可停止并尝试guest撤销，分别保存localRevoked/guestRevoked，明确inflightCancellationConfirmed=false。11项新增隔离PG+真实loopback测试，包括停止联动、六类身份/类型/过期拒绝、短剩余期限、DB失败、网络不可达不伪造撤销、绑定错误；全后端237/237通过，1项既有弃用提示。并未修改旧日报Worker、接生产VM或创建模型任务；真实SSH通道、桌面Worker及端到端仍待完成。额度实时剩余89%，积分基准未变，重置卡未用。P5运行环境未改。

P6通信期限最终回归：后端226/226通过，执行层143/143通过；保留1项既有Starlette/httpx弃用提示。无生产部署或真实桌面授权。

P6后端控制客户端（2026-10-03）：先提交期限细则63a22f9，网络续期强制notAfterMs，guest到达已过期拒绝，expires取绝对截止与本地TTL较早者；同序号变期限拒绝。GET返回固定binding和guest时钟，客户端在任何修改前核对身份（包括尚无许可时），查时钟后调用可信authority拿monotonic执行权截止，扣查询耗时及500ms余量；HTTP修改只发送一次，校验响应身份/序号/截止，迟到ACK不报有效。7项客户端真实loopback测试通过：许可/撤销与门禁联动、迟到首授、权限失效/DB回调异常、身份/序号冲突、真实写入后ACK丢失无自动重发、ACK迟到、空guest错误绑定零修改。执行层143/143通过；后端中间完整225/225通过，最终新增空guest反例后再跑全量。所有测试均无模型、无VM；尚未接Worker数据库authority或SSH隧道，不能视为真实任务执行通过。P5运行环境未改。

P6独立控制HTTP（2026-10-03）：先提交细则eed0be9，再新增desktop_control_http服务工厂，只绑定127.0.0.1，独立控制token、固定任务身份；GET /lease、POST /renew或/revoke，≤4KiB请求、2秒读超时、拒绝分块/额外字段/错误凭证，不记录token或原始错误。新增5项真实loopback HTTP测试，含从续期到LeaseGate再撤销拒绝、重复序号原回执、错误角色/越权动作/过大请求/到期停止，执行层142/142通过。该测试实际使用本机socket，但不是VM/SSH或模型测试；网络入口尚无生产launcher、Worker时限绑定与延迟防护未接通，不可真实授权。P5服务/库/VM配置未改。

P6许可控制存储（2026-10-03）：先提交方案76d0da2，再新增desktop_control.LeaseController，复用门禁的私有有界文件读取；文件锁串行更新、0600临时文件和原子替换，固定run/owner/epoch，guest计时最长30秒。重复序号返回原记录不续期，乱序或变参拒绝；过期/时钟倒退持久停止，撤销可重复且可先于首次授权写入停止记录，防延迟授权复活。新增8项无模型测试，执行层137/137通过，含控制存储到最终LeaseGate的联动、并发、身份冲突、重建持久拒绝、符号链接和损坏记录。未增加网络服务或后端心跳集成、未调用VM/模型；P5目录、生产库和服务未改。后续必须实现独立认证控制通道并核对通信延迟/执行权期限，不能把guest文件存储称完整远程停止。

P6执行端准入（2026-10-03）：先提交门禁细则d24e224，新增独立desktop_lease.py，DesktopTask继承原RealAppTask，不改旧C0/C2/TextEdit实现。每次最终_admit前校验VM本地私有控制文件的run/owner/epoch、停止和≤30秒余期，拒绝链接/宽权限/特殊文件/过大或异常JSON/时钟回退；失败持久stop，即使0次派发也不能重启续用。新增6项测试（含多字段反例），VM执行层全129/129通过；均模拟传输，不是实际VM证据。后端到guest可信许可传递、远程停止确认、全局锁和真实执行适配仍待接通，不承诺取消已在途副作用。没有模型或VM调用、未更改P5环境。

P6队列接入（2026-10-03）：先提交细则8dbdf60，再新增默认关闭的POST /desktop-tasks（503且零建单）、认证/幂等/输入校验及TaskService类型过滤。旧日报正文和摘要不变，无kind仅日报领取，显式desktop-textedit仅对应领取者，未知/null类型不派发；两类竞争同一desktop资源。桌面排队停止零attempt、可重新排队，任何既有attempt/session/预算/运行证据均拒绝resume，尚无安全桌面恢复实现。新增9项隔离PG/API测试，全后端219/219通过，1项既有弃用警告；并发同键仅一个任务、跨类型竞争仅一个领取者、旧摘要和幂等均通过。没有数据库迁移、生产开关、模型或VM调用；P5原目录/服务不变。该结果不证明旧P5二进制可兼容新桌面队列，也不证明真实VM停止/执行权，真实适配和交付仍待完成。

P6首步完整回归：独立工作树执行后端210/210通过（既有176项+新增34项），1项既有Starlette/httpx弃用提示。使用原解释器和现有测试库创建权限，测试夹具新建独立临时PostgreSQL库并在结束后删除；不迁移或修改生产库、不调用模型。测试通过不代表新桌面任务已能执行。

P6开始（2026-10-03）：用户批准回顾后的计划并授权实施。自8bd099e建立p6-desktop-task-service独立工作树`/Users/zhangchengjie/CUAgent-p6`，先提交方案1513eda，再新增desktop_contract及34项输入/权限覆盖反例，单测34/34通过。契约仅允许desktop-textedit和1–10条单行文本，完整UTF-8正文含末尾换行≤4096字节；冻结不可变输入，拒绝控制字符/额外路径、工具、模型和预算字段，不生成业务文件、不开放新API。P5原工作树/配置/服务保持不动，未复制凭证、未调用模型或VM。类型化队列、实际执行权与停止、产物下载及真实闭环尚未实现，P6未验收。后续P7/P8方向已纳入路线，不提前扩权。

P5最新额度与观察频率调整（2026-10-03）：用户明确剩余额度至少40%可用，覆盖下方历史70%已用停止线。先提交方案21ca9e4，再将操作员门槛改为剩余≥40%，39.999%持久停止、40%可放行；不使用积分/重置卡，不清除已有停止记录。完整后端176/176通过（1项既有依赖弃用告警），没有新增DSH任务。原定时任务cuagent-p5已同步40%条件；今天偶数小时11分每2小时检查，明天首次唤醒时更新同一任务为00:11/06:11/12:11/18:11每6小时。模型批次仍每天12:10、总7批14任务，不增加模型频率；README和使用说明同步。七日观察仍未完成。

P5操作员入口收尾（2026-10-03）：用户要求将观察交给定时、同时继续推进。先提交方案4bd08de，再新增schedule_operator，使用私有有界记录/O_NOFOLLOW、文件锁、原子替换、不可覆盖回执；本次70%停止线持久锁止，拒绝自然重置后自动再授权，grant还要求原计划到期未发生。20项新增无模型反例，完整后端175/175；包括重复许可、并发、过期/未来/NaN/bool、其他计划撤销、停止后重启/重置、慢查询跨许可时限。真实CLI拒绝旧过期检查INVALID_ATTESTATION；最新查询剩余90%、积分未变/卡1张未用，对已发生首期返回NOT_AN_UNCLAIMED_DUE_OCCURRENCE；revoke返回REVOKED，均新回执留存于私有backend根目录。原正式计划仍1期、下一期10-04，六个冻结核心文件SHA全部一致，零新增DSH任务，无服务重启。原定时跟进cuagent-p5已更新为调用正式入口并核对JSON结果，不再手写运行时许可；首日记录保留，不冒充新入口已完成未来实际授权。README/后端使用说明同步。

README当前状态整理（2026-10-03）：将P5旧115/141项回归、开发消耗和启动前状态归为历史说明，当前入口只保留155项回归、首批已通过/下一批10-04及七日待验收；原证据未删除。只改说明，不改冻结源码或增加模型任务。

P5正式第1天完成（2026-10-03 12:11）：实时额度已用9%/剩余91%，积分62494.0260570000未变、卡1张未用。调度进程81383/session92548在12:10:01真实记录WAITING_PERMISSION；操作者单期授权后，原occurrence `fc4ad466-dc33-417e-9f44-436016f306b8`、batch `4e726e7f-544d-48da-a613-2f340dd6b1ab`唯一创建。task `948922ae-515a-4e72-8302-d6f0f45a31a6`/session-f89a43f2-7890-4751-b20c-4d18256d4e11为9raw/12638token，task `507294fc-bade-42d7-884e-e63fd38b2261`/session-bee12891-a56c-4036-a327-c3a6e645d20f为10raw/15995token；均Flash/off、各5模型工具调用、合计28633token。原源摘要、Git范围、冻结元数据载荷、会话/审计、API用量、通知与四下载独立核验VERIFIED；两任务各恢复基础配置一次/0告警，pending0，12:11:15许可已撤销。正式证据`.runtime/backend/p5-week-20261003-001/day1-attempt2/receipt`，完整七日结论仍INCOMPLETE，次日10-04 12:10到期；用户采用未评估。

首日介入保留：初次私有控制脚本用证据文件的排他写入函数更新已有撤销许可，FileExistsError，finally同样拒绝覆盖；独立确认许可仍false且0发生后，改为原子替换运行时许可，在新attempt2目录继续同一期，不新建计划、不重试模型。day1原证据与day1-interventions.json保留。定时跟进cuagent-p5的额度文字收紧为已用严格小于70%（剩余>30%）才能放行；此前仅写保留5%不充分，不能用底层通用余量门槛取代用户70%停止要求。本轮模型费用未使用积分/重置卡；没有把人工到期授权称为Codex自动唤醒验证。

P5正式七日计划已创建（2026-10-03 12:03）：schedule `1ab2e3a4-8426-48e8-bf1b-3452efa1fdfe`，北京时间10-03 12:10开始、10-10 12:10满168h；10-03至10-09各最多一批两任务，共7批14个新任务。固定p5-personal-workflows分支、基线2ca41a5、观察器版本102a8d5；源码哈希及原创建意图保存在私有`.runtime/backend/p5-week-20261003-001`，不上传。首次脚本因缺PYTHONPATH在任何写入前退出，补本项目导入路径后唯一创建成功。当前聊天定时跟进cuagent-p5已ACTIVE，每日12:11、共8次，最后一天只做最终核对；每次需新查额度、单期5分钟许可，不绕过配额或预派七天。12:03真实scheduler只返回NOT_DUE，原计划0发生/0任务，before-start回执INCOMPLETE；旧短测许可仍撤销，API80171/Worker80173保留。电脑/App需运行，未改睡眠/开机自启/共享服务；仍无用户阅读采用反馈。代码与短测已验证，真实一周未完成，不更新默认分支为P5验收。

P5七日观察准备（2026-10-03）：先提交回执契约9a99914，再新增workflow_preview/week_observer及14项反例，完整后端155/155。来源预览真实运行零提交；初次人工填错完整Git SHA被拒，读取真实rev-parse后采集成功，没有改Git或放宽校验。新观察器首次误用整个usage对象比较，API额外models/monetaryCost导致CHECK_FAILED，保留diagnostic-001；修为逐项核对原token、模型和预算，diagnostic-003原短测两任务VERIFIED、四下载SHA一致，七日结论仍INCOMPLETE。回执位于私有.runtime/backend/p5-observer-diagnostic-20261003-003，预览位于.runtime/p5-preview-20261003-001；无新增模型调用/服务重启。正式七日尚未启用，P5未验收。

更新：2026-10-03。主路线：[Harness最小可用底座 → Computer Use主线 → 通用增强/O0](Harness_Development_Plan.md)，当前按[个人任务服务P1–P5路线](docs/product-roadmap.md)推进。下方“当前交付”及最新收尾记录代表当前状态；各日期过程中的未提交/未完成描述保留当时事实，不代表目前状态。

## 当前交付

P5真实到期闭环（2026-10-03）：0007新增计划/发生表，九张旧表迁移前后行数及内容SHA不变；新API80171/session62216、Worker80173/session22385。单次诊断计划`06388638-8839-4ee3-baa6-79704a2a6f51`真实11:42:09+08到期：此前NOT_DUE，到期无许可WAITING_PERMISSION且0发生/任务；实时套餐92%、积分未变后给该期5分钟许可，11:43:18提交唯一发生`92df77bb-3afd-489f-9254-11a4bd748bc8`及batch `b6e6181b-11ab-4554-8fb3-13b9f3c42139`。再次启动调度器NO_ACTIVE_PLANS，同键创建返回原计划；源重新采集与冻结SHA `df8bf225e75a50600067a0349683f0bfed2738daee9c5341f24eaa102b980dda`一致。任务`5085ff30-f483-41a8-a43e-b891662f706c`、`3ee02047-0b73-4d9d-acfd-2447640d05c1`各5模型工具调用、raw9/10、token12463/15792；Flash/off、独立验收、通知3/4链接下载四产物SHA/ETag通过。正常恢复，无待执行任务，通知未代用户已读；短测许可已明确撤销，原许可审计副本保留。后端141/141，私有证据`.runtime/p5_schedule_20261003_001/independent-verification.json`。本轮新增28255 token，P5累计8次模型开发验证113613 token及1次0调用停止；七日正式计划尚未启动，未把一次EXHAUSTED当一周完成。

P5调度入口接入：固定本仓库两分支的WorkflowCollector，按发生时刻固定24h任务窗口/时区日期；API/CLI创建、查询、暂停计划，独立`backend.manage scheduler [--once]`只协调到期批次、不创建模型循环。QuotaPermit读取developer-owned私有普通文件，拒绝符号链接、宽权限、过期/未来/跨计划时刻、低余量/积分变化/重置卡记录；每次许可最多5分钟，API创建计划不会自动授权。13项新许可/采集边界/API持久测试及全后端141/141通过；额度是操作者实时账户查询后的记录，不伪称服务端能直接读取Codex账户。0007生产迁移和真实到期闭环仍待执行。

P5周期调度核心：先补技术事务细则，再新增0007计划/发生表、ScheduleSubmission及ScheduleService。计划同键同正文幂等，IANA时区与首时刻偏移一致，固定UTC24h、最多7次；无许可等待、超10分钟MISSED、PREPARING60秒超时不重采。事务外采集，最终持计划锁复核暂停/许可/源身份与时间窗，将原源快照SHA、批次及两个任务同事务落库。BatchService增加调用方事务入口，原批次行为回归保持。13项新受控时钟/隔离PG测试：并发仅一采集/一批次、采集中暂停、进程退出超时、许可撤销、7次漏跑不创建任务、源错误/篡改、子项插入故障整批回滚，后端128/128。未做生产0007迁移、未创建计划、无新增模型消耗；实际采集器/许可文件与API/CLI待接入，受控时钟不是一周真实观察。

P5真实通知通过（2026-10-03）：额度实时剩余92%、积分62494.026057未变、重置卡未用；空队列下停本项目服务后迁移0006，八张旧表逐行内容SHA及行数一致。先只启动API，排队task `8cbbb153-d365-4d5a-87ce-bf43fabfd826`真实停止、无session/0raw，产生唯一STOPPED通知；重复停止不重复通知、两次已读返回同时间。实际API79232→79252重启后读取原通知/已读状态一致，再启动普通Worker/session13469。新task `3d151535-33d1-44d5-9651-b96c63e407f1` / session `session-703c489c-af8a-4b65-9c63-be1ba01ed4fa`，Flash/off、5模型工具调用/9raw/12583 token；独立验收及通过真实通知链接下载两产物SHA一致。成功通知2保持未读，诊断通知1的程序已读不冒充用户使用反馈。基础配置恢复无告警、无待执行任务；后端115/115。私有证据`.runtime/p5_notification_20261003_001`。P5累计六次模型开发验证85358 token，另排队停止0调用，均不算一周。周期调度及真实一周仍待完成，P5未验收/未推送。

P5通知开发：方案先补终态事务契约，0006新增notifications表；TaskService在finished/stop_requested/owner_expired的实际终态事件同事务写入通知，event_id唯一，不追补历史。API/CLI支持游标列表、未读筛选、幂等已读；同时显示历史终态和当前状态，仅当前仍成功提供原下载入口。8项新增独立PG/API测试（并发已读、事务回滚、失败/阻塞/待核验、恢复后的历史提示、重建App持久性）及全后端115/115通过。没有外部邮件/聊天/系统弹窗；生产迁移与新真实通知待验证。

P5真实批次通过：0005仅新增batches/batch_items，停止空闲本项目API/Worker后，迁移前后tasks/attempts/events/artifacts/usage/resources六表行数及逐行内容SHA一致。新API78694/session3060、Worker78698/session43087；不改PG/VM/SSH。真实batch `ef18d713-c46b-4534-9668-24b1d8c3f151`关联两任务`d0c1e805-0d59-47c4-a7f4-a5a7a8684c45`、`7cc894db-4996-4adb-ac3c-0fcf87cb4b24`，同键重复POST返回created=false、原批次；两任务各5模型调用，raw9/10、token12572/15948，Flash/off、独立verify及四次API下载SHA/ETag核对通过。恢复配置无告警、无待执行任务。全后端107/107；私有证据`.runtime/p5_batch_20261003_001/independent-verification.json`，批次这两次新增28520 token，P5至此开发验证五次共72775 token（含旧版和返工，不计一周）。周期调度、通知及一周验收仍待完成，P5未推送/未验收。

P5批次开发：新增0005迁移（仅batches/batch_items新表）、BatchService事务提交及/batches创建/查询/停止、CLI batch-submit/status/stop。2–3个独立任务整批先验证、同一事务写入任务/事件/关联；稳定请求摘要与唯一键处理并发和ACK丢失，同键不同正文409。部分失败不标整批成功，停止按原任务边界逐项持久执行，中断可重做剩余停止、不重建任务。7项新独立PG/API测试及全后端107/107通过，包含第二子项故障整批回滚、4并发仅一个批次、旧实例重建后查询；生产迁移及真实批次仍待验证。

P5两类真实报告闭环（2026-10-03）：核对套餐93%/积分未变、空队列后精确停止旧API49955/Worker76802，启动本项目新API77570（session36494）及Worker（session20026），PG/VM/SSH未变。项目变更task `36a7740a-ae01-4b1b-903d-4df19f8ec912`，5模型工具调用/9raw/13005 token；运行日报首版task `7332b05d-044a-4a63-8e90-be6a69e018d9`，5/10/15297 token，链路正确但缺用途要求中的状态数量。补明确状态计数，不改原17任务源数据，另存新快照SHA `c471bbf52960507b2688e45deaf120c0094444b76c7fd6f0b0ead453c246fff7`，新task `d5949c63-af6c-418e-9a7d-5ede1a8141ff`，5/10/15953 token，状态计数与来源逐项一致。三次均Flash/off、独立verify和两产物API下载SHA/ETag通过，首版及返工消耗保留，共44255 token，费用未知。后端100/100，旧请求幂等/审批模式不变/聚合失败不续跑均覆盖；基础配置恢复记录与无待办核对通过。此为用途开发验证，不计正式一周；批次、计划及通知未完成，未推送P5或标总目标完成。

P5聚合后端入口：Submission可选`inputMode=aggregate`，默认省略保证旧幂等请求摘要不变；显式拒绝releaseAt组合。Worker同时将模式传给prepare/verify，恢复时核对原审批工具清单，聚合原终态只核验、不套用P3自动续接；已有聚合续接意图拒绝派发，错误保留UNVERIFIED。CLI可传入模式。5项新API/Worker测试及全后端100/100通过，真实部署与两类任务闭环待执行。

P5开始（2026-10-03）：从已推送P4 `aa6d031`新建`p5-personal-workflows`，技术方案先提交`95357f4`。根据P3/P4证据选两类项目内用途，保持单Worker/Flash-off/30raw与独立验收，不访问个人资料。新增`backend/workflow_sources.py`：固定本仓库/完整Git提交范围，合并按第一父统计、二进制分列、超20提交拒绝；真实任务元数据白名单、100行上限、时区与窗口固定、未知usage空白而非零、缓存与普通用量分开，私有快照不覆盖。15项新测试（真实临时Git及恶意标题、空窗口、缺失用量、身份/预算/时间范围反例）通过，后端总95/95。首次只读采集真实15提交、17任务，私有project快照SHA `9809e1fb930acffe69c2e3c6b627429f5d9cae402471f5ddab35efac03960f75`，operations SHA `2ccad68ffbc812bc4b02a7bab3662cc4a607234712f2002c563cf6d971c01c70`。未调用模型、未提交任务或重启服务；真实报告、批次/调度/通知、一周记录尚未完成，不标P5通过。

P4正式完成（2026-10-03）：在`cdfd7c2`冻结20对/40唯一会话、相同输入/oracle及交替顺序，manifest SHA `7e312f0d025bdb852164b3cb65ac2bf71a2389ee0e355fa69a13f217673f87b7`。基线/候选各20/20独立SUCCEEDED；总token316162→256741（-18.79%），完整墙钟249487.147→219320.894ms（-12.09%），模型工具调用189→101、raw209→206，任务修正介入0/0。每对实时额度剩余93%、积分未变、重置卡未用，未换模型、样本或提示、未补跑。最终重新读40个官方当前终态与原持久证据，验收产物/来源/审计/停止/基础账本PASS，私有审计SHA `842efc6838bae4f3ee5e00291f5044f116091b6c69a42392b6cd07ea12925ac1`。基础配置恢复，普通Worker76802/session32584已运行。当前版回归39 Python、71核心、37官方适配、80后端通过；最终私有审计首次缺PYTHONPATH导致导入错误，修正启动环境后通过，不改正式源码/证据。详见`docs/stages/p4-summary.md`；P4声明范围本地通过，仍opt-in，P5真实一周及C3/第二人未完成。

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
