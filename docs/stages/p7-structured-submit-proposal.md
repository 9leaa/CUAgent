# P7 结构化最终提交方案（用户已确认）

2026-10-08用户明确同意。沿p7-project-handoff阶段分支实施，先加入有界纯函数核验完整提交对象与原有效草稿/文档的一致性；随后接入执行端持久提交、预算/停止门禁、HTTP/Harness及独立验收。纯函数不授予执行或发布权限，未接齐之前不开放新工具、不部署或试跑。旧协议和旧失败保留；新协议必须显式版本化。

## 决策依据

2026-10-07继续核查：官方Messages扩展文档只解释附加字段传输与接受事务，不保证服务端生成JSON。官方源码639ed015的subagent-in-process-driver/structured.ts使用structured_output工具、schema校验、tools/result成功后提交及concludeTurn结束；并非最终文本格式约束。安装版0.2.0-rc.2对应lib/index.js摘要a169b6dac8f9fd0ef6e8db4ec0d2c009580c5c10b6d561e6d214cbe9b89521d1，同样存在该机制。本次未启动子Agent或真实推理。

参考：[官方扩展协议](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/deepseek-llm-api-wire-extensions.md)、[固定版结构化实现](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015/packages/subagent/subagent-in-process-driver/src/structured.ts)。传输可扩展不等于账户接口支持JSON模式；公开检索未取得本路由原生JSON约束的明确保证，也不能由此断言服务端绝不支持。

## 提议的契约变更

从“最终助手文本必须整体是JSON”改为“原模型在原会话调用唯一最终提交工具，提交完整报告对象”。不是从解释文字中截取JSON，不是程序复制预检草稿当模型提交。普通最终文字只用于展示，不计报告交付；未调用、调用失败或证据不完整一律不通过。此变更须用户确认，现有严格解析和所有历史失败保持原状。

## 确认后实现范围

- 沿当前P7分支先冻结实现方案，再增P7专用vm_submit_handoff；不启用子Agent、不改模型或官方主循环。P6工具集不变，新增能力明确进入P7白名单/请求审计。
- 只接受完整受限报告对象，绑定原run/session/input。VM检查既有草稿、GUI保存/关窗/重开、新观察、result写入并读回证据已齐；最后提交必须与预检原报告一致。工具不能提供任意文件路径、命令、网络或改历史证据。
- 进入同一执行端租约/停止/30raw账本；有效、无效提交都计数，不延长预算、不换会话。原预算不足即失败。仅在原调用结果成功后提交；结果未知禁止重发，沿原身份只读核对。
- 采用官方结束本轮接口及单调终态门禁，成功提交后拒绝后续副作用；并发、同响应后续工具、拒绝后继续、停止竞争均需测试。不能只靠提示词要求停止。
- guest原始调用/结果、官方会话原工具参数/结果、host独立schema/来源事实/草稿核对三方一致；报告由原模型参数取证。修改证据导出、验收和正式发布入口以显式标注新协议版本，禁止旧证据走新捷径。
- 仍需独立语义和截图审查、正式发布及下载字节核对；结构合法不代表报告正确。既有005失败不重判或补跑，剩余任务不自动换协议。

## 验证与交付

预设冲突修正（2026-10-08，代码前）：部署前全链检查发现cordis.desktop.handoff.patch.yml的persona仍无条件要求最终JSON。将其改成服从原任务显式完成协议：p7-tool-submit-v1必须完整report工具提交、成功后无总结；legacy仍仅最终JSON。新版用户prompt显式写协议标识，不依据工具猜版本；增加静态预设/新旧prompt一致性测试。已部署454da53的25个guest文件只作未激活文件包，改动仅宿主persona/prompt，后续冻结候选需记录host/guest版本差异及guest源码一致性，不能把部署回执写成业务通过。

生产组合细化（2026-10-08，代码前）：operator增加显式handoff_protocol（默认旧版），仅project-handoff允许新版，原单任务launch意图保存该版本；仍检查唯一未尝试QUEUED任务和新额度/原共享锁。HandoffTaskAdapter构造固定版本，prepare钩子将版本传给会话创建；新connection从该原私有创建记录读可信session并严格核对run/input/cwd/protocol，激活和verify沿同一版本。新联合验收后只写v2审核上下文，依然抛出语义审核待完成，不能直接发布。旧入口/旧队列默认行为不改，新实测必须显式新建候选任务后指定该版本，禁止升级旧005剩余任务。测试新旧adapter完整模拟证据与参数选择/未知版本拒绝，未通过不得实机派发。

创建前门槛细化（2026-10-08，代码前）：会话prepare显式protocol默认旧版，新版才在独占desktop-request加入版本；startHandoffSession仅接受旧字段或增加一个正确protocol字段，新版ready必须同时匹配session/protocol/十工具，错配在任何RPC之前拒绝。App启动ready期望同样核对可信连接的新字段。新prompt明确完整report提交、紧邻read_result、预算包含submit及失败未知不重发，移除旧最终文本JSON要求；旧prompt字节与九工具默认保留。此步只开放显式创建API，不自动修改现有队列或生产operator选择。

Harness终态细化（2026-10-08，代码前）：仅可信连接显式protocol=p7-tool-submit-v1且固定sessionId才注册完整report工具；旧连接不变。使用安装版ToolRuntime真实register/guard/concludeTurn/tools/result接口，不启用子Agent或PTC。提交HTTP派发前进入单调pending门禁，拒绝并发/后续所有工具及新模型请求；HTTP未知/失败不解除门禁、不重发，发送原stop。核对成功响应固定身份/协议/摘要/预算后调用concludeTurn；只有原execution的不可变tools/result成功且原输出一致才标committed，管线后置错误或取消仍锁止并stop，不能将HTTP成功当最终成功。完整report参数直接传VM保留原计费，参数schema使用现有HandoffResult及其defs。用安装版官方registry测试成功终态、同响应后续、并发、篡改/错误/丢失/取消和外层结果失败；新生产会话和prompt切换仍需后续贯通后才派发。

