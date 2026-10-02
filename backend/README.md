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

P3 开发版可在输入 spec 加 `releaseAt`（必须带时区，例如 `2026-10-03T09:00:00+08:00`）。第一轮只生成 JSON 草稿，状态转为 WAITING_RELEASE 并释放资源；到点由持续运行的 Worker 领取同一任务完成 Markdown。等待中停止后再恢复不会提前发布，工具端也拒绝提前渲染/普通写入绕过。数据库需迁移至0004。短时间真实闭环已通过，1/8小时仍待证据，不承诺未启动 Worker 时自行唤醒机器。

只读长测观察器：`python -m backend.soak --task TASK_UUID --seconds 3600 --output /绝对路径/.runtime/backend/新的证据目录`（在后端虚拟环境内执行；8小时用28800）。它不提交模型请求、不修改时钟、不重启服务；要求真实观察满时长、等待证据不变、到期执行、API/Worker至少各两组实际存活PID及最终独立验收。重启由操作者另行执行并确认安全空闲。只生成采样不等于PASS，以verification.json为准；目录已存在则拒绝覆盖。

### 基础配置恢复失败

报告SUCCEEDED只表示业务核验通过，不代表Desktop配置恢复成功。若Worker输出 `RESTORE_PENDING_REQUIRES_IDLE_APP`，对应run会保留 `backend-restore-pending-*.json`；目前API任务状态不单独展示此告警。不要为恢复配置而resume已成功任务，也不要删除提示/账本或重复业务。先确认没有在途任务及其他App会话运行，再停止空闲Worker，由维护者使用原批准基础tasks执行现有runner的restore；它会再次检查App空闲且核对旧账本不变。配置恢复失败不得循环强制重试；保留失败记录，完成后另记成功，不覆盖原证据。新任务继续前应核对实际配置，不能仅以API /health判断。

测试：`.runtime/backend-venv/bin/python -m backend.manage test`，为每项创建并删除独立临时测试数据库。生产任务保留。实际证据及未测范围见 [P2 总结](../docs/stages/p2-summary.md)。此阶段没有开机自启、关闭 App 后执行、数小时持久性或多用户验收。
