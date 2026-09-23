# Harness 接入边界与下一步

当前目录提供接入设计和 [上游参考版本](upstream-reference.json)，没有已运行的项目profile、插件或启动脚本。核心工具在父目录，其测试不依赖Harness。

## 固定基点

源仓库 `deepseek-ai/deepseek-harness`，commit `00102833dfaee1da9f48a3a8eae9d34005a75218`，源码版本 `0.1.7-alpha.2`。Node要求 `^22.19.0 || >=24.0.0`，包管理器 `pnpm@11.7.0`。本机Node 24.9.0（macOS arm64）已通过完整源码构建及CLI版本/帮助检查；尚未验证Web启动和真实模型。

初始实现选择固定源码及其lockfile，构建输出放忽略目录。源码下载后遵循其AGENTS与LICENSE；依赖安装/构建和模型执行分别记录。npm latest=0.1.5-rc.2与当前源码不一致，不能混用API。

## A0 实施顺序

1. 已完成固定源码构建和launcher help/版本检查；独立设置 `DSH_HOME`，不用默认个人配置。模型、凭证与策略固定仍待后续接入。
2. 根据官方Web模板创建项目profile，在启动模型前展开有效配置。第一次创建与已存在profile的启动参数分开处理。
3. 禁用Web默认standard/PTC/Cordis/minimal presets及不需要的执行插件，注册项目专用preset。A0只允许list/read/write和图片探针；CSV工具等通用增强排在A1，先以无模型加载与调用测试证明生效。
4. 关闭独立的DeepSeek session-log contributor和OTel会话上报，复核插件管理、终端、网络与配置覆盖入口。
5. 在Cordis插件中注册最小工具，最终执行guard做fail-closed检查；再验证官方Web中的模型、会话、一个受控文件任务和两种图片路径。达到最小门槛后优先接C0真实桌面，不等待CSV完整业务流程。

官方CLI有 `--profile`、`--from-default-profile`、`--patch`、`--dump-config` 等入口。创建自定义profile时可从web模板初始化；同一profile已经存在后不能重复传初始化参数。它们是固定源码文档提供的机制，不是本项目已验证的启动命令。

配置补丁替换整个config块。实施时必须保存最终展开结果，不能从一段YAML推断全部生效配置。

## 本地安装与检查（2026-09-23）

源码与构建产物：`/Users/zhangchengjie/CUAgent/.runtime/harness`。项目本地 pnpm：`/Users/zhangchengjie/CUAgent/.runtime/toolchain/node_modules/.bin/pnpm`，未全局安装。

```bash
cd /Users/zhangchengjie/CUAgent/.runtime/harness
../toolchain/node_modules/.bin/pnpm install --frozen-lockfile --store-dir ../pnpm-store
../toolchain/node_modules/.bin/pnpm run build
DSH_HOME=/Users/zhangchengjie/CUAgent/.runtime/harness-home \
  ../toolchain/node_modules/.bin/pnpm dsh --version
DSH_HOME=/Users/zhangchengjie/CUAgent/.runtime/harness-home \
  ../toolchain/node_modules/.bin/pnpm dsh --help
```

以上安装时通过。锁文件SHA-256：`b86256be5afec5814a404747893cab392a73b40901d14fa8135f663fb42c8d40`。上游源码安装后已应用下面记录的本地补丁，工作树不再干净。独立home、workspace、runs已建立；没有配置API Key、授权桌面或修改个人配置。

本地记录：`.runtime/harness-installation.json`、`.runtime/harness-build.log`、`.runtime/harness-install.log`（后者为构建后的离线锁文件复核）。首次安装在CLI产物生成前提示三个SDK/desktop workspace的`dsh` bin链接缺失；构建后离线install未补建它们。已验证的入口是上述根目录`pnpm dsh`，这些子包入口未验收。构建另有上游弃用项及bundle体积警告，不影响本次退出码为0。全部`.runtime`内容被Git忽略，不公开上传。

## macOS ARM64原生模块修复（2026-09-23）

首次完整构建虽退出0，但Rosetta环境中的`cc`默认生成x86_64，Node却是arm64，导致`system.node`到实际调用时才报架构错误。CLI版本/help不加载此模块，不能替代原生功能验收。本次未修改上游源码，仅在ARM64 shell中重新执行官方原生模块构建：

```bash
cd /Users/zhangchengjie/CUAgent/.runtime/harness
/usr/bin/arch -arm64 /bin/zsh -f -c '/usr/bin/cc -dumpmachine && exec /opt/homebrew/Cellar/node/24.9.0/bin/node /Users/zhangchengjie/CUAgent/.runtime/toolchain/node_modules/pnpm/bin/pnpm.mjs run build:native-system'
file native/system/packages/darwin-arm64/bin/system.node
TMPDIR=/Users/zhangchengjie/CUAgent/.runtime/workspace node --test --test-name-pattern='^(acquisition resolves asynchronously|separate opens of one file contend|closing the locked fd allows|invalid fd rejects asynchronously)' native/system/test/flock.test.js
```

