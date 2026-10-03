# 单人本地任务服务（P2）

P6消息证据：原用户prompt必须唯一且rpcId匹配。官方默认repeat-tool-reminder的3/5/8次提醒，只有来源/form、完整固定模板、已完成的同名同参数调用链均匹配才单独计为frameworkNotices；未知来源、自定义阈值/模板或额外用户指令继续拒绝。JS观测/原字节归档与Python独立验收共享模板策略，不删除会话行、不关闭提醒。归档被取消的会话不代表业务成功；若含无完整用量的assistant/attempt，usage仍unknown/null，不将此前部分token冒充完整总量。

## P6 独立队列服务

`backend.desktop_service init` 创建新私有目录、新数据库和独立token，只引用现有私有backend.env；不修改原库、不复制App凭据、不启动Worker/模型。新目录的父目录须已存在且仅当前用户可访问。端口只允许18100–18999，固定监听127.0.0.1；占用则拒绝，不停止已有服务。

```sh
python -m backend.desktop_service init --baseline-env /absolute/path/backend.env --root /absolute/private/parent/p6-service --port 18100
python -m backend.desktop_service serve --profile /absolute/private/parent/p6-service/service.json
```

初始化失败保留新目录和初始化意图，不能删除重建或对同一目标盲目重试。服务进程前台运行，停止再以原profile启动会保留原任务。配置及token不能上传GitHub。此服务只接受桌面提交，拒绝日报/批次/定时任务写入；API能接收任务不代表有人执行，**新任务先排队，需下方单任务Worker另行准入**。原P5环境和18089默认服务不变。

## P6 受控单任务执行命令

```sh
python -m backend.desktop_operator worker-once --profile /absolute/private/parent/p6-service/service.json --execution /absolute/private/execution.json --quota /absolute/private/current-quota.json --task TASK_UUID --cutover-approved
```

这是可信操作者入口，不是模型工具。必须已进入批准的切换窗口、停下原P5领取者、确认VM就绪；命令不自行停启P5或解锁VM。它在原共享锁内检查后只领取指定任务，执行原官方App/Flash-off/30raw链路并独立核验、恢复App。不得用另一个共享锁绕开P5，不能因API已启动而批量授权。

`execution.json` 为0600操作者配置，仅接受：`version=1`、`node`（规范可执行路径）、`officialHome`（原私有App home）、`buildTools`（当前用户所有且组/他人不可写的依赖目录）、`knownHosts`、`askpass`、`guestCommit`（已部署40位commit）、`guestManifestSha256`（原部署64位SHA）、`tunnelPort`（19000–19999）。不会自动部署或接受任务传入的路径/模型设置。

`current-quota.json` 必须来自本次真实Codex用量工具读取，0600，不能复制示例/旧读数或填造数据。字段严格为：`version=1`、`taskId`、`profileSha256`（service.json原字节SHA256）、`source="Codex get_usage_limits"`、带时区的`checkedAt`/`expiresAt`（至多五分钟）、`remainingPercent`、`ordinaryUsageAllowed`、`creditsBalance`、`resetCardsUsed`。余额基准62494.0260570000，普通额度可用且剩余≥40%、卡未用方可进入；缺失/过期拒绝，真实触线在原共享运行目录持久写desktop-operator-stop.json，自然重置不解锁，禁止手动删除绕过。原P5 scheduler停止锁同样生效；这不限制DSH平台余额。

准入、准备、App切换及正式prompt前会重新检查：原P5无排队/在途/未释放资源、未来30分钟无到期计划、旧Worker进程不存在、VM身份正确且已解锁、绑定额度未过期或变更。操作意图和结果存在独立service/admission目录；有attempt的任务或已有启动意图不能再次运行。`EXECUTION_RECORDED`只表示收到了结果，必须读取outcome.status、restoreConfirmed和quarantined；未知/隔离不得重放，不能换任务掩盖失败。确认原App恢复和无隔离后，由本次切换操作者恢复原P5领取者。本命令目前经过隔离PG/模拟VM边界测试，尚待通过正式命令运行同版三例，不把历史私有脚本验收当作新入口验收。

## P6 桌面提交命令（开发入口）

客户端新增 `desktop-submit --spec --key`。JSON 只接受下面两个字段；1–10 条单行文本，拼接正文含末尾换行最多4096 UTF-8字节。文件必须为普通UTF-8 JSON且不超过32768字节，不接受链接、重复字段或额外权限参数。

