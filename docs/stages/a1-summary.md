# A1 本地完成总结（第二人验收暂缓）

2026-10-02，分支 `a1-agent-expansion`。按用户最新范围完成 A1 本地实现和验收；C3 继续跳过，所有第二人验收暂缓、未验，不登记为通过。没有提交、推送、PR、标签或发布。

## 做了什么、为什么

专业解释：框架无关核心、同版 Cordis 适配、执行端持久准入与保护的独立验证器组成通用扩展路径。直白说：模型确实读取文件和表格、生成报告并读回；重启、切换和增加工具不能偷开权限或获得新次数。

- 默认 A1 六工具、只读 preset 四工具；CSV 不经 shell。通用 fingerprint 示例是单独审查的 opt-in 候选，编译不等于挂载或审批，默认任务不授权。
- 每 session/run 固定工作区和独立私有账本，30 次写前计数；失败/卸载后的工具请求计数，停止后禁止新派发，配置改写/审计失效/未配对旧派发拒绝。参数保存字节数和 SHA，不保存正文；结果保存耗时、错误码及产物引用。
- 启动和运行时共用审批校验；工作区/账本/配置不能重叠或通过链接别名复用。工具正文还要求活跃准入，卸载 policy 不会让剩余工具偷跑。
- 提供输入/输出 schema、稳定 HarnessError 转换、取消/官方图片转换和不授权的等效流程。继续复用官方主循环、结果显示、附件、会话和压缩，不自建 Agent loop/UI。

## 真实业务和生命周期结果

| 验收 | 实际证据 |
|---|---|
| 三文本 | 新 synthetic 输入，八次真实调用；全部字段、来源 SHA、JSON/Markdown 字节与完整读回独立一致 |
| sales.csv | 五次真实调用；行列/count/missing/sum/min/max/mean、全表格、来源 SHA、产物和读回独立一致 |
| 多会话与审计 | 两业务官方会话并行但授权根/账本独立；真实 call/result 与 run/session/call 对应，原证据字节前缀再次匹配 |
| 重启与压缩 | 原身份/预算保持；官方手动 compact 16 项约 3083 tokens，不派发业务工具，压缩后原 session 读回通过 |
| preset | 新任务首轮前 controlled→readonly，真实模型只有四工具；standard 禁用，首轮后切换 locked，不绕过锁 |
| 图片 | 工具返回 PNG 与直接输入 PNG，独立像素/答案/颜色产物/完整读回/SHA 全部核对 |
| 取消与预算 | 官方 cancel 在第 12 次派发后形成 aborted/user；请求及确认取消后无新派发。明确新轮次用至 30，第 31 次及重启后请求均拒绝，未清零 |

原 A1 三任务当前预算为文本 10/30、CSV 30/30、只读 1/30，均 terminal；CSV 不能继续派发。业务/生命周期原报告和失败留在私有 `.runtime/runs/a1_business_20261002_001` 与 `a1_preset_20261002_001`，不上传原会话、PNG、账号或密钥。

## 新真实 VM 安全/兼容回归

用户确认继续后，以项目补丁 Lume 0.5.3、隔离开关、无显示/剪贴板、NAT 启动原 `mac-agent-mvp-15-6-1-restored`，保留 VNC 57593。测试账户 mvpagent 登录，SIP enabled、无 virtiofs，Driver daemon 自身 Accessibility/Screen Recording 均 true；没有改 TCC/SIP/SSH或端口。十个 guest 源、C0 adapter 和 fixture 字节与原 C2 基线相同。

- `a1_c0_mul12_34_20261002_001`：官方模型真实 Calculator 独立 SUCCEEDED，17 个模型工具调用、20/30 raw；All Clear→1→2→Multiply→3→4→Equals，新的显示/result.txt/读回/预存期望均 408。八项实际 HTTP 认证、模型不能独立验证、验证器不能操作、shell 与停止后请求拒绝；原预算仍 20，停止后零派发。
- `c2_budget_a1_20261002_001`：真实 30 raw、28 个新快照/PNG；第二个独立进程 1188→1482 重启仍 30，七项继续/恢复/交还拒绝，停止后零派发。
- `c2_inflight_a1_20261002_001`：真实 Driver 输入返回后暂存，stop 约 0.000308 秒记录在途；新派发/提前接管拒绝，原返回只记一次，接管后的新观察确认 cedra-42→cedar-42，共 6 raw。
- 后两项是无模型执行层安全诊断，业务保持 UNVERIFIED，不冒充官方取消/网络超时或业务成功。宿主读回原 trace/报告/PNG 哈希及官方会话，独立 `a1_vm_audit_20261002_001/verification.json` PASS；原 VM 证据未改。

对应 executor 和两诊断 fixture 均已退出；VM/Driver 保持运行。App 正常恢复 A1，原预算 10/30、30/30、1/30 不变。此次回归覆盖未改 C0/C2 层的兼容与声明安全边界，不重报完整 C2 18 次评测或整机安全认证。

## 测试、原失败与限制

最终核心 59/59、官方 App 同版注册集成 25/25、Python 103/103、git diff --check 通过；无模型测试不能替代上表真实证据。注册集成覆盖卸载/重载、配置覆盖、非法审批、并发预算、孤立工具，以及 21 类文件边界拒绝（两正常加 21 失败，23 次派发/结果，原文件不变）。

原文本 verifier 末尾空行、compaction isolate 缺失、preset 初始事件投影和普通 Error.code 丢失均记录并修正，原产物/尝试保留；没有删失败、重置预算或修改 oracle 迎合错误业务输出。详细过程见 [业务记录](a1-business-progress.md)、[逐项核对](a1-acceptance-audit.md)和 PROGRESS。

固定 App 0.2.0-rc.2 / Node 24.18.1 / 同版参考 639ed015，实际模型 deepseek-account/deepseek-flash / high，Driver 0.28.2、guest Python 3.12.14。未评估恶意同用户进程/任意插件、网络抓包、跨机器或第二人复现；原 VNC 监听按用户选择保留，不能据此声明公网可达或不可达。费用未核算，未猜费用。

本地验收已完成；第二人新增工具/独立复现仍为暂缓未验，C3 未完成。后续新增任务须新 run/明确审批，不复用耗尽任务；提交、推送和发布由用户另行决定。
