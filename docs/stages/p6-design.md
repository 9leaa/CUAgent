# P6：将受控桌面任务接入个人任务服务

2026-10-03，用户批准后续计划并授权执行。分支 `p6-desktop-task-service`，起点 `8bd099e`；独立工作目录 `/Users/zhangchengjie/CUAgent-p6`。方案先提交，再实现。P5七日观察未完成，P6不得取代或提前宣告P5通过。

## 目标和非目标

专业目标：任务类型化、按类型执行/核验、统一持久生命周期。直白说：像提交日报一样提交一个测试VM里的TextEdit任务，随后查询、停止并下载经过独立核对的结果。

复用官方Harness唯一Agent循环、现有VM桥接与TextEdit验证器。第一种任务仅把1–10条用户指定的纯文本交接内容按原顺序逐行保存；不承诺开放式总结、任意应用、创建任意宿主文件、GUI长任务或无人值守解锁。DSH固定Flash/off、单任务30次实际请求，失败/观察/内部请求均计数。C3/第二人、O0、多Agent、跨机器与新桌面壳仍不做。

## 隔离与发布

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