控制激活细化（2026-10-08，代码前）：bind_draft_session同时一次绑定可信protocol（默认旧），新协议才向独立控制端activate-handoff发送protocol；必须包含有效session，不接受模型端激活。VM激活在原独占意图后、新Task前独占写0600 handoff-submission-protocol.json，包含version/protocol/run/session/input，失败保持原激活不可重放。新提交轨迹导出必须带该原记录，guest核验、bundle读回和host联合入口都核对，缺失/替换拒绝。旧草稿session记录字段不变，旧协议不新建该文件。

工具入口细化（2026-10-08，代码前）：Task构造增加可信submission_protocol，默认legacy-final-json；只有显式p7-tool-submit-v1且绑定session才允许submit_handoff方法及HTTP操作。旧P7/P6不扩权。原HTTP单次提交走task锁/计费/stop/lease，完整report信封可用既有P7预检的512KiB上限，但规范report仍限制64KiB。先验证真实loopback请求、无权限/错误协议/拒绝/重复提交，再接控制端激活与模型注册；不靠模型参数切换协议。

审核/发布细化（2026-10-08，代码前）：审核上下文v1固定旧协议；新上下文v2必须显式protocol=p7-tool-submit-v1，字段集合严格校验，未知/缺失版本不回退。记录独立审核和准备发布都按此版本重新核验原任务请求/会话/guest/图像证据，必须与原execution完全一致；独立审核的executionSha256同时绑定协议结果。保留原审核失败/未通过/未知状态及禁止重放，不改变发布授权、数据库锁和产物字节门槛。

联合入口绑定细化（2026-10-08，代码前）：verify_handoff_execution增加可信protocol参数，默认旧协议。新协议必须在原私有desktop-request.json及desktop-session-binding.json同时存在相同protocol字段且身份/输入/cwd完全一致；不得从模型日志自动推断。提取、请求审计白名单、原guest双日志与host提交门槛使用同一版本，最终返回显式protocol与提交证据摘要；收尾重新读取创建记录/绑定和其他证据防变化。新模拟组合覆盖全套只读子进程与原文件，不开放模型入口；生产创建和后续人工审核入口稍后同步版本。

会话提取细化（2026-10-08，代码前）：extract_handoff_result增加可信调用者显式protocol参数，默认legacy-final-json保持旧行为，p7-tool-submit-v1才允许第10个工具。新协议报告只来自原assistant/message声明的vm_submit_handoff完整arguments，与对应tool/call原字符串一致；必须唯一末次调用、唯一成功结果、原模型/会话/请求和completed单轮，禁止提交后新模型消息/请求/工具。核对响应协议、身份、报告与文档摘要和预算范围。无提交即拒绝，绝不从tool/result或普通文本猜报告。生产路由仍不切换，待可信创建意图/绑定和联合验收入口一致后另接通。

trace/exchange接入细化（2026-10-08，代码前）：旧轨迹仍按旧协议处理；出现submit_handoff即要求原有效草稿和可信session，并核对唯一最后提交在成功read_result后紧邻发生，原参数与草稿完整对象一致、响应字段和摘要重算一致。提交结果前stop或之后新派发均拒绝。双日志按原参数/原结果增加vm_submit_handoff匹配；导出仍依赖既有草稿session私有绑定，不新增模型可写的身份。此兼容读取不允许旧业务失败按新协议改判，正式入口后续需显式新协议选择。

独立host证据门槛（2026-10-08，代码前）：不调用guest提交校验作为真值，使用host Pydantic及原draft证据核验重新计算完整报告/正文/摘要；要求提交为唯一末次raw，唯一原helper_arguments/result、连续预算、原run/session/input绑定和紧邻成功read_result。官方日志必须有唯一匹配vm_submit_handoff调用及成功结果，完整参数/响应一致且后续零工具调用；stop先于提交完成则拒绝。此门槛返回仅SUBMISSION_EVIDENCE_MATCHED，不代表完整会话真实性、截图语义或发布通过，之后仍需接完整trace/export/session联合入口。

执行端提交设计细化（2026-10-08，代码前）：原Task记录成功write_result与紧邻成功read_result；任何其他准入调用使读回绑定失效。submit_handoff自身先计一次原raw，再核对可信session、输入/保存/重开标记、原文档与reopen摘要、原文档逐字节等于预检document、刚读回内容等于document+LF。提交前在dispatch锁内再次核对stop/lease；原helper_arguments与result用既有fsync审计写入，成功result作为原提交凭据。内存终态先锁止，审计写失败则stop，不能重试或宣告成功；跨进程沿既有非零预算即停止的恢复规则，旧记录不会自动恢复执行。此步只新增未开放方法，必须补齐独立证据核验和官方结果后结束本轮，才能注册模型工具。

先做安装版适配及无模型反例：提交前置缺失、报告被替换、错误session、双提交、同响应提交后动作、结果失败/未知、停止和预算耗尽；再做完整原Task/模拟Driver/独立导出验证。通过后才固定新候选，并按原额度/模型/VM限制运行完整三组真实业务。失败保留，不以模型前缀被忽略替代业务验收。README/PROGRESS、提交推送继续随实现同步。
