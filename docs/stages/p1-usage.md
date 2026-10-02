# P1 日报使用方法

适用于本项目已配置的官方 Desktop 0.2.0-rc.2 和 A1 私有环境。输入可以换成自己的记录；开始时复制快照，源文件不由模型修改。第一版支持 1–3 份 Markdown 进展记录和 1–2 份 CSV，记录格式见 [例子](../../agent/fixtures/daily-report/progress.md)。输入文件名使用英文字母、数字、连字符/下划线，全部与 spec.json 同目录。数值列最多 4 列；超出全文读回规模的任务在准备时拒绝。

技术上是任务准备、官方会话执行、独立结果验证三个步骤；直白说，先装好这一单的资料，再让模型做，最后程序核对。当前模型生成 JSON，专用工具读取 JSON 并确定性生成 Markdown，模型再读回两份文件；此工具的内部读和写分别计一次预算。

在 `/Users/zhangchengjie/CUAgent` 执行；RUN 必须是未使用的新目录。准备不调用模型：

```bash
export RUN=/Users/zhangchengjie/CUAgent/.runtime/runs/my-daily-001
python3 agent/daily_report.py prepare \
  --spec /Users/zhangchengjie/CUAgent/agent/fixtures/daily-report/spec.json \
  --run-dir "$RUN"
```

将 COOKIE 和 BASE 指向项目现有私有登录 cookie JSON 与 A1 tasks.json。cookie 文件仅含登录信息、权限 0600，不能放进模型 workspace 或上传 Git。BASE 是要保留的原批准任务配置，包含原账本；不会清零旧预算。

```bash
export CUAGENT_DSH_COOKIE_FILE=/absolute/private/developer-cookie.json
export BASE=/absolute/private/tasks.json
node agent/harness/daily-report-runner.mjs activate "$BASE" "$RUN"
node agent/harness/daily-report-runner.mjs start "$RUN"
node agent/harness/daily-report-runner.mjs poll "$RUN"
```

activate 会检查 App 全部会话空闲，正常退出并用合并后的任务配置重启。新任务加旧任务不能超过 20 个。start 使用专用 p1-daily-report preset 的五个工具，固定 DeepSeek 4.1 Flash / off，不静默回退；它只提交一次，记录请求后即使超时也不得重新 start。poll 查询同一会话，看到 terminal=true 后才验证；RUN/session.jsonl 为官方原会话记录。

```bash
python3 agent/daily_report.py verify --run-dir "$RUN"
# 如需停止，取消之后继续 poll，不能将取消响应当作副作用已撤销。
node agent/harness/daily-report-runner.mjs cancel "$RUN"
# 所有任务终止后恢复原 A1 配置：
node agent/harness/daily-report-runner.mjs restore "$BASE"
```

SUCCEEDED 才表示来源、内容、统计、写入、完整读回及预算/模型轨迹均一致；产物在 RUN/workspace/report.json 和 report.md。UNVERIFIED 会保留原文件与原因，不能把模型“完成”视为成功。当前 Markdown 空行也严格验收，格式偏差会拒绝；真实评测失败不修改原产物补成成功。日志位于 RUN/audit 与 RUN/session.jsonl，包含私有内容，公开时只使用脱敏摘要。

无凭证测试及新固定评测准备：

```bash
python3 -m unittest discover -s agent/tests -p 'test_daily_report.py'
python3 agent/daily_benchmark.py /absolute/new-private-suite
```

生成 20 个输入和批准任务，schedule.json 在首次模型调用前固定；按上述 activate/start/poll 分批串行运行，最多 17 个新任务加旧三个。全部终止后 `python3 agent/daily_benchmark.py /absolute/new-private-suite --report` 核对所有原样本并统计失败用量。基准是合成输入，不能代替一周真实个人使用，也不证明任意格式理解。
