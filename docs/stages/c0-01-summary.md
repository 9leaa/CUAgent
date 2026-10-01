# C0-01 总结

日期：2026-10-01。分支：`c0-01-computer-use`。状态：**SUCCEEDED（本机单例）**。先写方案，再实施；未提交、推送或发布。

## 做了什么

完成真实 Harness 模型在测试 VM Calculator 中计算 `12×34`，写入并读回 `result.txt`。独立验证核对实际按钮轨迹、验证时新显示、文件与预存期望值，均为 408。C0-02、C1、C2 尚未完成。

## 怎么做

- 固定官方 Desktop App 0.2.0-rc.2、官方 Agent 循环、`deepseek-account/deepseek-flash`、Cua Driver 0.28.2、guest Python 3.12.14（20260929 arm64 Darwin）。不增加自制模型循环，不改官方 App。
- 使用既有 restored 开发 VM，普通 `mvpagent`、SIP enabled、无 virtiofs 挂载、无宿主目录/剪贴板桥；SSH 仅允许 mvpagent，远程完整磁盘访问关闭。保留用户接受的原 VNC 监听方式，不声称公网可达或仅本机。
- guest bridge 只允许指定 Calculator bundle/PID/窗口，按钮需要新鲜且未消费的 AX 快照；写文件只能匹配实际新显示。持久 raw 预算 30 次、调用审计、在途记录与最终停止准入；模型与独立验证 token 分离。超时不自动重试，不让模型修改轨迹/报告。
- 官方 App 使用专用 `c0-calculator` preset，根执行 guard 限四工具与首个会话；实际请求审计限制工具，截图通过官方附件服务作为 image block 送给模型，取消信号传 guest stop。原 A0 账号/会话/账本保留，配置有私有备份。
- 桌面自动化接口超时后，使用官方 Host 的认证 RPC 创建会话与派发一次 prompt；仍由官方 App 的真实模型和 Agent 循环执行，不以固定脚本代替模型点击。

## 怎么验证

1. `python3 -m unittest discover -s tools/mac_vm/tests -q`：23/23 mock 通过，guest Python 下同样通过。官方 Electron Node 执行 `c0-vm-tools.test.ts`：实际 defineTool 接口、会话限制、图片附件、取消和无自动重试通过。它们不是模型成绩。
2. 真实 HTTP run `c0_gate_20261001_003`：错误 token、模型验证入口、shell 拒绝；新观察成功；stop 成功；停止后无新观察派发。此前 001/002 的观察失败保留：guest 自动锁屏导致 AXWindow 为空，解锁后通过，没有放松检查。测试期间临时 caffeinate 有时限，不改永久设置。
3. 正式 run `c0_model_20261001_001`，会话 `session-9c5a4e06-e422-450e-8fa0-2ebc2628c5bf`。模型执行 17 个工具调用；19 个模型请求记录中 17 个含 image block，所有工具名仅 `vm_observe/vm_click/vm_write_result/vm_read_result`。记录窗口 02:51:44–02:52:25 UTC，约 41 秒（不是端到端完整耗时）。
4. 独立 guest 验证器返回 SUCCEEDED：完成动作 `All Clear → 1 → 2 → Multiply → 3 → 4 → Equals`；验证时新显示 408，文件及此前工具读回 408；所有派发有成功结果，没有 UNKNOWN。含内部观察/启动/验证共 **20/30 raw 请求**。

原始轨迹、截图、结果及验证报告在 guest `/Users/mvpagent/C0Evidence/c0_model_20261001_001/`；模型会话、请求审计及开发侧验证汇总在 Git 忽略的 `.runtime/runs/c0_model_20261001_001/`。开发 RPC 登录信息与 bridge token 不进入模型输出、公开文档或 Git。

## 限制及下一步

这是既有开发 VM 的单例，不是干净无凭证发布基线，不是恶意同用户进程隔离或完整网络沙箱证明；全套故障、接管和 18 次可靠性门槛属于 C2，第二人干净复现属于 C3。接下来 C0-02：九个计算器任务及表单、滚动定位、测试文档保存，各自独立目录、真实模型执行与独立验证。
