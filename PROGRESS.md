# CUAgent 实际进度

更新：2026-09-23。主路线：[DeepSeek Harness → Computer Use → O0](Harness_Development_Plan.md)。设计、实际实现、本轮测试和历史结果分别记录。

## 当前交付

| 项目 | 状态与证据范围 |
|---|---|
| 新仓库 | 公开 `9leaa/CUAgent`；首次发布使用 `harness-migration` 分支，不创建PR；以Git远端实际状态为准 |
| 旧仓库 | `9leaa/os_agent` 已归档，描述/主页指向新仓库；后续按用户要求将旧本地源码和Pi移至废纸篓，VM/镜像保留 |
| 设计与计划 | README、DESIGN、Harness_Development_Plan、AGENTS、COLLABORATION、MIGRATION已按Harness改写 |
| 核心工具迁移 | 20个文件逐字节迁入；manifest记录来源类别和SHA-256，其中15个来自旧未跟踪文件 |
| 本轮工具测试 | Node 24.9.0：31/31通过；属于无模型单元测试 |
| 本轮VM工具测试 | Python 3.9.6：7/7通过；属于mock，不操作桌面 |
| Harness版本 | 固定源码00102833dfaee1da9f48a3a8eae9d34005a75218 / 0.1.7-alpha.2；本地安装、完整构建及CLI版本/help检查通过；本地源码已打插件元数据补丁 |
| Harness A0 | 未验收：profile、Cordis插件、Web、模型、会话和图片链路待接入 |
| A1、C0–C3 | 待实施；无Harness桌面任务通过记录 |
| O0 | 后置，未开始 |

## 2026-09-23：仓库与方案迁移

本轮工作：

- 创建新本地仓库与公开远端，配置origin。只建阶段分支，提交和推送仍由用户负责。
- 将旧公开仓库归档为只读并设置迁移指向；未删除仓库、旧工作树、VM、镜像或开发凭证。
- 读取最新Pi计划及实现，同时审阅更早整体设计、联合开发计划、MVP计划和交接要求；逐项映射见MIGRATION。
- 复用框架无关工具核心、测试和验证器；旧Pi安装/启动/注册层不作为新运行时迁入。
- 以固定Harness源码核对profile/preset、工具schema、执行guard、取消、Web展示、额外会话上报、文件沙箱和Computer Use provider差异。
- 保留Cua补丁和MIT许可证；迁入历史Pi验收摘要但明确不构成Harness通过。

实际验证：

```bash
node --test agent/tests/*.test.mjs
python3 -m unittest discover -s tools/mac_vm/tests -v
```

结果：31项Node单元、7项Python mock均通过。迁移的20对文件SHA-256与原工作树一致，清单见 [migration-assets.json](migration-assets.json)。本轮没有重新构建Swift/Lume、启动VM、安装Harness、读取密钥或发送模型请求。

九份旧设计/进度/规则文档另保存来源哈希；本轮文档检查覆盖13份Markdown相对文件链接及5份JSON解析，无缺失链接或解析错误。尚未发布到GitHub。

## 2026-09-23：本地安装 Harness

- 路径：`.runtime/harness`；固定源码浅克隆，Node 24.9.0/macOS arm64，项目本地pnpm 11.7.0。未全局安装。
- `pnpm install --frozen-lockfile --store-dir ../pnpm-store`通过；随后`pnpm run build`退出0，包含原生模块、Host/Client与Web，生成263个client artifacts。
- 以独立`DSH_HOME=.runtime/harness-home`（执行时使用绝对路径）运行根目录`pnpm dsh --version`与`--help`，均退出0，版本输出`0.1.7-alpha.2`。
- 构建后离线frozen install复核通过；上游源码无修改，锁文件摘要与具体命令见[接入说明](agent/harness/README.md)。初次安装的三个子包bin链接缺失仍记录为限制；使用根目录CLI不受影响。构建有弃用项/体积警告，无构建错误。
- `.runtime/harness-installation.json`记录本地安装，build/install日志保存在同目录，全部被Git忽略；本次未提交、推送或创建PR。
- 没有读取/配置API Key、启动Web服务、调用模型或操作桌面。A0-01仅环境安装/构建部分完成，模型/策略固定以及整个A0仍未验收。

## 历史资产，不计入 Harness 验收

