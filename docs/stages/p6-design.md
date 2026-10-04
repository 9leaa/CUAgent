# P6：将受控桌面任务接入个人任务服务

2026-10-03，用户批准后续计划并授权执行。分支 `p6-desktop-task-service`，起点 `8bd099e`；独立工作目录 `/Users/zhangchengjie/CUAgent-p6`。方案先提交，再实现。P5七日观察未完成，P6不得取代或提前宣告P5通过。

## 目标和非目标

专业目标：任务类型化、按类型执行/核验、统一持久生命周期。直白说：像提交日报一样提交一个测试VM里的TextEdit任务，随后查询、停止并下载经过独立核对的结果。

复用官方Harness唯一Agent循环、现有VM桥接与TextEdit验证器。第一种任务仅把1–10条用户指定的纯文本交接内容按原顺序逐行保存；不承诺开放式总结、任意应用、创建任意宿主文件、GUI长任务或无人值守解锁。DSH固定Flash/off、单任务30次实际请求，失败/观察/内部请求均计数。C3/第二人、O0、多Agent、跨机器与新桌面壳仍不做。

## 隔离与发布

2026-10-03用户明确批准本次受控临时切换窗口：可临时停旧Worker、切换App进行P6真实测试，结束恢复；P5调度计划不取消。这解除此前等待切换批准的限制，不豁免实时前置检查。首次检查发现VM锁屏，故尚未停Worker或切换App。解锁后须重查额度、App/队列空闲、VM/锁与配置，再执行同一授权窗口。40%门槛对应Codex套餐额度；DSH平台显示API余额，不能用两种数值互相替代。

- P5原目录、分支、运行进程、数据库和冻结文件不改。独立Git工作树做P6开发；不复制凭证、原会话或.runtime，使用已有Python解释器运行无模型测试。
- 数据库测试只用独立测试库；不迁移当前生产库。新API与Worker不能接入当前P5生产队列，更不能让旧日报Worker领取桌面任务。
- 真实集成前检查P5无在途任务、配置恢复完成及共享Desktop锁；显式核对剩余额度≥40%、不用积分或重置卡。VM/Driver/锁屏/权限前置检查失败即停止，不自动改SSH、睡眠或权限。
- 真实测试必须是受控串行窗口，记录环境切换和恢复，不能与正式观察抢占Desktop。无法证明隔离就先留在无模型阶段；核心与运行环境切换安排在P5收口后，除非用户另行明确批准。
- 各小步验证后提交推送P6阶段分支，默认分支仅在阶段验收完成后同步，不发布PR/tag。P5默认分支同步与P6开发快照分开。

## 实施顺序

1. **输入契约**：新增独立 `DesktopSubmission`，显式kind仅 `desktop-textedit`，lines为1–10条非空单行UTF-8文本，总正文≤4096字节；拒绝多行、控制字符、未知字段和任何工具/路径/预算/模型/应用覆盖。确定性拼接仅用于冻结任务要求及独立期望，不生成业务文档。先做单元反例，不提前开放新接口。
2. **队列与类型路由**：保留旧日报JSON及幂等摘要不变；新桌面类型显式准入。类型固定后不可通过恢复改变；未知类型不派发。API、领取、停止、日志、通知与产物按类型联动。旧Worker不能领取新类型，不能仅在API增加字段。先验证同键同任务、冲突、停止未派发、类型隔离及旧任务兼容。
3. **执行生命周期适配**：从日报专属Worker中抽出必要的prepare/start/inspect/stop/verify/restore契约，日报行为不变；TextEdit适配复用既有桥接。单Desktop全局锁和持久owner/epoch约束必须覆盖两个类型，并在VM最终派发端拒绝过期owner。不能仅靠数据库心跳推断VM安全；初版断线/未知副作用暂停并核对，不重放输入或Save。
4. **产物与独立验收**：任务目录与run身份由可信端生成；只准测试VM自己的目标文件。复用原GUI输入/新观察/Save/完整文件/result读回判据，收集并核对原截图哈希和完整账本。下载只开放声明产物，非SUCCEEDED或哈希变化拒绝；配置恢复告警与业务成功分开显示，模型不能登记成功或写审计。
5. **真实验收与交付**：满足上述隔离条件后，先单例最小真实闭环；再固定三组不同文本（含中文）逐项提交，记录全部尝试，不用新样本替换失败。另验证排队停止零调用、实际运行停止后零新派发、重复提交只有一个任务、失去执行权后安全拒绝。原预算不清零，未知状态不得直接resume重放。最后重跑相关日报回归，更新README/PROGRESS及P6总结，核对公开内容不含凭证后推送。

## 验收和证据

### 结果快照与准备失败收尾（002真实失败后，实施前）

002第一例文档/result原字节正确，但read_result后追加一次真实observe；final_state由write_result保存，当前desktop_evidence却要求它同时是最后一次观察，导致互相冲突。修正仅P6核验：明确final_state是结果写入前的依据，必须是write_result前最后一个已核验观察，且晚于全部Save；写结果之后仅允许只读观察/读回，不允许再次编辑或保存。所有后续观察仍须完整匹配原PNG/state哈希、同应用/PID/窗口，并核对正文一致，不能直接忽略尾部事件或放行新鲜界面与文件不一致。补正常尾部观察、改正文/换窗口/缺图/过期来源/尾部写入等反例，原失败保留UNVERIFIED；新规则离线复核不等于重跑成功。

002第三例已启动未激活guest，但在保存隧道意图前失败，adapter尚无prepared对象，Worker只能隔离，无法自动清理已启动guest。当前未保存原异常，不能将端口TIME_WAIT猜测写成确定原因。先补安全错误分类/阶段回执及准备阶段所有权收尾设计，再实现：预检端口在启动guest之前；guest已启动而后续失败时，只可用原绑定控制通道撤销/确认零在途/关闭，失败继续隔离，不新建guest、不重放模型、不猜PID杀进程。用真实loopback端口占用/关闭复用与模拟guest启动后失败覆盖资源泄漏和未知响应；不得放宽端口归属、许可、预算或旧P5隔离。后续部署冻结新版本并单独回归，不能覆盖002样本。

### 准备失败的未激活guest清理（实现前细化）

