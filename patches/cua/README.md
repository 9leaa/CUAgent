# Cua / Lume 隔离补丁

## Driver CLI错误诊断候选（隔离CLI验证通过，未安装）

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