结果：文件为Mach-O arm64；ARM64 Node实际`require`成功并检查`tryLock`导出；异步加锁、锁竞争、释放再获取、非法fd四项测试通过。此项修复时上游工作树仍干净；后来因下述插件元数据修复而有本地修改。模型、凭证、会话和正在运行的Web进程未修改；用户需停止并重新启动dsh。完整Web/模型链路仍未由本次测试验证。

后续在同类Rosetta终端做完整构建时，使用上述`arch -arm64 /bin/zsh`命令，将最后的`build:native-system`换为`build`，然后再次检查产物架构和实际加载；直接执行旧的完整构建命令可能覆盖回错误架构。

## 插件元数据错误修复（2026-09-23）

Web插件卡片读取可选`locale/en.json`时，Node可能返回只读`stack`的`ERR_PACKAGE_PATH_NOT_EXPORTED`。固定版Harness的profile resolver直接改写`error.stack`，抛出新的`TypeError`，使元数据回退失效。已在本地上游源码修复两处改写：保留原异常和`code`，只在允许时更新诊断栈；补丁及回归测试保存在[readonly-error-stack.patch](../../patches/harness/readonly-error-stack.patch)。重新克隆固定commit后，在源码根目录执行`git apply /Users/zhangchengjie/CUAgent/patches/harness/readonly-error-stack.patch`，不要重复应用。

验证命令：`../toolchain/node_modules/.bin/pnpm exec vitest run packages/boot/app-boot/tests/profile-resolution.spec.ts packages/boot/app-boot/tests/package-meta.spec.ts --reporter=dot`，结果304通过、1跳过；`git apply --reverse --check`通过。`pnpm run build:lib:host`成功，编译产物包含修复，`system.node`仍为arm64；未执行会重编原生模块的完整`build`。尚未在重启后的Web界面复验插件卡片；此修复不代表A0完成。用户重启dsh后再刷新插件页检查红色元数据错误是否消失。

## 工具接口适配

固定参考版本使用Cordis插件 `apply(ctx)`，通过工具注册服务接入定义；`execute(args, exec)`返回与 `output.schema` 一致的JSON值，`output.render`投影为模型可见内容。适配器需显式传递 `exec.signal`，复核并发与超时语义。

工具定义的 `timeoutMs` 是声明，实际超时需要 `dsh-tool-call-timeout-policy` 执行包装器；取消必须由工具协作响应，不会回滚已经发生的副作用。

最终 `ctx.tools.guard` 可拒绝执行，返回拒绝原因或不改变已有决策；guard没有“强制允许”返回值。作用域工具过滤不能替代最终guard；还要检查插件本身可能直接执行的能力。

Pi工具层的导入、注册、写入队列和 `details/content`结构需要重写。现有纯核心函数和测试无需因换框架重写。图片探针必须返回实际可读内容；Web专用卡片使用Client插件机制，Host-local的 `presentCall/presentResult` 不是Web卡片接口，A0优先使用通用显示。

## 有效配置必须覆盖的差异

- Web根tool-bash/tool-fs被禁用不代表Agent preset里没有同类工具，必须检查preset内部注册。
- 固定版本的sdk-minimal默认提供持久Bash/PowerShell并使用danger-full-access；名称中的minimal不是权限最小化。
- fs-sandbox不限制reads/listings/metadata，写入范围也未必等于本项目任务目录。
- `session-log-deepseek` 的 `enabled: false` 与 `session-telemetry-otel` 的 `mode: DISABLED` 是两条独立配置；只设OTel环境变量不等于关闭DeepSeek日志贡献。记录网络实测，不能只看配置文本。
- 原生Computer Use provider操作它所在的机器；执行进程放测试VM，另加项目桌面控制权协调。上游服务的单provider注册不是跨进程锁。

以上是开发检查点，尚未生成可执行profile或宣称完成限制。最小底座与Computer Use验收见 [阶段计划](../../Harness_Development_Plan.md)。

## 固定源码参考

- [package.json](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/package.json)
- [CLI参考](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/apps/cli/reference/README.md)
- [添加工具](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/docs/cookbook/adding-a-tool.md)
- [Web配置](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/bundle/web-app/cordis.patch.yml)
- [Agent preset](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/preset/agent-preset/README.md)
- [文件沙箱](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/fs/fs-sandbox/README.md)
- [DeepSeek会话日志](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/session/session-log-deepseek/README.md)
- [OTel会话上报](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/session/session-telemetry-otel/README.md)
- [Computer Use服务](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/computer-use/computer-use/README.md)
- [Cua native provider](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/experimental/computer-use-cua-driver-native/README.md)