```json
{"kind":"desktop-textedit","lines":["项目：交接","下一步：核对结果"]}
```

已配置隔离后端的开发环境中，用其 Python 运行：

```sh
python -m backend.client desktop-submit --desktop-service /absolute/private/parent/p6-service/service.json --spec /absolute/path/desktop.json --key desktop-001
python -m backend.client status --desktop-service /absolute/private/parent/p6-service/service.json --task TASK_UUID
python -m backend.client stop --desktop-service /absolute/private/parent/p6-service/service.json --task TASK_UUID
python -m backend.client download --desktop-service /absolute/private/parent/p6-service/service.json --task TASK_UUID --name document.txt --output .runtime/document.txt
python -m backend.client download --desktop-service /absolute/private/parent/p6-service/service.json --task TASK_UUID --name result.txt --output .runtime/result.txt
```

提交只发送一次；超时不代表未创建，先查列表/原任务，必要时沿用原内容及原键核对，不换键制造重复任务。下载须任务成功且原文件哈希一致。每条命令显式指定同一`--desktop-service`；省略时仍走旧环境/18089，不自动选择P6。默认API仍503，只有显式独立服务开放提交；不能自行开启P5桌面队列。现有日报命令与默认行为不变。

P6产物交付开发：桌面类型仅登记/下载`document.txt`和`result.txt`，需独立结果kind/session匹配、两文件齐全、SHA及冻结正文一致；STOP_REQUESTED不能转成功。CLI download新增这两个名字，需显式`--name`；日报名字/媒体类型保留。通知只列已登记且符合任务类型的文件，缺文件不会凭成功状态制造链接。桌面Worker、VM证据采集及独立核验代码已组合，但只完成本地/合成证据/隔离PG验证，真实GUI闭环尚未验收。

P6分支开发状态：已提供`POST /desktop-tasks`契约（`kind=desktop-textedit`及1–10条`lines`），旧默认API仍503、不创建桌面任务；上方独立服务显式开启提交，但没有自动执行。新版默认Worker仅领取无kind的旧日报；显式桌面领取者与日报竞争同一desktop资源。查询新增kind，底层桌面从未领取的排队停止可恢复，但独立服务不开放resume；有执行证据则拒绝恢复，不能套用下方日报resume说明。不能用接口测试称完整桌面功能已上线。P5旧服务不得接入该新类型队列。

P6专用SSH：`desktop_ssh.create_ssh_wrapper(root=私有目录, known_hosts=原私有主机密钥文件, askpass=原私有可执行认证脚本)`生成新的0700传输脚本，只引用凭证路径且保留stdin。`DesktopTaskAdapter`通过显式known_hosts/askpass自动生成；离线部署准备代码调用`deploy_guest`时也须传该生成器返回路径，不能复用旧vm-ssh（它丢弃stdin）。本机1MiB往返与ssh -G解析通过不等于VM连接通过。实际执行仍需上方操作者入口核对切换许可、VM状态、剩余额度≥40%，且遵守P5隔离；没有自动部署或自动启用开关。

专业上是 FastAPI + PostgreSQL 持久队列 + 独立 Worker；直白说：提交后拿任务编号，后台执行，随后查日志、停止或下载核对过的报告。Harness 仍负责唯一的模型循环。仅日报模板、本机单用户；不是公网多租户服务。

## 启动

在仓库根目录执行。需要已完成项目 Desktop/A1 配置、私有 developer cookie、Docker、Python 3.12 和 Node。固定依赖见 requirements.lock；已有环境不要重复 init。init 中的基础任务与 cookie 路径对应本项目现有验收环境，其他环境须先准备自己的授权配置，不能复制凭证。

```bash
uv venv --python 3.12 .runtime/backend-venv
uv pip sync --python .runtime/backend-venv/bin/python backend/requirements.lock
.runtime/backend-venv/bin/python -m backend.manage init
.runtime/backend-venv/bin/python -m backend.manage db-up
.runtime/backend-venv/bin/python -m backend.manage migrate
.runtime/backend-venv/bin/python -m backend.manage api
```

另一个终端启动独立 Worker（加 `--once` 只领取一次）：

```bash
.runtime/backend-venv/bin/python -m backend.manage worker
```