收尾衔接（f9924dd之后、实现前）：仅当前adapter本次prepare失败且清理确认的原上下文可以返回结构化PreparationClosed证明。Worker先停止/确认心跳线程退出，独立复核固定run/owner/epoch、私有失败/清理意图与确认、无App/profile应用/会话启动意图、原profile-before/plan SHA与当前实际配置字节一致。任何缺失、篡改、执行权丢失或线程未退出都保持原隔离，不读取旧任务回执自动解锁。随后只刷新数据库停止态控制（不续guest），由原owner/epoch正常finish为FAILED；已观察到用户停止则STOPPED，usage仍unknown、无session/业务产物。确认原配置未变明确标environmentUnchanged，不执行App恢复动作；正向证据充足时避免新建隔离，绝不删除既有quarantine。不自动恢复P5；真实VM验收和原002失败状态均不受本补充替代。

本步只补adapter清理，不改变Worker的保守隔离/非成功判定，不自动恢复P5、清除旧隔离或修改旧失败。bootstrap已返回并验证原ready后，后续control-client/tunnel/connection准备失败才可进入清理；bootstrap响应未知或非法时不猜身份、不重启guest。先关闭本次自有隧道，再沿原SSH包装器直接访问guest loopback控制口，不依赖失败的host转发端口。

清理复用同一DesktopControlClient源码及固定协议函数，以可信SSH单次运行；固定guest Python、普通mvpagent/VirtualMac核对，token仅有界stdin，不入argv。原run/owner/epoch严格绑定，必须未激活、raw/pending均0、modelPort为空，且尚未发放有效许可；然后只执行revoke和shutdown，不renew/activate、不操作GUI、不按PID杀进程。新私有清理意图先独占落盘，操作未知不重试；仅收到并重新验证原身份、停止且已关闭的回执才记录cleanupConfirmed=true。只保存固定字段，异常原文和远端额外字段不写回执；原prepare异常继续抛出，Worker仍隔离供后续核对。验证用真实loopback协议、模拟SSH/失败注入，不冒充真实VM收尾或完整P6通过。

### 官方提醒修复版回归 002（执行前）

在17ead3c修复和470项后端、113项Node测试通过后，冻结新的repair-entry-cohort-002，仍使用原三组文本及guest c448ae2。旧001的成功和失败不变；其第三项从未执行，先通过原API停止并确认零调用、无session，保留未执行记录。核对身份后只停止旧P6 API，原数据库与证据保留；新实例使用独立库及原18100端口。新批次全部任务先提交冻结，再按既有逐例额度、切换、独立核验及恢复协议执行。不把新批次成功覆盖旧失败，不因再次失败自动替换样本；P5进程和冻结源码约束不变。

### 官方提醒与用户指令区分（真实失败后，修复前）

原取消会话末尾还存在无usage的assistant/attempt（stream为空）。新分类允许归档该失败终态后，用量读取也不能只合计此前assistant/message就声称完整：存在未说明消费的assistant/attempt即保留available=false/null，不把空stream解释为零费用。先补此反例，再改P6专用usage；不修改原失败或P5用量代码。

repair-entry-cohort-001第二例在11raw后被取消并隔离；原会话只有一条真实用户prompt，另有官方repeat-tool-reminder插件以user/message记录的notice。现P6复用了按行数统计userMessages的旧函数，运行态校验因此拒绝，随后终态归档也因同一条件失败。先保留原失败、原会话和未知用量，安全撤销/零在途/原终态独立确认后恢复P5，不将该例重新标成功。第三例尚未执行，不以新版本结果覆盖原冻结版记录。

修复只落P6，P5冻结daily-report-runner源码不改，也不关闭官方重复提醒。区分真实用户prompt与经过核对的框架notice：原用户消息仍唯一且rpcId绑定；只接受已审查source.kind=repeat-tool-reminder、form=notice、固定工具/阈值、原提示模板和对应此前重复调用证据，其他来源或伪造内容继续拒绝。JS观测/归档与Python独立验收必须遵守同一分类，并显式报告框架提醒数量，不能删原会话行或把任何user/message笼统忽略。先用原失败脱敏结构和合成反例验证，再新建明确版本的修复回归；旧任务不resume、预算不清零，不承诺修正分类即可保证业务成功。

### 正式入口修复版三例回归（执行前）

以已提交bb812b6执行源码为基线、guest固定c448ae2（原部署manifest逐次核对），新建独立服务实例与明确标注repair-entry-cohort-001的三例回归，不替换原formal-01失败。沿用此前冻结三组英文/中文/混合字符输入；先通过真实loopback API和公开client命令提交全部三例，冻结原任务ID、正文SHA、源码版本与文件SHA后才允许任何模型执行。每例调用当前Codex用量工具并绑定原任务/profile，额度记录至多五分钟，正式worker-once执行原任务，不能重发未知请求、重建任务或重置预算。

每例在原P5空闲/下一计划30分钟以外、VM解锁、原App/profile已恢复前提下，按已授权窗口核对原Worker身份并单次TERM退出；执行命令自己持共享锁和实时门禁。结束按原outcome、session/guest账本、实际GUI保存、独立核验和HTTP下载原文档/result完整字节共同判定，未知保留不重试。App/profile原SHA相同、guest关闭零在途、无隔离后才恢复原P5 Worker，逐例记录临时停启。API自身重启持久性用已完成无模型HTTP测试，不额外重复这三项业务请求。三例都完成后审计所有成功/失败/用量/人工介入及恢复；不将本新cohort拼入旧版3/3，不以三例通过替代P5七日或用户实际使用反馈。

### 独立服务启动入口（实现前）

受控Worker首版命令为单任务worker-once：显式profile/execution/quota/task和cutover-approved，所有配置只来自私有操作者文件，不能来自任务正文。先在原共享锁内执行准入，再按精确task ID领取，不取队列中另一个任务；缺任务/非QUEUED/已有attempt均拒绝。quota绑定原task及profile文件SHA，五分钟内普通额度≥40%、固定积分且卡未用，真实触线持久锁止、自然重置不清除。执行配置固定guest commit/manifest和官方App/Node/SSH路径，不自动部署或修改网络。准入和adapter每次gate都重查quota、原P5所有在途/排队/临近计划、旧Worker进程不存在、VM身份与解锁状态。首版不自动终止/恢复P5领取者：原已授权切换窗口须先完成可信停启，命令发现仍运行即拒绝，不能把一个布尔开关当作已停止。命令负责原任务执行/App恢复并保存回执；未知仍沿原Worker隔离，不复用配额尝试另一任务。测试分别验证持锁前置检查、精确领取/默认兼容、期限/额度持久锁止与生产组合参数，不用模拟adapter声称真实桌面通过。

