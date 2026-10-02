# A1 通用受控插件扩展示例与第二人交接

示例：`agent/workspace-text-fingerprint.mjs` + `agent/harness/a1-example-fingerprint.ts`。当前作者的集成测试通过不算第二位开发者验收。默认 A1 六工具和 A0 五工具都未加入此工具。

## 接口和责任

| 层 | 专业说明 | 直白说明 |
|---|---|---|
| 工具核心 | 框架无关函数，复用 UTF-8、扩展名、大小、相对路径和链接边界 | 只在指定目录查文件，不碰 shell/网络 |
| Harness 适配 | `defineTool` 描述输入/输出，`exec.signal` 检查取消，调用 live admission service | 告诉模型怎么调用，但先检查是否获准 |
| 执行策略 | 注册候选不授予能力；任务显式允许、session 根绑定、30 次持久计数 | 挂了工具也可能不能用，重启不送次数 |
| 独立验证 | 保护的字节与 SHA 期望、实际 call/result、派发审计交叉核对 | 不靠模型自己说对了 |

`workspace_text_fingerprint` 输入为 `{"path":"relative.txt"}`，不允许额外参数；输出严格为 `{"path":"relative.txt","bytes":123,"sha256":"64 lowercase hex characters"}`，不返回正文。支持 .txt/.md/.json/.csv、UTF-8、最大 1 MiB，继承读取核心的 200 行/64 KiB呈现限制与单行拒绝，不通过 shell 实现哈希。正文核心调用不是第二次 Harness 调用，整个工具只消耗一次实际准入；若在工具内部另调注册表工具，必须另计数，不能偷偷封装多个能力。

错误码由 `withWorkspaceErrors` 将核心错误转成同版 `HarnessError`，保留到官方 `ToolExecutionResult.error.info.code`；普通 Error.code 不会自动保留。路径为 `ABSOLUTE_PATH_DENIED`/`PARENT_PATH_DENIED`/`SYMLINK_ESCAPE_DENIED`，类型/编码/大小为 `FILE_TYPE_DENIED`/`BINARY_FILE_DENIED`/`FILE_TOO_LARGE`，缺失路径为 `NOT_FOUND`，其他不可用为 `UNAVAILABLE`；实际注册集成已核对 `PARENT_PATH_DENIED`。未知任务、未批准工具、停止、预算、失效审计由策略拒绝。执行前与核心返回后检查取消，不重新派发；在途副作用 UNKNOWN 必须独立核对后处理，不能把 AbortError 当作未执行证明。

文本工具的 `output.render` 产生官方文本内容块，不自建聊天 UI。图片参照现有 `image-probe.ts`：先核对实际模型支持 image、取消与准入，再通过官方附件服务保存 PNG，返回 `type:image` + attachment 引用；不是返回宿主图片路径或 base64 文本。颜色答案只写保护的验证记录，不发给模型。不要让模型任意打开附件、宿主目录或修改验证器。

## 第二位开发者独立任务（用户已明确暂缓）

2026-10-02 用户确认所有第二人验收暂缓，以下作为后续交接清单保留，不要求本次寻找参与者，不阻塞 A1 本地收口；没有执行便保持未验。

1. 在自己的工作分支选择一个新的受控工具（例如 UTF-8 文本的去空白计数）；提交其参数/结果 schema、稳定错误码、取消和副作用说明。不得修改官方 Agent 主循环，不放开 shell、网络、MCP 或子 Agent。
2. 核心与适配分离。以 fingerprint 为参考，但独立实现自己的功能和独立预期，不能把复制示例测试或本代理通过结果当作交叉复现。
3. 由人审查能力后加入 `A1_REVIEWED_EXTENSION_TOOLS` 候选表；只在新的专用任务配置中显式允许，在专用 preset 中挂载。默认六工具、A0/C0 白名单保持不变。不要自动扩大既有任务权限或复用其账本身份。
4. 给构建入口加入自己的适配，使用当前安装的官方 App 同版本接口；创建全新 session/run/root，配置/期望/审计在模型根之外。执行前正常结束已有 App，保留账号和原任务，不复制旧凭证，不改 VM/端口。
5. 独立跑正常输入、越界/错误类型、取消、未授权任务、30 次上限与卸载拒绝。至少一次正常真实官方结构化调用并独立核对产物；拒绝测试记录实际注册表/模型/执行层范围，不能混写。
6. 交付代码差异、执行命令、固定 App/模型版本、session/run/call关联、输入/产物字节哈希、正常及失败记录、使用次数和未测项。公开材料脱敏，账号、密钥、原始会话不上传。维护者决定提交/推送和是否验收。

本示例候选只允许通过已存在的项目任务根获取文本指纹。新增工具名不会自动获批：即使插件注册成功，只要任务配置没有此能力，执行仍被根 guard 拒绝。文档、Skill、测试输入和模型 Prompt 都不能改这个条件。
