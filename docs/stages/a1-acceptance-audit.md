# A1 逐项验收核对（本地完成，第二人暂缓）

2026-10-02，`a1-agent-expansion`，依据主计划第 8 节和实施前方案。C3 跳过但不标完成；2026-10-02 用户进一步确认所有第二人验收暂缓，先收口 A1 本地部分，第二人项保留未验且不阻塞本次本地收口。没有提交、推送或发布。此文件是证据清单；本地完成总结见 [a1-summary.md](a1-summary.md)，不代表第二人通过或 C3 完成。

| 原要求 | 当前权威证据与范围 | 判定 |
|---|---|---|
| 新三文本、字段、Markdown、读回、来源及哈希 | `a1_business_20261002_001_texts` 官方 turn 1 八次真实调用，保护的独立字段 oracle；原 session/audit 字节前缀再次匹配原报告 SHA | 通过 |
| sales.csv 完整统计、JSON/Markdown、读回、无 shell | 同批次 csv turn 1 五次真实调用；完整 count/missing/sum/min/max/mean、全部表格单元及来源 SHA 独立核对 | 通过 |
| 插件示例、schema、错误码、取消、图片转换 | fingerprint 核心/适配、交接文档；实际注册表正常/非法/取消/未授权/卸载拒绝；原真实模型两种 PNG 有像素/产物/读回独立报告 | 已提供并测试，不算第二人验收 |
| Skill 或等效流程，不授予权限 | `a1-controlled-workflow.md`；输入/输出/读回/独立判定约定，权限来自执行策略，不来自文档 | 已提供 |
| 复用官方结果与会话，不重写循环/UI | 同版 defineTool/render/附件服务、官方模型 call/result 与持久 session；未增加自定义卡片 | 通过当前实现范围 |
| run/session/call、脱敏、耗时、产物、验证关联 | 原任务独立报告关联真实会话、派发/结果及产物 SHA；审计只保存参数摘要，不保存正文；策略测试核对关联/篡改/UNKNOWN | 通过当前声明范围 |
| 插件卸载/重载、配置覆盖 | 实际同版 Cordis/ToolRuntime 集成，旧预算持续、孤立工具正文拒绝；配置改写、非法审批及示例卸载拒绝 | 通过注册集成范围，无模型热切换声明 |
| preset 切换 | 新只读任务官方首轮前 controlled→readonly，一次真实读；standard not-found、首轮后 locked；未绕过锁 | 通过官方允许范围 |
| 重启、压缩、多会话隔离 | 原 session/run 续接，官方手动 compact 16 项约 3083 tokens；两业务并发授权根/账本独立；非法会话/路径注册拒绝 | 通过；不声称副作用可自动重放 |
| A0 最低安全回归 | 真模型图片/取消/30 次与跨重启拒绝；实际 A1 注册 21 类路径/类型/大小/链接/覆盖/证据逃逸拒绝，23 次派发均有结果，失败计数 | 通过已声明 A0 范围 |
| C0 安全回归 | 新官方模型 12×34 独立 SUCCEEDED，20 raw/17 模型调用；8 实际 HTTP 拒绝；新 VM 30 次跨进程/7 拒绝及 6 次在途停止诊断；宿主原证据读回审计 PASS；同版源码/adapter/fixture 未变 | 通过 A1 兼容与声明安全回归范围，不重报完整 C2 |
| 第二位开发者独立新增受控通用工具、不改主循环 | 交接说明保留，无实际第二人证据；用户明确暂缓 | 暂缓、未验；不阻塞本次本地收口 |
| README/PROGRESS、版本、失败、限制与总结 | 已同步当前证据/原失败及本地总结；App 0.2.0-rc.2 / Node 24.18.1 / 参考 639ed015；第二人未验单独记录 | 本地收口完成 |

## 本轮复核命令

```bash
node --test agent/tests/*.test.mjs
node agent/harness/test-desktop-adapters.mjs a1-policy.integration.test.ts a1-csv-tools.integration.test.ts a0-policy.test.ts a0-policy.integration.test.ts a0-file-tools.integration.test.ts c0-vm-tools.test.ts
python3 -m unittest discover -s tools/mac_vm/tests -q
git diff --check
```

实际结果为核心 59/59、注册集成 25/25、Python 103/103、diff 检查通过；全部属于无模型测试，不能替代真实 VM。业务私有证据见 `a1-business-progress.md` 的 run/report 引用；不上传原始会话、截图、账号或密钥。

App 当前 A1，三个官方会话 terminal，原预算 10/30、30/30、1/30。CSV 已耗尽，不为复核再派发。用户确认继续后已启动原测试 VM、完成新真实回归并恢复 App 为 A1；VM/Driver 保持运行，任务 executor/诊断 fixture 已退出，未改端口或权限。私有 `a1_vm_audit_20261002_001/verification.json` PASS；原始证据及第二人未验项保留。本地 A1 完成，不代表第二人验收通过。