API 127.0.0.1:18089；独立数据库 127.0.0.1:55432，不改现有 5432/Redis。凭证自动保存为忽略的 `.runtime/backend.env`，权限 0600，不提交、不输出。`/health` 只表示数据库可连，不证明 Desktop/模型或完整任务可用。Worker 切换批准配置时要求 App 全部空闲；执行结束恢复基础 A1 配置。不要同时手动运行其他 Desktop 测试。

## 使用

```bash
.runtime/backend-venv/bin/python -m backend.client submit --spec agent/fixtures/daily-report/spec.json --key my-daily-001
.runtime/backend-venv/bin/python -m backend.client list
.runtime/backend-venv/bin/python -m backend.client status --task TASK_UUID
.runtime/backend-venv/bin/python -m backend.client events --task TASK_UUID
.runtime/backend-venv/bin/python -m backend.client stop --task TASK_UUID
.runtime/backend-venv/bin/python -m backend.client resume --task TASK_UUID
.runtime/backend-venv/bin/python -m backend.client download --task TASK_UUID --name report.md --output .runtime/my-report.md
```

用返回的 UUID 替换 TASK_UUID。请求结果不明时复用原 key；同 key 同正文返回原任务，不同正文 409。输入 spec 使用同目录简单文件名；不接受任意绝对源路径。下载必须新文件，核对响应 SHA，只有 SUCCEEDED 产物开放。

排队停止为 STOPPED；运行停止先 STOP_REQUESTED，执行端立即拒绝新派发，已经开始的调用保留事实。resume 不是重新开始：保留任务/session/30 次总预算，只重新领取并查询原会话。原会话创建、配置切换或写入结果不明时停在 BLOCKED/UNVERIFIED，不盲目重放；完整故障恢复属于 P3。

日志提供工具名、callId、耗时、错误码、产物哈希，不开放提示词和源材料；用量单列缓存 token，不根据 token 猜货币金额。实际模型固定 DeepSeek 4.1 Flash/off，无其他模型回退。

P3可在输入spec加`releaseAt`（必须带时区，例如`2026-10-03T09:00:00+08:00`）。第一轮只生成JSON草稿，状态转为WAITING_RELEASE并释放资源；到点由持续运行的Worker领取同一任务完成Markdown。等待中停止后再恢复不会提前发布，工具端也拒绝提前渲染/普通写入绕过。数据库需迁移至0004。真实1小时、8小时及重启恢复已通过，见[P3总结](../docs/stages/p3-summary.md)；这不是连续8小时推理，也不承诺未启动Worker时自行唤醒机器。

P5开发版可在spec/API正文显式加入`"inputMode":"aggregate"`，使用P4已验证的受控输入聚合；不填写保持旧行为，旧幂等键不变。不可与releaseAt组合，已有任务不能更换模式。原聚合会话终止后只重新核验，不自动续跑；不完整产物记UNVERIFIED。两类实际来源采集位于`backend/workflow_sources.py`，真实报告及下载核对已通过。

### 批次（P5开发版）

数据库迁移至0005后，`POST /batches`接受`{"tasks":[任务正文1,任务正文2]}`（2–3项、整批请求最多262144字节），与/tasks使用相同认证和Idempotency-Key。完整校验后事务写入整批；同键同正文返回原批次，不同正文409。`GET /batches/批次UUID`返回逐任务状态、用量和产物；全部独立成功才显示SUCCEEDED，混合失败显示COMPLETED_WITH_ERRORS。每项仍独立30raw、串行执行，不共享或重置预算。

```bash
.runtime/backend-venv/bin/python -m backend.client batch-submit --spec .runtime/batch-body.json --key my-batch-001
.runtime/backend-venv/bin/python -m backend.client batch-status --batch BATCH_UUID
.runtime/backend-venv/bin/python -m backend.client batch-stop --batch BATCH_UUID
```

批次JSON中的tasks是内联任务正文，不是任意文件引用。停止按现有单任务边界逐项持久执行，保留已完成项；中途失败可用原batch再次stop完成剩余项，不承诺跨任务的原子停止、不新建任务。下载沿用各任务的原下载入口。真实两任务批次及重复请求已通过；周期计划尚未交付。

### 本地通知（P5开发版）