完整入口分为独立队列服务和受控单任务执行两层，不能把开启API当作已运行桌面任务。先提供desktop_service init/serve：显式引用原私有backend.env，仅复用本机数据库连接和已有App配置路径；创建全新cuagent_p6_service_UUID数据库、私有目录及独立认证token，迁移仅作用于新库。配置独占落盘，失败保留初始化意图，不自动删除或重建。serve逐次核对原配置，拒绝同库、重叠产物目录、原18089/管理端口及非loopback监听；只开放桌面提交和既有查询/停止/下载，不允许日报、批次、定时任务混入。客户端新增显式--desktop-service配置选择，未指定仍走旧环境/18089，禁止悄悄改默认地址。初始化/启动都不触碰VM、不启动模型、不停止P5或领取任务。

第二层再组合原DesktopWorker/adapter为单次执行入口：使用原共享锁、固定部署、原P5空闲/已停止领取者和VM就绪检查，逐任务绑定五分钟内真实Codex额度记录；正式请求前重查，不凭服务启动授权未来任务。未知执行保留原身份和隔离，恢复配置确认后才恢复旧领取者。不得将这一层省略为手写脚本或将第一层标作完整可用。先以真实独立PG迁移和实际loopback HTTP/CLI验证隔离、重启持久性、幂等/停止/下载拒绝及旧日报回归，再沿完整入口跑固定同版本业务回归；原失败不覆盖。

### 操作者桌面提交入口（实现前）

现有client仅能提交日报，桌面提交依赖开发脚本。先增加desktop-submit --spec --key，spec仅允许既有DesktopSubmission的kind/lines，不把命令或路径当任务权限；有界读取普通UTF-8 JSON，拒绝重复字段、未知字段、超限或控制字符，再向原/desktop-tasks单次POST。复用原认证、查询、停止与两产物下载，响应未知时保留原幂等键，不自动重发；默认服务仍503，不因增加CLI提前打开生产桌面执行。使用独立PG和原API验证CLI提交/同键幂等/冲突/排队停止、非法spec零POST及默认关闭；这是操作入口开发，不替代真实VM正式三例或生产Worker启动器。

### PostgreSQL失权到真实VM停派（执行前）

新建独立诊断库，通过原API提交/TaskService领取固定桌面任务，绑定原task/run/owner/epoch；原DesktopExecutionControl负责数据库heartbeat/authority→SSH隧道→guest许可。系统curl仅作为可信诊断请求方发送原生产模型HTTP observe，不创建官方会话。首次真实观察后只在该诊断库把desktop资源expires_at设置为已过期，记录修改前后原行；随后调用未经替换的refresh，必须由真实数据库拒绝并自动关闭本地/guest许可，不能手动revoke冒充联动。原HTTP observe409、预算不增；旧owner heartbeat/authority、重建control均拒绝，guest原许可sequence不得增加。零在途确认后正常claim过期清理应把原任务标BLOCKED/OWNER_LEASE_EXPIRED，不重排、不重放、不登记业务成功。finally关闭原guest/隧道、核对配置并恢复P5。保留完整私有故障/响应/原账本；此证明真实数据库至执行端联动，不冒充官方模型取消或完整Worker失权故障。

### 真实HTTP拒绝边界补验（执行前）

只读探测发现系统curl能够收到VM SSH端口响应，区别于此前Python/Homebrew Node/Electron Node的EHOSTUNREACH；不据此推断根因或已连通模型端口。使用新的独立诊断run，先验证原guest模型端口GET明确405，再通过原生产HTTP入口进行observe→缺参数type_text拒绝→旧snapshot的save拒绝→新observe。独立要求两个拒绝计预算、无输入/hotkey派发，新观察来自真实Driver；随后可信控制通道revoke，原模型token再次observe必须409且预算不增，原控制身份直接POST renew也必须被guest拒绝，不能只测试客户端预检。curl不跟重定向、不自动重试，凭证仅stdin，不进argv或公开日志；不改变监听、来源校验、权限或网络配置。原trace、响应摘要、观察PNG/state与关闭记录私有保存并独立核对。该诊断不调用模型、不替换正式三例或旧连接失败；App/数据库失权全链路另验。

### 真实VM自然到期诊断（实施前）

宿主独立Python/Node直连VM受阻，不改网络权限或模型入口。新增仅可信开发者可运行的VM诊断：沿用prepare_guest、原共享锁、真实DesktopTask/Driver及未改的生产许可门禁，先实际观察，再停止续期等待真实墙钟到期；同一对象再次observe必须在Driver派发前拒绝。之后原controller及从同一许可文件重新构造的controller均不得续期；不手写许可、不修改时钟、不重建任务、不增加模型工具。finally撤销并关闭原runtime，保存原trace、观察文件摘要、到期时间、拒绝与关闭回执。宿主独立核对首次真实观察、到期后预算不变/零新派发、原身份及关闭结果。该结果只证明真实VM最终派发/持久许可边界，不冒充官方App请求、HTTP来源隔离或数据库失权全链路；后者仍分别验收。P5空闲检查/共享锁/临时Worker停启与配置核对保持原要求，未知清理结果不得自动恢复领取。

### 已请求停止的有证据收尾（实现前）

现有Worker任何中断均隔离，连已明确停止且无在途也不能收尾。新增仅STOP_REQUESTED路径：先撤销local/guest，单次cancel原会话，结束并确认续期线程退出；有界读取原session/guest，不重新prompt或授权。仅同一原任务仍STOP_REQUESTED、guestStopped=true/零在途/合法raw、官方原prompt明确terminal、再次撤销确认及原owner/epoch的停止态DB心跳有效时，保存usage并finish STOPPED；之后才允许已有恢复流程。取消ACK本身不算停止，未知状态、失权、超时、缺字段继续隔离；不把副作用当回滚，不对非用户停止的错误自动收尾。先模拟协议/独立PG反例，再真实App停止验证。

