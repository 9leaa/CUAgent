# Cua / Lume 隔离补丁

2026-10-15父链包更新：原生适配返回分类覆盖及逐层无正文诊断已补，模块479通过/6忽略、完整构建通过。独立静态包已签名并读回，签名后SHA`12cf062a32d81b14877afa493e805b4ab24f7bac168e292971a50ab0d1659330`，准入固定新路径/摘要且12项测试通过。新包未启动/授权，原Driver未替换，不是实际输入/保存验收；下方“未部署”是上一轮记录。

2026-10-15父链候选（仅macOS，未部署）：`driver-focus-diagnostic.patch`新增严格同PID、有界窗口解析，不复用上游Sheet到父窗口的映射；模块477通过/6忽略，反向去掉匹配检查触发两项失败，恢复后10项通过，完整构建通过。尚待原生返回边界覆盖与诊断补齐，再重新签名部署；下方旧摘要不代表新产物，不沿用旧权限/准入。两秒检查是超时后不发送动作，不是强制中断同步AX调用。

2026-10-15新候选补充：窗口错误纯函数反例及反向移除检查验证完成，模块472通过/6忽略；完整构建与VM独立静态签名部署通过，签名后SHA为`1c3315747d6775c8e3a396c1adf3f3d62481ddd2351ed9de9293c3bb59ef00de`。新App未启动/未授权，原Driver未替换；下方“尚未构建部署”为此前步骤记录，不作为当前状态。

2026-10-15补充：foreground_point错误增加AXWindow属性状态/值存在标记、窗口查询状态/ID；point_preflight保留query_error。仅增强私有诊断，不新增原生查询或改变放行条件。模块471通过/6忽略，完整补丁反向应用检查通过；当前尚未构建部署，不能沿用旧二进制摘要或声称Calc输入已修复。

## PointGuard权限助手身份取证窗口

`driver-permission-identity-window.patch`在现有身份补丁之后应用。仅macOS独立PointGuard助手成功写出权限报告后保留10秒存活窗口，供可信监督从进程表读取完整路径、唯一结果文件参数和PID；原报告不改，正式/Local不等待，不增加工具请求。启动回调曾在实机返回PID=-1，不能代替独立身份。Rust1.97.1/SDK15.5构建及305项CLI测试通过；新独立VM包的007实测PID与报告匹配，但两项权限false，业务仍被拒绝。10秒不保证调度，未观察到身份仍须拒绝；外层必须清理并恢复服务，不得复活旧任务。

## Driver焦点诊断与精确key窗口保护候选

PointGuard身份补丁`driver-pointguard-identity.patch`应与命中保护补丁一起应用于固定0.34.1源码。精确识别包目录/可执行名，分离CLI、bundle、state/home命名空间，权限助手从当前包路径启动；不借用正式/Local身份。两项单元测试及三个真实临时路径的无GUI身份探针通过；不等于VM权限或业务验收。

旧系统命中候选曾在测试VM独立打包为`CuaDriverPointGuard.app`/`com.trycua.driver.pointguard`，adhoc签名后的可执行SHA为`01c3db9176267741a1608c971f2233e0371611d13f2346fecbf97c648f2d2c16`。009临时授权后助手空回执失败，权限已撤销；该旧产物缺少内部身份补丁，不得作为修复后候选。构建/签名后须记录新摘要并更新准入，不能复用旧ready或许可。

当前系统命中版已完成相同SDK/工具链下的完整`cargo build --locked -j2 -p cua-driver`，arm64产物SHA256为`661e761263c072c86f83bd82ac3baabe87a1b1063b0af71281197d0404642654`；仅私有构建保存，未打包重签、部署或调用真实GUI。旧准入固定摘要不能用于此新产物。

2026-10-13系统命中版进一步增加foreground_point模块：ForegroundHid像素click在激活后的闭包内做系统级AX点查询，只允许命中原PID/window。全局查询错误、缺窗口和目标不同均拒绝；不影响背景/AX点击或键盘。新增4项测试，模块469通过/6忽略，移除匹配条件的反向测试失败。point_preflight仅是输入前状态，action_attempted仅表示进入外围闭包；都不能证明最终事件接收者或不存在竞争。此版尚未实机验证，不将旧007/008结果升级。

`driver-focus-diagnostic.patch`基于下方相同Driver 0.34.1提交及MIT许可，在隔离源码目录应用，不覆盖已授权App。`CUAGENT_FOCUS_DIAGNOSTICS=1`记录私有stderr JSON行，包括光标前后、精确焦点与前台身份、HID的preserve/temporary分支及恢复事实。默认不采样；读取AX和同步日志仍可能改变时序。日志不含文档内容，但含进程身份，应私有保存。

2026-10-13起本补丁不再只是日志：临时前台分支要求make_exact_window_key成功，再等待精确AX焦点，才允许执行一次原动作；失败保留错误并走原前台恢复。新增make_key_returned和action_attempted，区分拒绝与实际发送。已有精确前台的preserve分支不变。本项不证明屏幕无遮挡或实际点击接收者，也不提供自动重试；仅macOS候选，未部署或声称跨平台修复。旧007/008运行的是此前日志版，其失败不能归给本次新增逻辑。下方构建与权限记录属于历史版本。

