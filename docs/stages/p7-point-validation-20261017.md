# P7 联合窗口查询实测（2026-10-17）

结论：专用探针的系统级 AX 与 WindowServer 联合读取已在 VM 运行；本轮遮挡样本均未匹配原表格，但窗口外侧仍出现双查询匹配，因此联合身份不是点击许可。正式 Driver 未修改，P7 输入、保存、重开及独立读回仍未通过。原生保存面板已采样，尚未取得 AXSheet 角色证据，不能将 Sheet 项标为完成。

## 环境和权限

- macOS 15.6.1 / 24G90，VirtualMac2,1，LibreOffice 26.2.6.3，原 Driver PID25760 保持运行。目标 Calc PID468/window123，独立清单 bounds=(96,61,768,541)。这些 PID/窗口只描述本次现场，不可用于后续授权。
- 原生探针来自33c9ae5，arm64/SDK15.5；包目录 CUAgent-PointProbe-33c9ae5-arm64-sdk15，签名后可执行文件 SHA256 `928b6898f69bd2b205281f33d1744cf26b891ab69624b870fec28bb7d12d32d8`，CDHash `1eecf9a22b684e9e5a3a3d3e00a13ba641d76824`。
- 开启已有 CUAgentPointProbe 开关，以及未删除旧行直接重新添加当前包，均仍 trusted=false。删除该权限行，再通过文件选择器添加精确当前 App 后，新的 LaunchServices 进程 PID43444 返回 trusted=true。只证明这次重新登记有效，未读取 TCC 数据库，不能断言历史失败均由签名缓存导致。
- 用户确认本对话内允许该 VM 专用探针权限操作。本轮 UI 实际执行了开启、重新登记和最终关闭；回执 permissionChanges=false 仅表示采集脚本自身不改权限，不能解释成整个操作过程未改权限。未授予 SSH/Python 权限，未改变原 Driver 开关。

## 采样结果

除最后三行外，点均为桌面(360,176.5)，匹配目标均为原 Calc 468/123。每行是独立的一次只读样本，没有循环重试。AX 命中错误直接保留，不用 SPI 成功掩盖。

| 场景 | 系统 AX PID / 状态 | WindowServer PID / window | 联合身份匹配 | 私有回执目录前缀 |
| --- | --- | --- | --- | --- |
| 无遮挡公式栏 | 468 / 0；AXWindow、AXParent 均 NoValue | 468 / 123 | 是，仅诊断 | calc-unobscured-e467714f |
| 系统设置遮挡 | 4486 / 0 | 4486 / 358 | 否 | other-app-overlay-3f0d82c1 |
| Calc 菜单 | 468 / 0 | 468 / 999 | 否 | calc-menu-fcd37040 |
| Format Cells 普通对话框 | 无 PID / -25208 | 468 / 1000 | 否 | calc-dialog-1f5340b1 |
| 同文档第二视图 | 468 / 0 | 468 / 1034 | 否 | calc-second-view-5e6034e1 |
| 原生 Save 面板 | 468 / 0 | 468 / 1050 | 否 | calc-save-panel-76cd85f0 |
| Spotlight 系统弹窗 | 546 / 0 | 546 / 1058 | 否 | spotlight-c3f2e58a |
| 空白桌面(10,400) | 476 / 0 | 476 / 22 | 否 | desktop-3e9ff83f |
| 左界外侧(95,300) | 468 / 0；AXWindow Unsupported | 468 / 123 | 是，反例 | edge-outside-245002df |
| 左界内侧(97,300) | 468 / 0 | 468 / 123 | 是，不证明内容区 | edge-inside-abb93e68 |

十份回执均由独立 libproc 路径、ps 用户/启动时间/本次标记核对真实进程，观察到其退出；open 返回0且stderr空，助手自身退出码仍为null，不用open退出码替代。CGWindowList使用选项1，显式包含桌面；查询前后清单均存在实际命中PID/window且几何一致，时间覆盖原生查询。该检查不能排除两次采样之间的瞬时竞争。

专业解释：AX PID 与 SPI PID/window 的一致性只补充窗口归属，不能证明坐标处于可操作内容区。直白解释：窗口外一像素也可能被系统算进窗口，不能因为“认对窗口”就点击。必须保留内容内部范围/边缘排除、严格父链的冲突拒绝、激活后新观察与投递前复核；矩形只能额外拒绝，不能单独放行。

## 清理、证据和验证界限

- 第二视图已关闭，Format Cells 和 Save 面板取消，Spotlight关闭；未保存文档。布置保存面板时组合键被屏幕共享误送成字符s，立即Escape取消；新截图确认A2恢复原probe。后续改用菜单。该人工诊断不算模型业务动作。
- CUAgentPointProbe最终开关关闭；新回执 permission-revoked-64c51d85 中 PID43666 独立身份/退出核对通过，trusted=false、AX_NOT_TRUSTED_NO_PROMPT。原CuaDriver-0.34开关仍开启，原Driver25760仍存在；设置窗口关闭，Calc恢复可见。
- 原回执、采集脚本、完整桌面和audit.json留在忽略目录 `.runtime/p7-point-validation-20261017/`。截图API返回JPEG，最初保存为.png的原字节保留，另存同字节.jpg并记录摘要；不把扩展名当PNG格式，也未用这些图片生成正式业务截图准入。
- 本轮本地命令：指定backend虚拟环境运行 `python -m unittest tools.mac_vm.tests.test_native_point_probe backend.test_windowserver_probe backend.test_diagnostic_admission backend.test_diagnostic_desktop_review`，32项通过（19.911秒）。这些测试不替代实机或业务验收。私有离线审查11份回执（10场景+撤权）身份、退出、时间及前后窗口清单一致。
- 无新增正式模型运行，未重放018。DSH RPC预检为DESKTOP_RPC_UNCONFIRMED，不能据此声称App空闲或模型可用。

## 下一步准入条件

先扩充只读诊断的有界角色/窗口链分类，确认原生Save面板是否为AXSheet；仅输出固定角色类别、属性错误码及窗口编号，不读正文。补充窗口边缘拒绝和AX异常不回退的反例后，才能完成生产接线设计。随后独立构建/部署、实时身份/权限/截图准入，再运行新的DSH Flash/off任务，保持30raw/180秒及UNKNOWN不重放。当前没有生产点击修复，也没有完整P7验收结果。
