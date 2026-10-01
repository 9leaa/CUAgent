# C1 总结

日期：2026-10-01；实施分支 `c1-computer-use`。按实施前 [技术方案](c1-design.md) 完成六类、前后各三次，共 36 次真实模型/VM 评测。C1 完成，C2 没有因此完成。

## 做了什么、怎么做

`c1_cases.py` 冻结六例，AppKit fixture 提供真实窗口、字段、效果文件，不承担模型决策。`c1_bridge.py` 复用 C0 准入、预算、审计、停止和 verifier；目标切换后旧快照失效，核对可执行路径、PID、窗口及新观察；跨应用输入取自 Calculator 实际显示，不自算、不共享剪贴板。GUI 返回只算尝试，新观察证明效果才记完成。

官方 Desktop 插件只增加固定标题选择和必要字段输入，继续使用官方 Agent 循环。基线全部结束后新增可选弹窗观察提示：一次计预算的 owned window inventory 提示可见确认窗口，模型仍须选择并重新观察，不自动输入。其余任务、fixture、模型、工具权限和成功判据不变。没有增加第二规划循环或 Agent-S/Jev。

`c1_report.py` 离线核对全部固定轮次、唯一 session、官方会话真实终止/工具数、实际模型请求清单/图片、源码冻结、独立 GUI/文件证明。遗漏、失败和版本漂移不能过滤成通过；默认启用条件按实施前方案计算。

## 怎么验证

同一 App 0.2.0-rc.2 / 内置 Node 24.18.1、`deepseek-account/deepseek-flash`、Driver 0.28.2、guest Python 3.12.14、隔离 restored VM。每次新 run/session，预算 30 包含失败、拒绝、内部请求及独立新观察。phase 内源码未改动；两轮只有 `c1_bridge.py` 的候选增强不同。

| 固定任务 | baseline raw（三次） | after raw（三次） | 独立通过 |
|---|---|---|---|
| 跨应用 | 23 / 23 / 23 | 23 / 23 / 23 | 3/3 → 3/3 |
| 弹窗 | 21 / 18 / 19 | 14 / 17 / 15 | 3/3 → 3/3 |
| 窗口变化 | 14 / 14 / 13 | 15 / 13 / 14 | 3/3 → 3/3 |
| 输入纠错 | 12 / 12 / 12 | 12 / 12 / 12 | 3/3 → 3/3 |
| 长流程 | 16 / 16 / 18 | 18 / 18 / 17 | 3/3 → 3/3 |
| 失败后重观察 | 13 / 13 / 15 | 12 / 14 / 14 | 3/3 → 3/3 |

baseline 18/18，295 raw，累计 639.166 秒；after 18/18，286 raw，累计 585.153 秒。正式评测人工介入均 0；启动前诊断修复与解锁单独记录，不冒充正式轮次的零介入。时间为 host 启动至模型终止/独立验证。正式轮次无失败；此前诊断失败保留，没有补跑替代正式轮次。

弹窗三轮全部低于基线中位数 19，平均 raw 19.333 → 15.333，约减少 20.7%；平均耗时 42.591 → 26.510 秒。各类成功数未退步；其他用例的随机成本变化不归因于弹窗提示。这只是固定测试，不是通用 benchmark。

官方会话记录 baseline 6,277,837 totalTokens、after 5,899,209，包含 cache-read。分别 input 623,876/602,465、output 33,865/25,832、cache-read 5,620,096/5,270,912；只记录实际 usage，未推算货币费用。

命令与结果：

```bash
python3 -m unittest discover -s tools/mac_vm/tests -q
node --test agent/tests/*.test.mjs
node .runtime/build-c0-tests.mjs
ELECTRON_RUN_AS_NODE=1 '/Applications/DeepSeek Harness.app/Contents/MacOS/DeepSeek Harness' --expose-internals --test .runtime/desktop-adapter-tests/c0-vm-tools.test.mjs
python3 tools/mac_vm/c1_report.py --runtime /Users/zhangchengjie/CUAgent/.runtime --output /Users/zhangchengjie/CUAgent/.runtime/runs/c1-independent-comparison.json
git diff --check
```

Python 53/53（mock/注册表/报告）、核心 Node 36/36、官方 App 工具适配 2/2。这些不替代真实 36 次。另逐次读回 guest 36 份 trace/verification/result：预算序号连续且匹配报告、无 UNKNOWN、停止后无新增派发、实际文件与新显示/独立期望一致。抽查弹窗最终原始截图，真实显示 Confirmed cedar-42。

## 证据、失败与限制

私有 host `.runtime/runs/c1-{baseline,after}-report.json`、`c1-independent-comparison.json`、两个 source manifest；run 为 `c1_<phase>_<case>_20261001_<001..003>`。guest `C0Evidence/<run>` 留 trace、截图、AX、真实文件及独立验证；官方会话和 request-audit 留模型证据。baseline executor 副本保留在 `.runtime/c1-baseline-source/`。不公开凭证、原始截图或会话。

诊断阶段 popup 前两次 UNVERIFIED 保留：面板失焦隐藏/锁屏、重复完成记账。修复后才冻结 baseline；不能倒改失败或把诊断当正式评测。

观察提示具备重复成本收益，但默认仍关闭，显式 `CUAGENT_C1_OBSERVATION_HINTS=1` 可用；C2 完整安全/恢复回归未完成，离线报告不会凭成功率批准默认启用。没有开放任意 shell、网络、键盘或模型 verifier 入口。VM 和用户接受的 VNC 端口保持现状；全部 C1 任务已冻结、官方轮次终止、guest bridge 正常结束。未提交、推送或创建 PR，阶段分支和用户未提交改动保留。

> 提交整理说明：本阶段开发时未提交；用户在四阶段验收完成后授权分别提交和推送。前序执行器来自保留的 guest 源码，共享适配器按能力拆分并重新做本地测试；不是原验收时自动保存的完整 Git 快照。实际发布状态以 Git 为准。