### 下一步真实停止/拒绝边界验证安排

保持原三例失败和版本变更记录，不重启原模型请求。直接宿主HTTP诊断两次零raw连接失败后，不改系统网络权限；优先通过原官方App执行通道验证。停止测试应绑定新诊断任务、原会话及run，在首次实际观察完成后调用原任务stop，记录停止请求/guest撤销/在途返回/官方终态，独立比对停止后零新Driver派发；任何未终态保持隔离，先查原状态，不补发prompt或冒称回滚。排队停止应证明未创建会话和零raw；失权测试以真实guest许可撤销或到期证明原owner不能续派，不能仅用mock或DB状态代替。P5切换和恢复沿用现有授权窗口，禁止修改原正式七日任务。完整修复版业务回归与历史失败分开报告，不将跨版本2成功覆盖原首例失败。

### 正式第一例发现的旧观察复用（修复前方案）

807c18a最小真实闭环11raw通过；同版预先固定三例中的第一例14raw被独立核验拒绝，原任务保留UNVERIFIED，不重跑或用新样本替换。其轨迹为观察→拒绝输入→以同snapshot保存，执行端拒绝路径未作废观察；独立核验已拒绝，不能放松。仅在P6 DesktopTask覆盖charge_rejection：在原dispatch_lock内首先清空snapshot，再调用原拒绝计数/审计逻辑，无论失败此前是否已消费raw；禁止新增GUI请求或重置预算。旧C0/C1/C2实现不改。反例验证拒绝后Save与AX输入在Driver前被阻止，新观察仍是继续前提；保留首例失败及后两例未执行状态，后续修复版验证单独标注版本，不能拼接成原三例全部通过。

### 首次真实会话后的修正方案

插件依赖采用官方 profile-scoped resolver，独立 run 不在其解析范围。构建证据仍保存于私有 run，同时只向原 profile 下独占的新目录安装两个已核对插件，候选指向该目录；apply 前分别校验两处摘要，不覆盖旧插件。插件完成注册后写本 run 的无凭证 ready 回执，App 启动后、发 prompt 前要求回执身份和五项工具精确一致。源码需核对实际官方安装对应 resolver；不能用仅存在 preset 或编译成功代替插件加载。

live-003 已真实请求 Flash/off，但工具调用为零，不计成功。官方 V4 JSONL 首行是无 seq 的 session 元数据；用量读取须单独严格核对 version/id/cwd 后读取其余有序事件，不跳过任意无序行。该次实际输入267、输出36、总303 token，原 unknown 记录保留，另存核对记录。App 会把 YAML 引号和换行规范化；恢复允许通过可信解析器证明与已签名候选语义完全相同的格式变化，保留实际原字节与摘要，仍拒绝任何语义变化并在原子替换前复核当前摘要。先恢复原 P5，再定位插件未就绪；后续启动必须把工具就绪检查作为发模型请求前门槛，不能只看 preset 存在。

### 授权真实窗口（2026-10-03，执行前）

真实部署已成功，首个任务在领取前被共享锁目录权限检查拒绝：旧P5的.runtime为用户所有0755，锁文件0600。共享目录不是凭证文件，不更改P5目录；门禁改为规范目录、当前用户所有且组/他人不可写，锁文件仍要求0600/普通文件/当前用户。原任务尚未领取、无会话，继续原任务而不新建替代样本。

现场预检修正：原known-hosts为0644，内容为公开主机密钥，不是登录秘密；允许规范路径、当前用户所有、普通文件、无组/他人写权限（0600/0644均可），不修改原P5文件权限。askpass仍必须私有可执行。原首次预检失败保留，未部署/停Worker/调用模型。

用户追加授权助手用现有测试账号自行解锁VM并完成测试，无需用户接手；不改密码/锁屏策略。真实窗口先固定当前提交，新建私有证据根和独立PostgreSQL数据库，保留失败不覆盖；首个用例仅输入“P6 controlled desktop task”。通过同一API工厂提交/查询/下载（隔离ASGI客户端，暂不称生产HTTP部署），执行器调用真实官方App/模型/VM。停旧Worker前确认P5空队列、未到期且全部会话空闲，取得原共享桌面锁；每个启动门槛核对最新五分钟内Codex普通额度≥40%、积分/重置卡未使用、VM解锁、旧领取者已退出和P5无在途。结束检查App配置原SHA和基础preset一致、guest撤销/关闭、锁释放后恢复原Worker；异常不盲重放原模型请求，保留原run并先恢复环境。DSH余额不设40%门槛，固定Flash/off与30raw预算不变。

### 桌面任务用量交付（实现前补充）

补齐路线要求的用量可统计：只从本次私有run原始session.jsonl读取assistant/message用量，核对绑定session/run，保留输入、输出、缓存读写和总token及模型路由；完整非负整数且总量一致才available=true。缺失、异常、截断或绑定不符返回未知/null，绝不当零或估算货币。adapter提供只读usage；Worker核验成功/失败均向既有finish传usage，未知执行仍不强制finish或释放资源，而在私有outcome保留可取得的用量。用量统计不能证明GUI成功或额度充足，不替代实时账户检查。纯合成会话及隔离PG验证，不切换P5环境。

### SSH标准输入修复（实现前补充）

只读确认P5旧vm-ssh最后使用`< /dev/null`，会丢弃P6部署包和导出请求。保留旧脚本原字节；新增P6专用包装器生成器，显式接收私有known-hosts和可执行askpass的路径（不读/复制凭证），在新私有目录独占写0700脚本。固定/usr/bin/ssh、VM地址/用户、严格host-key检查和认证超时，保持stdin原样；调用者既有有界I/O和命令/隧道参数不变。adapter配置改为known_hosts/askpass，在prepare生成本次独立包装器并传给bootstrap、隧道和采集；部署入口可使用同一生成器但不自动执行部署。测试以真实本机子进程回传大块stdin/参数、ssh -G无网络解析，以及私有路径/不可覆盖反例验证；不连接VM、不改P5运行环境。

### 完整执行适配与长准备续期（实现前补充）