迁移至0006后，新任务的成功、失败、阻塞、待核验或停止终态事件与通知同事务保存，不追补历史记录、不复制输入/提示。`GET /notifications?after=0&limit=100&unread_only=true`按游标查询；`POST /notifications/通知ID/read`幂等标为已读。两个接口沿用认证。发生时状态与当前状态分开，恢复后的历史通知不能当成当前成功；下载仍受原状态和SHA检查，不因通知而绕过。

```bash
.runtime/backend-venv/bin/python -m backend.client notifications --unread-only
.runtime/backend-venv/bin/python -m backend.client notifications --after 0
.runtime/backend-venv/bin/python -m backend.client notification-read --notification 2
```

只在你确实要确认该通知时执行已读命令。真实停止通知在API重启后保留，重复确认不改变首次已读时间；新真实成功通知及其两产物链接核验通过。这里是本服务内收件箱，不是邮件、聊天消息或系统推送；读取接口不会暗中标记已读，也不等于用户已采用报告。

### 周期调度（P5开发版）

0007迁移后，计划API/CLI和实际到期短测已通过。固定UTC每24小时、1–7次，保存IANA时区；跨夏令时不保证相同本地钟点。到期后10分钟仍未取得许可记MISSED，不补派；PREPARING采集最多60秒，超时保留PREPARATION_EXPIRED且不重采。暂停与最终提交按同一行锁排序，已提交的批次需要另行stop；EXHAUSTED仅指次数用尽，不代表其任务成功或一周验收完成。

计划源快照与批次/任务同事务提交；采集本身不占数据库锁。只读本项目指定分支的Git事实和到期前24h任务元数据，两个固定工作流不开放任意命令/路径。创建前准备JSON：startAt为未来7日内带时区时刻、timezone为匹配的IANA时区、runs为1–7整数、branch为harness-migration或p5-personal-workflows、baselineCommit为该分支上的完整40位起始SHA。超20个提交或100条任务拒绝缩减样本，记来源错误。

```bash
.runtime/backend-venv/bin/python -m backend.client schedule-create --spec .runtime/schedule.json --key my-schedule-001
.runtime/backend-venv/bin/python -m backend.client schedule-list
.runtime/backend-venv/bin/python -m backend.client schedule-status --schedule SCHEDULE_UUID
.runtime/backend-venv/bin/python -m backend.client schedule-pause --schedule SCHEDULE_UUID
.runtime/backend-venv/bin/python -m backend.manage scheduler --once
# 持续观察计划，不负责模型循环；模型仍由原Worker执行
.runtime/backend-venv/bin/python -m backend.manage scheduler
```

API为POST/GET /schedules、GET /schedules/ID和POST /schedules/ID/pause，使用原认证及创建幂等键。创建计划不创建额度许可。调度器只读取私有后端根目录的scheduler-permit.json：需由操作者实时查询账户后记录version=1、scheduleId、dueAt、checkedAt、expiresAt、ordinaryUsageAllowed、remainingPercent、creditsBalance、resetCardsUsed；时刻均带时区，许可最多5分钟且只匹配这一期，余量须大于5%，积分基准62494.0260570000不变且未用重置卡。文件/父目录必须私有，拒绝链接；无记录或过期不会派发。该记录是操作确认，不是项目直接连接Codex账户；不要复制旧额度读数或预授权七天。

调度器重启不会重做已登记发生；源准备进程退出后保留失败，不自动补样。可撤销许可或暂停计划，已提交任务另行stop。短测原计划06388638-8839-4ee3-baa6-79704a2a6f51仅1次，已EXHAUSTED，许可已撤销；不等同正式一周，也不表示机器睡眠时会自动唤醒。

只读长测观察器：`python -m backend.soak --task TASK_UUID --seconds 3600 --output /绝对路径/.runtime/backend/新的证据目录`（在后端虚拟环境内执行；8小时用28800）。它不提交模型请求、不修改时钟、不重启服务；要求真实观察满时长、等待证据不变、到期执行、API/Worker至少各两组实际存活PID及最终独立验收。重启由操作者另行执行并确认安全空闲。只生成采样不等于PASS，以verification.json为准；目录已存在则拒绝覆盖。

### 操作员额度入口

先用账户工具查询真实额度，将单期检查记录保存为新的私有JSON（0600）：version=1、scheduleId、dueAt、checkedAt、expiresAt（最多5分钟）、ordinaryUsageAllowed、remainingPercent、creditsBalance、resetCardsUsed。该记录不是命令自行查询或验证账户真实性的结果；不能复制旧读数。执行：

