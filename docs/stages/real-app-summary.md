# 单人真实 TextEdit 任务总结

2026-10-02：独立核对通过一个 VM 系统 TextEdit 任务。模型整理测试交接信息，真实界面输入、Command-S 保存，再写入并读回 result.txt。专业上是实际应用纵向闭环；直白说，是在真正的软件里把一件小事做完，不是证明任意软件都能操作。C3/第二人仍未验，没有提交、推送或发布。

## 实际结果与限制

最终 run `real_textedit_20261002_006`，官方 session `session-adf94ddc-9ba4-4215-bccc-b9e814a478b9`；Desktop 0.2.0-rc.2、Node 24.18.1、模型 `deepseek-account/deepseek-flash`。五个模型工具仅观察、输入、固定保存、写/读 result；没有通用 Shell、任意键盘或宿主 GUI。

- 12 次模型工具调用、1 次错误；GUI 输入一次、Save 两次，每次 Save 都有不同的新鲜观察。陈旧 result 写请求被拒，重新观察后完成；未删除错误或重置预算。
- 实际文档 87 字节，与派发前独立期望逐字节一致，SHA-256 `0a42c371a21cf4fc42ec146e764346b1d61284b1c371811ce84d7f939c229987`。result.txt 为完整正文加结果写入器的一个 LF，实际模型读回一致。AX 展示仅允许缺一个末尾 LF，其他字节仍严格比较。
- 业务阶段 14 raw；结束后在线 verify 请求新增一次失败观察，合计 **15/30**。Driver session 已结束，该请求 HTTP 409，没有 guest verification.json。最终只读独立验收使用本轮保存后的原始新 AX/PNG、当前完整文件、原期望、输入/保存/读回轨迹；**不声称结束后重新截图成功**。
- 10 项实际 HTTP 认证/角色/不开放 Shell/停止后请求拒绝通过；预算仍 15，停止后派发 0。独立收集核对连续唯一派发及结果、原图哈希（6 张）、冻结执行源码和官方请求，报告 PASS、任务 SUCCEEDED。只读验证器后来调整，执行与验证版本单独记录，不声称最新整个树已重跑。

## 所有尝试均保留

| run 尾号 | raw | 结果与原因 |
|---|---:|---|
| 001 | 7 | UNVERIFIED；锁屏下后台截图有图，但 AX 无目标 |
| 002 | 2 | UNVERIFIED；恢复旧窗口导致同名目标不唯一 |
| 003 | 5 | UNVERIFIED；唯一窗口仍无法激活，确认图形会话锁屏 |
| 004 | 7 | UNVERIFIED；press_key modifier 实际追加 s，保存字节错误 |
| 005 | 14 | UNVERIFIED；文档正确，但 AX 末尾 LF 投影差异阻断结果链 |
| 006 | 15 | 原始保存后观察与完整文件/结果/读回独立通过；结束后在线重观察失败另列 |

这些是开发诊断，不是预先冻结的六例评测或成功率。修正过程见 [实施方案](real-app-design.md)：唯一 run 文件名、锁屏前置检查、固定 hotkey 后端、严格 AX 投影比较。未改变期望答案或放宽其他文件/窗口权限。

## 收口与复现边界

所有独立 executor 和本次 TextEdit 实例已退出，测试 VM/Driver 保留运行。官方 App 已恢复 A1，旧文本/CSV/只读预算仍 **10/30、30/30、1/30**。最新无模型回归：核心 59/59、官方同版注册集成 26/26、Python 123/123；不能替代真实 VM 证据。

原始 session、原图、账本、失败报告和完整文件位于忽略的 `.runtime/runs/real_textedit_20261002_00*` 及 guest 对应 C0Evidence 目录，不提交账号凭证或私有数据。最终目录含 `verification-attempt.json`、`independent-acceptance.json`、`boundary-verification.json`、独立收集目录、冻结及恢复记录。执行源码在独立 guest 目录，原 C0/C1/C2 源和账本未覆盖。

本次只完成一个有预先授权空文档的纯文本任务；安装软件、创建任意文档、跨应用长任务、广泛泛化、C3/第二人及 O0 均未通过本次验证。