组合已有模块为DesktopTaskAdapter，显式配置已部署commit/manifest、SSH/Node/home/build-tools/base-tasks与cutover_authorized（默认拒绝）；该开关不替代实际P5/额度/环境验收，暂不提供生产启用入口。prepare创建新run/session、冻结输入、构建候选profile、启动guest控制并建隧道，不启动模型；start依次停空闲App、应用候选、启动P6 App、按实时DB执行权激活guest、单次官方prompt。poll融合官方终态与guest实际预算；verify只在撤销后采集原包、核验官方会话及guest证据，最后复制核验过的原文档/result至交付目录，不生成替代业务结果。restore恢复原App/profile后可信shutdown guest，再关自有隧道；任一步未知仍隔离，不自动重放。

现Worker在prepare前、verify期间没有续期，实际SSH/构建可能超过30秒DB租约，需改为全阶段DB心跳：准备只续DB，激活阶段才续guest；终态撤销时持互斥锁切回仅DB模式，核验期间不得重新授权guest。finish与心跳串行、最终退出再停止线程；准备期间停止/失权禁止start。增加可信/ shutdown接口，仅已停止且零在途时关闭runtime释放guest锁，模型token不可调用；guest主循环随runtime关闭退出。模拟完整组合及隔离PG验证阶段时序，真实VM/App仍不执行。

### 官方App有界启停（实现前补充）

新增独立App生命周期模块，复用已验证官方RPC；stop先查全部会话空闲、记录原preset，再核对唯一官方可执行路径/PID，持久意图后仅TERM一次，10秒未退出则未确认，不强杀。start须无官方App进程且版本0.2.0-rc.2，确认本次profile apply/restore回执与当前patch SHA；P6只用原run私有连接及审计路径，恢复只用显式且验证过的原A1任务配置。open命令显式DSH_HOME并清空另一模式环境变量，先写启动意图再调用一次；45秒RPC就绪且preset精确匹配才确认，失败不重启。原配置preset清单从activate前快照读取，不猜恢复值。所有测试模拟系统命令/RPC，无实际App启停；P5未收口前不执行真实切换，上层仍须持共享桌面锁并停止旧领取者。

### P6独立profile事务（实现前补充）

新增显式root/official home/build-tools路径的profile模块和命令，不沿用旧脚本推导.runtime。prepare只在当前私有run下构建c0-vm-tools/desktop-tool-scope，按已审查real-app模板合并受控条目，保留不相关配置；原patch字节、候选patch和前后SHA独占保存，不启动/停止App、不改official home。apply/restore必须确认官方App进程不存在，使用profile目录独占操作锁，核对目标私有规范路径和原/候选SHA；apply前再次检查插件哈希，restore只在目标仍是本次候选时恢复原字节，发现外部修改拒绝覆盖。原子替换和fsync，意图/回执留在run；错误不自动重放或热切换，恢复不得跨home/run。测试临时profile和模拟App状态，真实切换仍受P5收口/另行批准门槛约束，App启停和版本核对将由上层适配完成。

### 官方会话独立策略验收（实现前补充）

新增后端只读验收，绑定私有desktop-session-binding/prompt-request/session.jsonl与原提交、run/session；原会话必须唯一用户提示、唯一completed终态，全部request/header均Flash/off且恰好五个TextEdit工具，完整call/result配对。核对唯一vm_type正文与guest输入SHA、Save snapshot序列与guest attempted_save、最终vm_read_result完整正文；仅与guest rejected_write_result计数匹配的写结果拒绝可保留，其余工具错误不接受。要求官方observe返回含图片、原请求审计至少一次imageBlocks>0且模型/工具范围一致。返回会话策略验收报告而不是登记整体SUCCEEDED；图片存在/请求审计不等于逐像素视觉理解，原PNG/GUI/文档仍依赖guest独立核验，真实会话格式仍需端到端验证。旧切换脚本硬编码原.runtime，不直接调用以免误改P5；完整profile适配另补。

### Guest启动准备与私有回执（实现前补充）

后端新增单次启动准备：先写原run部署/启动意图，通过固定SSH/Python运行审查过的启动脚本。脚本先校验普通VM身份、部署manifest SHA与全部源码SHA、固定run/owner/epoch，再独占新建私有启动日志并启动desktop_guest.py；stdin关闭、输出只入私有日志、无GUI/模型启动。最多10秒读原guest-ready及两份新token，必须绑定原run/owner/epoch和自有子进程PID、控制loopback/模型固定URL；准备回执含新任务凭证，仅保存到宿主私有文件，不打印/公开日志。超时/中断不重启/不猜PID杀进程，保留未确认状态待原run核对。宿主校验字段/令牌及回执身份，后续才能构造控制客户端/隧道；还不授权GUI。先用模拟VM/进程验证，不部署生产或切换P5。

### Python到官方会话适配（实现前补充）

新增DesktopSessionClient，固定已审查desktop-session-command.mjs入口，可信部署显式指定Node、私有official home/cookie及原run/session；不复制凭证、不激活profile。prepare只独占保存冻结输入、cwd/run/session请求，start/cancel各先写Python侧意图，再一次有界子进程调用已有官方命令，失败不重发。start回执必须同session、accepted=true、Flash/off精确匹配；inspect严格验证原session与终态/运行态/原prompt唯一性，poll同时读取guest rawCalls/pendingCalls，禁止把官方工具调用数当实际Driver预算。未知/缺会话或异常状态不当完成，cancelRequested只表示请求取消。运行命令有输出/时间限制，原Node会话模块继续保存官方意图/响应和原JSONL；本轮模拟命令响应与真实参数边界测试，不触发App/模型。

### 固定版本VM源码部署（实现前补充）

仅打包14个已核对依赖文件及来源许可证，内容从显式40位Git commit读取而非脏工作树；包含逐文件SHA/base64，包≤1MiB。独立安装器不导入待安装代码，先核对普通mvpagent/VirtualMac，再完整验证文件白名单、编码/大小/SHA与Python语法，最后独占创建home/CUAgent-p6-commit并0600写入及fsync，生成部署清单；已有目录一律拒绝，失败保留残留供审查，不覆盖/自动清理旧版本。宿主先保存部署意图，再通过固定SSH/Python单次发送安装器与包，限时/限输出，核对回执路径和清单SHA；未知响应不重试。通用有界进程输入默认32KiB不变，仅部署显式允许≤1MiB。不启动VM/Driver/App/guest服务、不授权GUI；测试在临时目录及模拟SSH中验证，真实部署受P5隔离门槛约束。