```bash
.runtime/backend-venv/bin/python -m backend.schedule_operator grant --schedule SCHEDULE_UUID --quota .runtime/新检查记录.json
.runtime/backend-venv/bin/python -m backend.schedule_operator revoke --schedule SCHEDULE_UUID
```

必须核对JSON的result为GRANTED才算放行，退出码0也可能是明确拒绝。grant检查私有文件、时效、原计划确已到期且尚未发生、本次剩余≥40%、原积分余额和未用重置卡；拒绝重复活许可，文件锁防并发，许可原子替换，每次操作新建回执。达到停止线/普通额度不可用/积分变化/重置卡使用时写入scheduler-operator-stop.json并撤销许可，之后重启或自然额度重置也不能再grant；工具没有清除标记的命令，恢复需用户另行授权。不要绕过入口直接手写运行时许可。revoke可重复执行，不会撤销别的计划许可；已提交任务仍需原batch-stop。进程异常最多依赖原5分钟期限失效，不承诺自动取消模型在途动作。当前定时跟进已改用这个入口；176项后端回归通过，真实旧记录和已发生首期拒绝授权、撤销回执核验，零新增模型任务。

### 来源预览与七日回执（P5开发版）

本次操作者额度约束比通用QuotaPermit更严格：每批实时查询当前窗口，剩余必须≥40%（含40%）；低于40%停止，不用积分或重置卡，不自动等重置续用。底层5%余量只是通用拒绝门槛，不是本次允许消耗95%的授权。首日两报告已核验，下一批10-04 12:10；完整七日验收仍未完成。

当前正式计划`1ab2e3a4-8426-48e8-bf1b-3452efa1fdfe`：北京时间2026-10-03 12:10开始、10-10 12:10满168h，每日一批两报告、最多7批。Codex当前聊天10月3日每2小时（偶数小时11分）检查，10月4日首次唤醒后改为每6小时（00:11/06:11/12:11/18:11），每批新查额度，不能以自动化创建成功代替实际运行；需电脑和应用运行。仅P5分支保存开发进度，默认分支阶段验收等待真实观察。原短测计划不要重建或复用为正式观察。

`python -m backend.workflow_preview --branch p5-personal-workflows --baseline 完整起始SHA --cutoff 带时区截止时刻 --output 新目录`仅采集本项目Git和截止前24h元数据，保存两份来源及batch.json，不调用模型。复核后用batch-submit提交batch.json，复用稳定key；来源目录不允许覆盖。应在后端虚拟环境中执行，不把预览当真实模型报告。

`python -m backend.week_observer --schedule SCHEDULE_UUID --output /绝对路径/.runtime/backend/新回执目录`只读检查原计划、来源、任务、会话审计、用量、通知及产物下载，写新回执、不确认已读。它不派发、不授予额度，也不补跑失败；原来失败的回执保留。完整运行观察必须真实满168h、7个连续应执行日、14个唯一任务/会话且逐项验收通过；用户采用情况另记NOT_ASSESSED，不承诺连续在线168h。首次真实回执因API额外usage元数据比较过严失败，已修正并保留原失败；随后原短测两报告核对通过，但七日判定仍INCOMPLETE。

### 基础配置恢复失败

报告SUCCEEDED只表示业务核验通过，不代表Desktop配置恢复成功。若Worker输出 `RESTORE_PENDING_REQUIRES_IDLE_APP`，对应run会保留 `backend-restore-pending-*.json`；目前API任务状态不单独展示此告警。不要为恢复配置而resume已成功任务，也不要删除提示/账本或重复业务。先确认没有在途任务及其他App会话运行，再停止空闲Worker，由维护者使用原批准基础tasks执行现有runner的restore；它会再次检查App空闲且核对旧账本不变。配置恢复失败不得循环强制重试；保留失败记录，完成后另记成功，不覆盖原证据。新任务继续前应核对实际配置，不能仅以API /health判断。

测试：`.runtime/backend-venv/bin/python -m backend.manage test`，为每项创建并删除独立临时测试数据库。生产任务保留。实际证据及未测范围见 [P2 总结](../docs/stages/p2-summary.md)。此阶段没有开机自启、关闭 App 后执行、数小时持久性或多用户验收。
