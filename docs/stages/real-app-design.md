# 单人真实应用任务方案

2026-10-02，用户授权继续单人新任务验证；C3/第二人仍暂缓，不提交或推送。沿用 A1 脏工作树，新增文件独立，不清理或重置历史。

## 目标和选择

VM 只读 inventory 确认有系统 TextEdit，未发现 Numbers/LibreOffice；不安装软件或接个人账号。本次选择真实 TextEdit，而非再次扩展自制 fixture：将 prompt 中三条 synthetic 交接信息整理为指定纯文本文档，通过真实界面输入和 Command-S 保存，再读回。

专业上是新应用纵向闭环/有限迁移测试；直白说，看看原来那套观察、输入、验证能否用在真正的软件上。单例不证明任意软件、开放桌面、完整泛化或 C3。

## 范围与权限

- 官方 Desktop 0.2.0-rc.2 / Node 24.18.1 / 同版工具库，原模型 deepseek-account/deepseek-flash，原测试 VM 和 Driver；无新 Agent loop、MCP、Shell、网络或宿主操作。
- 新 `real_textedit_20261002_001` run；独立 evidence、artifact 与 verifier oracle，30 次实际调用，失败/重试/内部调用计数；停止和重启沿用原预算且拒绝继续。
- 开发 setup 只以 exclusive create 创建一个空 `artifacts/handoff.txt`，原空字节 SHA 记录。允许模型通过 TextEdit 编辑这个明确授权的测试文件，不允许直接写该文档；模型只有固定 result.txt 写入/读回。
- 仅新启动 TextEdit 实例、固定应用可执行文件、PID、唯一 handoff.txt 窗口、新鲜 AXTextArea。正文内容不硬编码白名单；限 UTF-8 4 KiB、无 NUL，只有该正文控件可输入。键盘只允许新观察后的 Command-S，不能另存、打开其他文件、执行代码或离开任务窗口。
- 新应用 bridge 独立于 C0/C1/C2 registry；同桌面锁、原预算/停止/原始审计复用。save 命令返回不算保存成功，必须后续新 UI 和实际 UTF-8 文件一致。
- verifier 预先独立保存期望，不在模型 workspace；最终核对真实输入/保存轨迹、后续新 AX 正文、文档原字节、result.txt/模型读回、连续完整 dispatch/result、PNG 哈希、实际官方 session/模型/toolNames。缺任一证据 UNVERIFIED。

## 实施与收口

先边界/反例测试，再部署新独立 guest 源目录及 SHA 核对，确认 App 全局 idle 后正常退出并临时配置。只派发一次新任务，保留失败；完成后停止该 executor，恢复 A1 配置并检查旧预算不变，保留 VM/Driver。README/PROGRESS 同步结果和未测项，不将此次算为原固定评测或第二人验收。

## 首次失败后的最小兼容诊断

`real_textedit_20261002_001` 官方轮次 completed，但全部工具失败、没有正文或保存，最终 UNVERIFIED；原 7 raw/trace/PNG/空文件保留并停止，不能冒充取消成功或业务成功。实际 Driver 两权限 true；新 TextEdit 背景窗口截图正确，但 AXWindow 数为 0、`ax_window_unresolved`。没有证据认定是权限或锁屏损坏。

候选修正只在这个新应用 opt-in bridge 生效：首次观察返回同 PID/窗口、正确标题/有效截图、明确 ax_window_unresolved 时，允许一次绑定该窗口的 `bring_to_front`，再重新观察，全部 raw 计预算并审计。它不是编辑或扩大目标范围；失败后停止，不反复激活、不降级为空 AX 或猜坐标输入。新 `...002` run 验证候选，首次失败不替换或删掉。此方案在候选实现和新真实调用前记录。