### 可信SSH证据采集（实现前补充）

新增后端采集器，固定现有guest Python路径、/Users/mvpagent/CUAgent-p6-<40位commit>部署目录和desktop_export.py；任务只提供已验证lines，run/owner/epoch来自绑定控制客户端，不接受任意远端命令。采集前后检查guest停止、零在途、调用数不变及持久许可已撤销；先独占写采集意图，单次SSH，无自动重试。子进程无shell，remote argv逐项quote，禁继承SSH配置和额外转发；stdin有界JSON、stdout选择器流式限65MiB/45秒，stderr不公开，超限/超时只终止自有句柄。完整成功传输先以0600独占保存原tar，再走既有内存接收核验；核验失败保留原包，不生成业务产物或登记成功。测试使用真实本机小进程验证有界I/O、模拟SSH结果验证集成，不连接VM。部署源码哈希、实际SSH和官方会话仍为后续必验项。

### 后端证据包接收（实现前补充）

新增纯内存decode_guest_bundle，只接可信SSH收集返回的有界原tar字节及冻结任务/执行身份；不直接解压到磁盘、不执行包内代码。限制包≤65MiB、普通文件≤65项、单文件≤8MiB及总内容≤64MiB，拒绝重复名、链接、特殊文件、任意路径/PAX扩展与白名单外文件；manifest有界且严格绑定run/owner/epoch、原输入摘要、每个文件SHA/大小、精确文件集合。文档/result再次逐字节核对冻结正文；返回内存快照与guest报告，始终sessionVerified=false，不能直接供finish登记成功。缺文件、改动、身份混用、tar截断及超限必须拒绝；后续实际adapter再结合官方会话/模型审计、安全落盘和全链路判据，不能将包校验当GUI真实性新增证明。

### Guest证据导出（实现前补充）

新增VM专用只读导出命令，固定C0Evidence/p2-UUID，owner/epoch由可信调用端提供；正文期望从stdin有界JSON lines读取，不接受任意路径或shell。先核对私有lease固定身份且stopped=true，再运行已有guest独立验证器；所有调用必须完成。仅将核验清单中的trace/final_state/state-NN.json/png/固定文档/result及生成的无凭证manifest打包到stdout，不能导出token、lease、个人目录或任意额外文件。逐文件二次安全读取并比对核验SHA/大小，发送任何字节前完成全部校验，总原始内容≤64MiB，固定tar普通文件/0600、无链接；失败stderr固定代码、非零，不生成业务文件。此摘要仅证明VM证据核验，不替代官方会话/Flash-off；后端仍需通过可信SSH采集、验证包哈希和独立绑定。测试合成文件与真实内存tar，不调用VM/模型。

### 宿主控制隧道（实现前补充）

复用已核对的私有vm-ssh开发包装器（固定mvpagent@192.168.64.3、严格known-hosts），不新建凭证或修改SSH配置。新增GuestControlTunnel，可信部署显式提供wrapper、固定绑定的DesktopControlClient和guest控制端口；仅-N/-T及127.0.0.1:hostPort→127.0.0.1:guestPort，ExitOnForwardFailure、禁agent/X11转发和复用连接。先校验私有规范路径及本地端口未占用，再独占落盘启动意图、单次Popen，不自动重启。最多10秒只读查询原lease binding确认身份和进程仍存活，监听存在本身不算就绪；错误/超时仅终止自己创建的进程，不杀已有服务。stdout/stderr不公开凭证，关闭限时TERM后KILL自有句柄；隧道关闭不代表guest许可已撤销。测试用模拟进程与控制客户端验证参数、身份、冲突、失败与不重放，不连接VM；真实隧道及部署仍需后续验收。

### Guest命令入口（实现前补充）

新增仅测试VM可执行的desktop_guest.py：先require_vm及显式--approve-task，固定当前mvpagent home/C0Evidence、原bridge.lock、模型192.168.64.3:8766；run必须p2-UUID、owner为UUID、epoch正整数。新run目录独占创建，随机生成两个私有token、不接受命令行凭证；仅控制端口用loopback动态分配，ready.json写绑定/端口/PID不含token，stdout仅固定就绪标记。启动不创建Task或模型会话，仍等待可信授权/activate。SIGINT/SIGTERM或一小时上限进入撤销与关闭，保留证据不删目录；在途未清空则持久写共享锁旁quarantine，新P6实例拒绝，返回非零供人工核对。旧C0不识别quarantine，禁止混跑旧版，不声称能抵御SIGKILL或系统崩溃。测试通过替换VM身份/环境和loopback工厂验证启动/信号路径，不在宿主启动真实GUI或生产服务。

### 后端guest生命周期客户端（实现前补充）

在现有固定loopback控制客户端上新增status/activate，不增加模型调用。status严格验证run/owner/epoch、布尔状态、端口、0–30调用数与在途数，调用数不得回退。activate对象内一次尝试，先查未启动且零调用状态、核对guest许可未停未过期，再新查可信authority期限；只POST一次，ACK必须仍在执行权/guest保守期限内，且active、未停、零调用。错误身份/类型/迟到/丢失响应都保持未确认，不补发启动；实际启动后的未知状态交由已有Worker撤销与隔离处理。guest持久启动意图继续约束跨进程重放；本轮真实loopback连接guest runtime，但Driver/环境仍模拟，不计真实VM验收。

### Guest受控启动生命周期（实现前补充）

新增DesktopGuestRuntime，构造时仅持有显式共享bridge.lock并绑定run/controller/token；不构造DesktopTask、不打开模型端口。可信控制HTTP可显式附加runtime，新增空参数POST /activate与GET /status，默认旧工厂无此能力。activate先独占保存启动意图，再检查有效许可、构造DesktopTask和固定地址模型HTTP；任何失败撤销许可并保留意图，不自动重试/重建。状态仅返回固定binding、active、stopped、rawCalls/pendingCalls及模型端口，不泄漏凭证/文件内容。revoke先持久停止许可，再停止已建Task；不等待在途Driver，也不宣称回滚。共享锁跨整个runtime存活；close撤销并关闭模型入口，若仍在途则拒绝释放锁。模型token无启动/状态/续期权限。本步用loopback和模拟Task环境验证完整grant→activate→工具→revoke链路及失败窗口，不部署VM或切换P5；后续CLI必须核对VM身份与现有全局锁实际路径。

