# 单人本地任务服务（P2）

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

### 来源预览与七日回执（P5开发版）

本次操作者额度约束比通用QuotaPermit更严格：每批实时查询当前窗口，已用必须<70%（剩余>30%）；达到70%停止，不用积分或重置卡，不自动等重置续用。底层5%余量只是通用拒绝门槛，不是本次允许消耗95%的授权。首日两报告已核验，下一批10-04 12:10；完整七日验收仍未完成。

当前正式计划`1ab2e3a4-8426-48e8-bf1b-3452efa1fdfe`：北京时间2026-10-03 12:10开始、10-10 12:10满168h，每日一批两报告、最多7批。Codex当前聊天每日12:11跟进，每批新查额度，不能以自动化创建成功代替实际运行；需电脑和应用运行。仅P5分支保存开发进度，默认分支阶段验收等待真实观察。原短测计划不要重建或复用为正式观察。

`python -m backend.workflow_preview --branch p5-personal-workflows --baseline 完整起始SHA --cutoff 带时区截止时刻 --output 新目录`仅采集本项目Git和截止前24h元数据，保存两份来源及batch.json，不调用模型。复核后用batch-submit提交batch.json，复用稳定key；来源目录不允许覆盖。应在后端虚拟环境中执行，不把预览当真实模型报告。

`python -m backend.week_observer --schedule SCHEDULE_UUID --output /绝对路径/.runtime/backend/新回执目录`只读检查原计划、来源、任务、会话审计、用量、通知及产物下载，写新回执、不确认已读。它不派发、不授予额度，也不补跑失败；原来失败的回执保留。完整运行观察必须真实满168h、7个连续应执行日、14个唯一任务/会话且逐项验收通过；用户采用情况另记NOT_ASSESSED，不承诺连续在线168h。首次真实回执因API额外usage元数据比较过严失败，已修正并保留原失败；随后原短测两报告核对通过，但七日判定仍INCOMPLETE。

### 基础配置恢复失败

报告SUCCEEDED只表示业务核验通过，不代表Desktop配置恢复成功。若Worker输出 `RESTORE_PENDING_REQUIRES_IDLE_APP`，对应run会保留 `backend-restore-pending-*.json`；目前API任务状态不单独展示此告警。不要为恢复配置而resume已成功任务，也不要删除提示/账本或重复业务。先确认没有在途任务及其他App会话运行，再停止空闲Worker，由维护者使用原批准基础tasks执行现有runner的restore；它会再次检查App空闲且核对旧账本不变。配置恢复失败不得循环强制重试；保留失败记录，完成后另记成功，不覆盖原证据。新任务继续前应核对实际配置，不能仅以API /health判断。

测试：`.runtime/backend-venv/bin/python -m backend.manage test`，为每项创建并删除独立临时测试数据库。生产任务保留。实际证据及未测范围见 [P2 总结](../docs/stages/p2-summary.md)。此阶段没有开机自启、关闭 App 后执行、数小时持久性或多用户验收。