第二次实际 launch 后 TextEdit 自动恢复旧文件，出现两个不同窗口同名 handoff.txt；唯一目标检查拒绝，2 raw、无输入/激活/保存，UNVERIFIED 原样保留。下一候选 `...003` 将测试文件名包含 run ID，让旧恢复窗口与新任务窗口可明确区分，不关闭或编辑恢复的旧文件、不放宽唯一窗口要求。只试一次，仍失败则保留阻塞结果并恢复 A1，不无限换 run。

第三次唯一窗口成立，但实际 bring_to_front 返回 partial/activated:false，二次 AX 仍空，5 raw 后主动停止、无正文或保存。追加只读系统检查确认 `CGSSessionScreenIsLocked=Yes`，实际 foreground PID 162 是 loginwindow；独立 VNC 黑屏唤醒后确为 MVP Agent 密码锁屏。这说明“console owner=mvpagent/权限=true/后台窗口截图”不足以证明图形会话可操作，并不是新应用执行通过。

本次针对已确认的环境前置失败调整上段停止点：使用既有专用 VM 测试账户，独立 VNC 只做一次解锁；不改自动锁屏/权限设置。新增启动及派发前 IOConsoleUsers 锁屏检查（锁屏即拒绝且无派发），另建 `...004` 验证有效图形会话，不清零前三次预算或隐藏原失败。模型不能解锁/激活任意窗口。若有效会话下仍失败则收口为未通过，恢复 A1。

第四次有效会话下实际 GUI 输入 87 字节，与预存 oracle SHA 一致；新 AX 正文也匹配。但 `press_key` 传 cmd modifier 的实际效果是追加字母 s，真实文件成为 88 字节（原稿+s），不能当作保存成功。后续截图 frame 无效，桥接停止，模型 completed 仍为业务 UNVERIFIED。Driver 同版 describe 区分 single-key `press_key` 和专用组合键 `hotkey(keys:[cmd,s])`。修正仅换该固定组合键后端，不开放其他 key/快捷键；新 `...005` 做最后一次 GUI/文件核对，第四次损坏的 synthetic 文档保留。另允许只读地对明确 px_frame_mismatch 重观察一次，不能猜比例或取消 frame 检查。所有内部请求仍计原 30 次。

第五次实际 document 已正确保存为原预存的 87 字节，GUI 输入 SHA 也正确；但 Driver AX value/tree 展示 86 字节、不含最后 LF。桥接把展示投影当作原字节，错误拒绝 result.txt，业务仍 UNVERIFIED；保留本轮两次 Save、模型错误、原正确 document 与实际 AX 原值，不倒填成功。最终 `...006` 仅修正比较：允许磁盘完整正文等于 AX 或 AX+一个末尾 LF；磁盘/模型读回/oracle 仍逐字节完整比较，不能忽略其他空白、内容、双换行或尾部垃圾。期望文件原字节不改。若此轮仍未闭环则收口未通过。px_frame_mismatch 的真实字段是 screenshot_error.code，按实际 schema 修正只读重观察分支并加反例测试。

第六次完整文档/result.txt/读回均已生成，实际输入一次、Save 两次，模型一次陈旧观察写请求被拒后重新观察并完成，预算未重置。结束后 guest verify 的重新观察遇到 Driver session 已结束，HTTP 409，第 15 次 raw 错误完整记录；没有生成 guest verification.json，不能称在线重新观察通过。初版 verifier 源码额外要求 Save 恰好一次，但没有实际运行到该判定；原方案没有禁止新观察后的同文档 Save。新增只读纯验证器保留全部尝试，核对每次 Save 的唯一新快照/同 PID 窗口/30 秒内/正确正文，输入仍严格一次，重复陈旧 Save、错误原字节、UNKNOWN、缺结果和重复派发均拒绝。最终使用本轮保存后的原始新 AX/PNG、独立读取的完整文件、原期望和读回轨迹判定 SUCCEEDED，不声称获得结束后的新 GUI 观察。执行版本与后续验证器版本分别记录，不声称重跑了整个最新树。结果见 [总结](real-app-summary.md)。