### VM只读证据核验（实现前补充）

旧TextEdit离线验证器仅接收内存数据，未绑定原PNG与完整账本。P6 DesktopTask在成功observe返回前追加observation_evidence：绑定snapshot、实际调用序号、原state/PNG文件SHA与大小；记录失败即停止，不向模型补造成功。新增只读guest核验器，不构造Task、不发GUI、不写业务文件；从固定run内有界读取原trace/final_state/文档/result及被账本引用的state/PNG，拒绝链接、特殊文件、身份不符、缺失/改动或超限。固定路径从序号生成，不采信账本里的任意路径。核对完整调用配对、顺序、停止后零新派发、原PNG哈希、输入/Save来源及保存后新观察，再复用原业务验证器。返回vmStatus与原字节哈希，不返回整体SUCCEEDED或会话已验证；官方session、Flash/off及可信收集后端仍需分别核验。测试使用明确合成的状态/截图/轨迹，不能冒充真实视觉或VM验收。

### VM模型工具HTTP接口（实现前补充）

新增独立服务工厂，接收已由可信端在初次许可后创建的DesktopTask，不修改旧C0/TextEdit桥接；本步不提供生产launcher。复用现有插件的POST /、{op,args}协议，只允许observe/type_text/save/write_result/read_result/stop，所有动作走原Task与最终许可门禁，不开放verify、renew、任意Driver方法或路径。模型token与控制token强制不同；部署模式固定绑定192.168.64.3，仅接受192.168.64.1，测试模式显式仅loopback。请求限32KiB（覆盖4096字节正文JSON转义），拒绝重复JSON字段、额外字段、分块及歧义长度；2秒读超时。stop不等待模型串行锁，停止后排队请求仍由Task拒绝；已在途不承诺回滚。认证后的无效工具请求沿用原失败预算与审计，错误仅返回固定代码，不暴露私有路径/凭证。先用真实本机HTTP加模拟Driver验证许可撤销、预算、停止并发与协议兼容；不视为VM运行、部署或P6验收。

### 官方会话适配（实现前补充）

原会话读取补充：使用显式配置的私有official home，只读其sessions下一层分组中唯一匹配sessionId的session.v4.jsonl.zstd；拒绝符号链接/越界/重复匹配，压缩与解压数据各限64MiB，固定zstd解压命令、10秒超时、不执行shell。保留原JSONL字节，不重排或伪造官方事件。仅原请求已观察、唯一用户提示且当前明确terminal时独占保存session.jsonl；已存在时必须逐字节一致，不能覆盖旧记录。该读取器接入inspect adapter，不启动模型；真实压缩文件测试使用合成事件，后续仍须核对实际官方会话。

复用已核对的官方session/list/create/selectModel/prompt/cancel协议及现有observedSession解析，新增独立desktop-session模块，不修改日报runner或复制上游循环。start必须全App空闲、唯一real-app preset、模型目录明确支持Flash/off；固定run/session/cwd，create/model-select/prompt都先独占保存意图，再只发一次RPC，响应另存；任何已有create意图禁止再次start。输入保存为不覆盖请求快照，提示只指向当前批准TextEdit文档及逐行正文，不允许附加工具。查询/取消基于原session及原request ID，只有明确running才cancel；idle不发重复取消。RPC固定loopback官方端口，读取显式私有cookie文件且不输出凭证，所有请求有超时、禁止自动重试副作用。此模块不激活profile或启动App；真实profile/VM/证据连接待下一步，先用协议模拟验证全部意图窗口与拒绝路径，不计真实模型验收。

### 桌面Worker编排（实现前补充）

新增独立DesktopWorker，不将桌面任务塞入日报prepare/verify。trusted adapter提供prepare/start/poll/cancel/verify/restore，仍由官方Harness执行推理；测试adapter只作故障编排验证。prepare只准备身份/目录/许可通道，不派发GUI或prompt；start唯一一次。共享宿主desktop-worker.lock必须由部署明确指定到同一实际文件，不能默认使用P6工作树另一把锁；先拿锁再领取显式desktop类型。

无法确认会话终止或许可撤销时不调用finish释放资源，写入共享锁旁持久quarantine文件，后续P6 Worker拒绝领取，必须人工核对；不提供自动清除。旧P5 Worker不识别该隔离标记，因此生产切换必须停止旧领取者、验证版本，不能混跑。实际终止未知时也不自动切换App配置，恢复待人工核对。

绑定run目录、session和控制客户端后，初次许可成功才start；心跳线程每3秒刷新，失败标记lost并关闭控制。poll只接受明确terminal、0–30连续不回退rawCalls及pendingCalls；结束仍有在途即BLOCKED，不验证成功。初版总执行观察期限300秒，取消只请求一次，不盲重复prompt或GUI。先确认本地和guest撤销，再允许独立verify和登记成功；不确认撤销或失权则不登记成功。取消不等于副作用回滚。finally退出心跳、保持控制关闭、尝试原配置恢复；恢复告警保留为独立结果，不以业务成功掩盖。隔离PG/模拟adapter验证以上时序，不冒充真实模型/VM。

### 类型化产物交付（实施前补充）

现有finish/下载/通知硬编码report.json与report.md，必须先补交付契约再接桌面Worker。旧日报映射不变；desktop-textedit仅允许document.txt、result.txt，必须两项齐全、验证结果kind/session与原任务绑定，并再次逐字节核对document为冻结lines正文、result为正文加原桥接末尾LF。文件为后续独立收集器从VM复制的只读验收快照，不在host生成业务结果。未知类型或跨类型文件拒绝，通知仅列已登记且符合类型的产物。API按类型返回text/plain或旧媒体类型，保留原SHA/状态门禁；停止/未验/篡改无下载。此服务层反例只证明交付规则，不替代GUI轨迹/截图/Save/读回独立验收。

### VM最终派发门禁（实现前补充）