| 来源 | 已有结果 | 尚未完成或限制 |
|---|---|---|
| Pi 0.86.1 / deepseek-flash | 历史三轮对话；CSV统计/写入/读回及独立核对；固定图直接输入与工具图片返回 | 新Harness需重验；默认模型固定/重启、三份文本与真实越界拒绝当时尚未齐备 |
| workspace_list | 核心与边界测试；用户报告真实调用成功 | 当时没有单独保存真实调用证据 |
| 受控文件核心 | 路径、类型、大小、默认不覆盖等测试 | 进程内策略，不是OS沙箱；并发/取消/宿主权限不能由这些测试推断 |
| M0 | 历史VM隔离、普通用户、Driver截图/应用信息及停机基线恢复通过 | 本轮未检查当前VM运行状态 |
| M1 | 固定12×34；17次Driver请求；新AX显示408；独立smoke通过 | 无完整result.txt闭环；其余八例和模型桌面执行未通过 |
| Lume补丁 | 历史五文件隔离补丁、两项Swift测试和零共享检查 | 本轮只保留文件，没有重新构建或重跑真实隔离 |
| 旧M2–M4 | 旧SDK路线停止 | 不恢复旧模型入口，不将未通过阶段改写成功 |

历史模型摘要：[Pi CSV与图片链路](docs/history/pi-a0-csv-image-2026-09-22.md)。其正文保持当时原字节，引用的是旧环境命令和能力，不是本项目启动方式。

## 2026-09-23：卸载 Pi 与清理旧代码

- 用户明确要求卸载Pi、删除旧文件和代码。确认没有全局Pi npm包或PATH入口，Pi实际安装在旧osagent/.runtime/pi。
- 清理前再次核对新旧20个资产和9份来源文档SHA-256一致，没有读取认证内容。
- 将旧osagent项目（含Pi运行时与项目配置）、用户`.pi`、旧Cua源码、旧交接Git目录和9份旧文档移入私有废纸篓目录；映射见MIGRATION §7。
- 保留旧osagentmvp内`.vm`、`.vm-tools`、`downloads`、`evidence`；未停止或修改Lume/VM进程，未卸载Node、npm或Cua运行工具。
- 清理只涉及旧资产及文档状态更新，没有改动新核心代码；不重复调用模型、启动VM或重新安装框架。没有commit、push或PR。

## 2026-09-23：修复原生模块架构错误

- 用户Web运行报`system.node`为x86_64、Node需要arm64。实查Rosetta状态为1，`cc -dumpmachine`为x86_64；此前构建退出0与CLI检查未覆盖原生加载，不能作为该模块可用证据。
- 在原生ARM64 shell中重新执行官方`build:native-system`，没有改上游源码、模型配置、密钥或会话，也未重启用户Web进程。
- 验证：`file`为arm64；ARM64 Node实际加载与导出检查通过；上游文件锁测试按名称筛选4项，4/4通过（加锁、竞争、释放、非法fd）；上游工作树干净。
- 模块SHA-256：`a0d2d9eddd629515646c5fe3e13c83d07713c97ab880fd11e2b5e65db6251623`。重编译与防复发命令见[接入说明](agent/harness/README.md)。用户重启后的Web/模型结果待验证，不将此修复计为A0通过。

## 2026-09-23：修复插件元数据异常

- 固定Harness的profile resolver在改写Node解析异常时直接赋值只读`error.stack`，把可预期的`ERR_PACKAGE_PATH_NOT_EXPORTED`变成`TypeError`，导致Web插件元数据卡片全红。仅修改本地上游源码的两处异常栈处理，并加一项回归测试；可重放补丁见[patches/harness/readonly-error-stack.patch](patches/harness/readonly-error-stack.patch)。
- 在`.runtime/harness`运行`pnpm exec vitest run packages/boot/app-boot/tests/profile-resolution.spec.ts packages/boot/app-boot/tests/package-meta.spec.ts --reporter=dot`：304通过、1跳过；`git diff --check`及补丁反向检查通过。`pnpm run build:lib:host`成功，产物包含修复，`system.node`仍是arm64；未重建原生模块，未触碰密钥或用户运行中的Web进程。
- Web重启后的插件显示尚未复验，不计入A0验收；上游源码当前有本地修改，重装需重新应用补丁。

## 2026-09-23：首次分支发布

- 用户单独授权助手检查、提交并直接推送本仓库到公开`9leaa/CUAgent`的`harness-migration`分支，不创建PR；后续仍沿用用户自行提交推送的约定。
- 发布范围仅含设计、迁移工具与测试、历史脱敏摘要和可重放Harness补丁；忽略`.runtime`、开发凭证、会话、VM磁盘和原始桌面证据。具体提交与远端结果以Git记录为准。

## 下一步

固定Harness构建已完成；用户重启dsh后先在Web插件页复验红色元数据错误。下一步A0-02实现项目Web profile/preset，先离线核对实际工具清单、停止/预算与额外上报配置，再让用户配置新运行时开发凭证，固定模型/策略并验证模型与会话。随后移植五个工具注册层并重跑A0全部业务用例。

## 后续更新规则

每轮记录阶段、版本、文件、实际命令、运行环境、成功与失败证据、未测项和下一步。只有独立验收通过才更新阶段状态。不要恢复旧文档中“自动提交PR”“默认codex前缀”或“旧Git历史一定可恢复”的假设。