固定Rust1.97.1：`cargo test --locked -j2 -p platform-macos --lib`为462通过/6忽略；`cargo build --locked -j2 -p cua-driver`通过。新增两项为JSON单行及输出错误不panic，不代表完整日志分支实机覆盖。2026-10-12临时服务准入发现独立候选没有原App权限，未执行业务动作或授予新权限。启动会派生daemon，不能只清理Popen父PID；须核对实际可执行文件和socket所有者后退出确切候选，再恢复原App。原服务/权限/Worker现已恢复，原失败回执保留；未修复或验收真实聚焦。

2026-10-13保护版：相同锁文件及Rust1.97.1，显式`SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX15.5.sdk`执行上述模块测试为465通过/6忽略；新增3项验证失败零动作、调用顺序及原错误无重试。反向移除make-key保护后对应测试失败，恢复代码复验。默认SDK26会在上游apple-cf Swift桥报IOSurface类型不兼容；不修改全局SDK或依赖来掩盖。此版尚未构建完整daemon或部署，旧二进制摘要不适用于本次补丁。

## Driver CLI错误诊断候选（独立CLI已实机取证，原App未替换）

2026-10-12更新：固定候选SHA256 `1c86beeaaf07d0deb43fa232961606ea8984ca1202e7e3e102e6c924ac6a2104`独立部署到VM私有目录，显式连接原socket。status及官方DSH005真实工具传输通过，失败stderr保留完整精确窗口焦点说明；原daemon/App/权限未改。该补丁只完成诊断输出，未修复焦点或实现保存重开。下方未安装描述为构建时记录。

`driver-cli-error-detail.patch`独立于下方Lume补丁，基点为Driver标签`cua-driver-rs-v0.34.1`解析的提交`0c69d9a2c8abbb5051a2df4a23f0fa166d5385dc`，同MIT许可。仅在工具失败且stdout已输出结构化响应时，把原content中的文本写入stderr；成功stdout、退出码、daemon调用、权限、会话、派发次数不变。CUAgent已有私有审计对每个输出流保留最多4096字节预览和完整摘要，文本不得作为模型指令。

本候选不修前台激活本身，不恢复旧UNKNOWN。只能在隔离上游副本`git apply --check`/应用并构建后测试；不得直接覆盖现有App。2026-10-11已在项目私有目录安装固定Rust 1.97.1（不改全局PATH），同提交源码中应用补丁后构建通过。首次精简checkout漏了编译期所需的`libs/images/sandbox-images.json`，补齐同提交的images目录后继续；无上游依赖版本调整。

将本目录`cli_error_detail_test.rs`复制到上游`libs/cua-driver/rust/crates/cua-driver/tests/`，在其Rust工作区执行`cargo +1.97.1 test --locked -j 2 -p cua-driver --test cli_error_detail_test --test broken_pipe_cli_test`。真实CLI只连接临时模拟Unix服务端，按实际list→metadata→session_end→单次call核对，临时配置和关闭遥测，不启动真实daemon或桌面动作。7组输出场景（普通/空/Unicode/长文本错误、无文本错误、仅文本错误、成功）及上游两项broken-pipe测试通过。首轮模拟器漏接list探测而失败，修正协议后通过；反向移除补丁，同一测试准确因stderr缺失cause而失败，恢复补丁后复验通过。

这是macOS上的真实CLI/模拟daemon验证，不是VM投递或全平台验证。构建仍有上游常量命名和重复rpath警告。尚未签名打包、安装、切换daemon或证明真实前台失败根因；需要独立部署/兼容性审查，不能仅凭此测试替换原App。

下方原Lume说明与基点保持不变。

保留本项目已有五文件补丁与上游许可证，不迁入整套Cua源码。补丁本轮按原字节复制，未重新构建或启动VM。

- 上游：[trycua/cua](https://github.com/trycua/cua)。
- 固定基点：`9bbfa7dd3e27ca7f1861ede70aaca390174493f9`。
- 历史项目改动：开发提交 `e29e22a83`；清理前发布树 `466dd627b4a23284eae5b9d248312bbd07f010f4` 的cua目录。这些是来源标识，不保证旧仓库重写后仍能fetch。
- 许可证：[MIT](LICENSE.md)；补丁：[lume-host-isolation.patch](lume-host-isolation.patch)。

补丁包含三个既有文件修改、一个隔离helper和一个测试文件。`LUME_MVP_HOST_ISOLATION=1` 时拒绝宿主挂载、native查看器/剪贴板桥、动态共享，并去掉隐式共享设备；它不能代替Harness工具权限和任务预算。

## 重建说明

在获准的独立上游目录执行；不要覆盖项目、VM目录或用户全局Lume。先读取上游AGENTS及LICENSE。

```bash
git clone https://github.com/trycua/cua.git cua-upstream
cd cua-upstream
git checkout --detach 9bbfa7dd3e27ca7f1861ede70aaca390174493f9
git apply --check /Users/zhangchengjie/CUAgent/patches/cua/lume-host-isolation.patch
git apply /Users/zhangchengjie/CUAgent/patches/cua/lume-host-isolation.patch
cd libs/lume
LUME_MVP_HOST_ISOLATION=1 LUME_TELEMETRY_ENABLED=false /usr/bin/arch -arm64 /usr/bin/xcrun swift test --jobs 2 --filter mvpIsolation
```

其他开发者替换补丁绝对路径。历史构建使用Swift 6.2；还需要正确virtualization entitlement和签名。单元测试通过不等于签名、VM启动或零共享已验证。

历史两项隔离测试和VM配置检查通过；CUAgent本轮只迁移补丁并校验哈希，不将历史通过写为新运行结果。