数据库authority与生命周期适配：在短事务内锁定同一desktop资源和task，核对desktop-textedit、RUNNING、owner/epoch/task绑定及未到期；用数据库当前时间计算剩余租约，保守映射到查询前host monotonic起点。不得持DB事务做HTTP。独立DesktopExecutionControl协调既有heartbeat→guest查询→新查authority→单次renew；停止/失权/DB或HTTP失败后实例锁止、关闭host控制文件并尝试guest revoke。分别返回本地/远端撤销确认，失败不伪称已停掉在途动作；不删除任务、不重放模型、不自动释放未知副作用资源。重启不沿用该对象续期，未来必须按已有桌面禁止自动resume规则处理。先以隔离PG+真实loopback HTTP验证，旧日报Worker与P5不改。

延迟授权细则：GET /lease另返回guest当前clockMs；网络renew必须携带notAfterMs（guest时域的绝对截止），到达时已过期直接拒绝，实际expiresAt取本地短TTL与notAfter的较早者。重复sequence必须绑定原ttl/notAfter，不能改变请求后重放延长期限。后端客户端先查guest时钟、再调用可信authority回调拿当前固定run/owner/epoch的monotonic截止（未来Worker从数据库执行权剩余时间换算，不接受模型提供）；扣除自查询起耗时和500ms余量后计算guest notAfter。请求只发一次、响应严格校验原身份/序号/期限；异常记录为未确认，不以HTTP成功猜正确，也不重放新序号。撤销独立执行且必须返回stopped=true，失败保留待核对。

此计算依赖host/guest时钟正常前进，不声称覆盖任意虚拟机冻结/时钟跳跃。guest现有倒退/过期拒绝仍保留。客户端先用本机实际HTTP和受控时钟验证，再接Worker真实数据库authority和VM隧道；后者未完成时禁止生产启用。

通信入口细则：新增仅绑定127.0.0.1的独立HTTP控制服务，预期通过既有经认证SSH隧道到guest loopback，不开放公网或改变SSH配置。每run使用独立随机控制token，不能复用model/verifier token；调用方不传路径/run/owner/epoch，身份由服务构造固定。只允许GET /lease及POST /renew、/revoke；请求体限4KiB、读超时2秒、拒绝额外字段和分块传输，日志不输出认证信息。错误只返稳定代码。失败或超时不能推断撤销成功，须查回原记录；同序号续期重试不延长，撤销幂等。

服务工厂不提供自动部署或生产CLI。当前先验证真实本机HTTP到许可存储再到最终门禁；worker发送权限期限、网络延迟上界及guest时钟校验尚未接通前，不授权真实桌面动作。网络入口测试不冒充VM隧道已连通。

许可控制端细则：guest可信控制端生成有效期，不直接采用host墙钟截止时间；每次授权最长30秒，固定run/owner/epoch，更新序号严格递增。重复序号只返回原记录、不延长有效期；过期、停止或时钟倒退后持久锁止，后续心跳不能恢复。记录私有、加文件互斥并原子替换；重建控制对象仍按原记录拒绝。撤销不依赖心跳序号，原固定身份可重复撤销，错误身份无权更新。此阶段先实现guest控制存储，随后才能接独立认证的网络入口；文件可用不冒充host→guest连通。

新增独立DesktopTask继承既有RealAppTask，不修改旧C0/C2/TextEdit源码。在每一次_admit（包括观察、Driver动作与result文件请求）进入原预算记账之前，从VM私有控制文件检查固定run/owner/epoch、未停止及未过期；任何缺失/不安全权限/符号链接/格式错误都拒绝派发。控制记录最多短租约，时间从VM当前时刻判断，host到guest授权传递仍须另行实现并核验，不声称本地文件等于网络撤销已接通。

准入首次失败后实例永久停派，不能等待时钟回退或替换许可自动续用。重启后沿用原run账本的停止状态；恢复须另行明确协议，不能创建新实例绕过停止。模型不获得控制文件路径、写权限或额外工具。正在执行的动作不承诺回滚，已有原始结果仍保留。验证先通过注入传输证明拒绝时零真实派发，再接可信授权传输及真实VM验证。

### 队列接入细则（实现前补充）

先复用payload中的显式kind做领取过滤，不迁移生产表或改旧日报请求摘要。缺少kind的旧记录只供日报Worker领取，desktop-textedit只供显式声明同类能力的领取者；未知/null kind均不能被默认领取。两个类型仍竞争同一个desktop资源锁，不能用分队列绕开桌面互斥。service入口拒绝未知kind，桌面正文再次按冻结契约校验。

新增POST /desktop-tasks的认证/幂等接口，但默认关闭，使用程序构造Settings的开发开关在隔离测试中验证；不提供生产环境启用开关，执行器完成之前生产返回503且不建单。普通POST /tasks继续只接受原日报格式；查询可返回明确kind。停止后从未领取的桌面任务可重新排队；只要已有attempt/session/调用证据，resume一律拒绝，直到有经过验证的现场恢复适配，不沿用日报恢复逻辑。

这只能证明新版类型隔离，不能使正在运行的P5旧二进制突然识别kind。P6与P5严禁共享新桌面队列；部署时必须先停止旧领取者并核对队列与版本，真实运行仍受上文P5隔离门槛约束。

| 要求 | 证明方式 |
|---|---|
| API到真实桌面闭环 | 原提交/任务/session/run绑定、真实AX/截图/动作、VM文件和下载SHA一致 |
| 正确而非自报成功 | 派发前冻结输入与期望，独立验证原轨迹、Save、新界面和完整读回 |
| 同桌面单执行者 | 类型间领取竞争与全局锁反例，过期owner在执行端拒绝；真实锁冲突不派发 |
| 停止/恢复不重放 | 排队停止、实际在途停止证据；未知输入或Save保持BLOCKED/UNVERIFIED |
| 旧日报不回退 | 原schema/幂等/提交/恢复/下载测试及最小实际兼容核验，声明各自范围 |
| P5不受影响 | 原工作树与冻结哈希不变；不迁移生产数据库、不重启P5服务；模型阶段另留切换恢复记录 |

纯单元、模拟执行、隔离PG和真实模型/VM分别记录；任意必需项未验证就不称P6完成。P7真实业务与P8易用性仅为后续方向，在本阶段结果及用户需求明确后分别另开分支写方案。
