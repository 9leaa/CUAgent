# Cua / Lume 隔离补丁

## Driver CLI错误诊断候选（未构建、未安装）

`driver-cli-error-detail.patch`独立于下方Lume补丁，基点为Driver标签`cua-driver-rs-v0.34.1`解析的提交`0c69d9a2c8abbb5051a2df4a23f0fa166d5385dc`，同MIT许可。仅在工具失败且stdout已输出结构化响应时，把原content中的文本写入stderr；成功stdout、退出码、daemon调用、权限、会话、派发次数不变。CUAgent已有私有审计对每个输出流保留最多4096字节预览和完整摘要，文本不得作为模型指令。

本候选不修前台激活本身，不恢复旧UNKNOWN。只能在隔离上游副本`git apply --check`/应用并构建后测试；不得直接覆盖现有App。必须验证结构化错误+文本、只有文本的错误、无文本、成功、Unicode/长文本、原退出码以及一次请求；再审查签名/权限/原版本回退和授权部署。本机未找到Rust工具链，当前仅验证补丁可应用及CUAgent模拟接收/停止边界，不能称Rust编译或VM兼容通过。

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
