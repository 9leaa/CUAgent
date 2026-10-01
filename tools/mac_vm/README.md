# macOS VM 桥接与历史诊断

本分支完成 c0-01、c0-02、c1。执行器只允许固定任务、明确授权、新观察、30 次真实调用与独立验证；模型没有任意 shell、路径或 verifier 权限。原生 fixture 提供固定测试界面，不替代模型决策。

方案与结果见 [阶段总结](../../docs/stages/c1-summary.md)。后续阶段不计入本分支。

三个Python文件从旧项目原字节迁入，源头是 `cua/samples/mac_agent_mvp/`。它们是环境诊断和固定运算对照，不是Harness Agent。来源哈希见根 [迁移清单](../../migration-assets.json)。

- `preflight.py`：开发侧只读环境清单，不启动VM，不调用桌面工具，不输出VNC密码。
- `driver_smoke.py`：在指定测试VM内固定执行12×34，检查计算器PID/窗口、新AX显示和执行证据。
- `tests/test_driver_smoke.py`：7项mock边界测试；`--live`另在测试VM执行固定流程与独立smoke断言。

根目录无模型测试：

```bash
python3 -m unittest discover -s tools/mac_vm/tests -v
```

历史live入口需要VM内Python 3.12.14或验证过的兼容版本、Driver 0.28.2、普通mvpagent账户与已授权图形会话。将本目录部署至VM后在该目录执行：

```bash
open -n -g -a CuaDriver --args serve
python3 tests/test_driver_smoke.py --live
```

以上命令只供测试VM的C0复核，不能在宿主删除VirtualMac/账户检查来运行。实际请求最多30次；动作超时不盲重放；每次在VM任务目录新建证据。当前固定smoke不生成完整MVP的result.txt。

开发側只读inventory：

```bash
python3 tools/mac_vm/preflight.py --storage /absolute/path/to/vm-storage --vm mac-agent-mvp-15-6-1-restored
```

退出0仅代表读取完成，NOT_ASSESSED不等于隔离或任务通过。

## 恢复与来源

[vm-manifest.json](../../vm-manifest.json)记录历史环境；[Lume补丁](../../patches/cua/README.md)记录固定源码与隔离改动。configured是历史停机基线，restored是曾配置开发凭证的副本，不能直接分享。

使用经过核验的隔离Lume二进制，从停机无凭证基线clone到新名字，明确source/dest storage；先核对固定版本help与当前资源。启动历史参数为 `LUME_MVP_HOST_ISOLATION=1`、`LUME_TELEMETRY_ENABLED=false`、`--display none --network nat`。不得覆盖现有VM或启用宿主目录/剪贴板共享。

普通账户图形登录后启动Driver daemon，再验证权限、新截图、应用信息与隔离。恢复基线不会自动安装Harness或配置模型。

历史M1为17次调用、AX408、独立smoke通过；本轮只重跑7项mock，没有新的VM验收。九组计算器、结果文件及异常要求见 [新计划C0](../../Harness_Development_Plan.md)。UFO固定参考与旧阶段迁移见 [MIGRATION](../../MIGRATION.md)，不依赖可能已不可达的旧Git历史才能理解规范。
