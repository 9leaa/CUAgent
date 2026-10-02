# A1 业务及部分生命周期验收记录

2026-10-02，分支 `a1-agent-expansion`。此文件保留原业务/生命周期过程；最新 A1 本地验收已完成，见 [本地总结](a1-summary.md)，C3 和第二人仍未验。

## 当前结果

| 范围 | 实际证据 | 结论 |
|---|---|---|
| 三份新文本 | 新 project/meeting/ticket synthetic 输入；实际读取、字段提取、来源引用、JSON/Markdown 写入及完整读回；独立逐字段和字节 SHA 检查 | SUCCEEDED，8 次真实工具 |
| sales.csv | 实际统计行列、count/missing/sum/min/max/mean；JSON 全字段、Markdown 全表格和来源 SHA；写入后读回，关联官方 call/result 与审计 | SUCCEEDED，5 次真实工具 |
| 实际多会话 | 两个同时执行的官方模型会话，各自授权工作区/账本；官方请求清单恰好六工具；独立关联 session/run/call | 本次业务无串扰，非法会话/路径另有注册集成拒绝测试 |
| 重启续接 | 正常退出前官方 API 确认空闲；原 session/模型恢复，预算 8→8、5→5；各真实读一次后 9、6 | PASS |
| 手动压缩 | 官方 `/compact` 命令、compaction summary/end 与 command/done；16 历史项约 3083 tokens；压缩不派发业务工具 | PASS，预算 9→9，压缩后读回 9→10 |
| 原证据保护 | 验证时的 session/audit 原字节前缀冻结于任务根之外，后续校验与原报告 SHA 一致 | PASS |
| preset 切换 | 新任务首轮前 controlled→readonly，真实模型清单只有四工具；standard 禁用，首轮后切换 locked | PASS，只读 1/30，切换时原预算 10/6 不变 |
| 工具图片与直接图片 | 随机 PNG 独立像素/答案、颜色文件完整读回及 SHA、官方附件/call/result 核对 | PASS，CSV 6→9→11 |
| 真实取消 | 第 12 次派发后标准官方 cancel，turn/end aborted/user；取消请求及确认后无新派发 | PASS，不冒充点击 UI Stop |
| 预算耗尽与重启 | 原任务继续 18 次实际调用到 30，第 31 次拒绝；正常重启后仍 30，再次实际调用请求被拒 | PASS，原账本未清零 |
| 通用插件及流程 | opt-in fingerprint 示例/schema/错误/取消/图片转换说明；等效流程不授权；正常和拒绝注册集成 | 已提供；第二人按用户确认暂缓、未验 |

专业解释：真实官方会话事件、写前持久准入账本、保护的独立 oracle 和产物字节四方交叉核对。直白说：不仅文件看起来对，还证明模型真的读了输入、调了工具、写了结果并读回来；重启和压缩没有赠送次数。

## 环境、命令和原尝试

- 官方 Desktop `0.2.0-rc.2`，同版源码参考 `639ed015`；模型 `deepseek-account/deepseek-flash` / reasoning high。复用官方 UI、会话、主循环、附件和 Cordis，不增加另一套 Agent loop。
- 新批次 `a1_business_20261002_001`，两个 run 后缀 `texts`/`csv`；私有批准配置、预存期望、审计及验证报告留在 `.runtime/runs/<batch>`，不上传凭证/完整会话。创建前确认原 124 会话都无活动轮次；正常退出/重新启动 App，不停止 VM 或修改 SSH/VNC。
- `node agent/prepare-a1-validation.mjs <new-batch-id>` 创建独立新根和 0600 配置，不覆盖已有任务。实际 RPC 请求 ID 派发前保存，遇到观察超时不得直接再发同一任务。
- `node --test agent/tests/*.test.mjs` 59/59；同版官方注册集成 25/25、Python 103/103 为无模型测试，不能拿它代替本表的真实业务或 VM 证据。
- 文本第一次内容验收未通过：验证器漏算最后一条记录之后的空行；任务预先要求每条记录后空行，模型产物符合。严格 oracle 修正为两个末尾换行，并加反例/格式断言；原输入、产物、请求与调用数不变，失败说明保留。
- 压缩首次接入未通过：preset 内 compaction 服务未放入隔离域，上游在恢复时拒绝。按同版源代码改为 `cordis:group` / `isolate.compaction=true`，正常重启，保留失败与原预算。官方 compact 实际命令只由开发侧发起，不开放给模型工具。
- 命令目录只读检查最初参数映射错误，返回 `gateway/arguments-invalid`；查同版 Agent wire 定义后使用 `agentId`，没有用错误调用的返回值冒充有效命令目录。
- preset 首个 verifier 将初始 preset 当作切换事件而失败；实际初始值在 session header，按 header/create 响应及唯一 selected 事件核对通过，原事件/失败保留。
- 扩展示例测试发现官方丢失普通 Error.code；将已知受控文件错误转为同版 HarnessError，注册测试独立核对 PARENT_PATH_DENIED/NUMERIC_OVERFLOW。额外参数发布封闭 schema 并在正文拒绝，不改为忽略错误码或非法字段。
- 新私有报告 `a1_preset_20261002_001/verification.json`、业务 CSV `images-verification.json` 和 `stop-budget-verification.json` 均 PASS；对应请求、失败、PNG、原账本及会话保留，不公开完整会话或账号数据。

## 本地收口与暂缓项

启动预检与运行时现已统一审批校验；新增缺失/非法审批和示例政策卸载反例通过。正常重新加载 App 后原三个预算仍 10/30、30/30、1/30。C0 回归前曾发现原 SSH 地址超时且 VM stopped；用户确认后启动原 VM，以全新 run 完成真实计算器/HTTP拒绝/持久预算/在途停止并独立读回原证据，不用历史 VM 成绩替代。

当前 App 为 A1；文本/CSV/只读任务累计 10/30、30/30、1/30。CSV 已耗尽，不能再派发或清零。插件卸载/重载、配置改写和非法会话由真实注册集成覆盖，App 重启/压缩/preset、图片/取消/预算由真实官方模型覆盖，不能混称每项均真实模型验收。本次新 C0 声明安全/兼容回归已通过，A1 本地部分完成。2026-10-02 用户确认所有第二人验收暂缓；其要求保留为未验、不阻塞本次本地收口，也不能由本代理或 mock 代替通过。没有提交、推送、发布、PR 或标签授权延伸。
