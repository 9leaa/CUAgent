# P7 最终输出协议调查

2026-10-07；调查，不代表实现或真实模型验收。

## 问题与证据

第五批原normal任务在25/30raw完成有效草稿、GUI保存/重开及result读回，但原最终助手消息在JSON前加了解释，严格解析第1列失败。保留UNVERIFIED，不截取JSON、不修补原会话、不把工具草稿代替最终模型响应。原应用随后人工正常退出，文件字节/SHA未变。

## 已安装框架核查

通过官方App自身Electron Node只读实际asar文件，三个包均0.2.0-rc.2；不是仅检查上游参考源码。对应lib/index.js SHA256：

- dsh-llm：9132c8a8053ee82b9fb1ded4f98c85cf557f288a15a85c552c6b1fb319ead120
- dsh-llm-deepseek：226e2047b843f954d8478207613f3e44448671c6f98f8edee77008d0fe005484
- dsh-deepseek-llm-api-extensions：3a8bafed2f2a0d024dbcf6c66552230448a8d62add71cb523fb81e96a4e9a875

当前适配器构造Messages协议并POST到/messages，不能直接套用Chat Completions参数。构造器未提供response_format/json_schema/json_object，output_config仅包含非off的effort；参考源码GenerateOptions同样没有最终响应格式选项。以上只能说明当前接口没有直接能力，不能证明服务端一定不支持。

deepseekLlmApiExtensions能注册并合并额外顶层字段，但这只是传输扩展，不是服务端能力声明。字段与基础请求冲突会拒绝；合并序列化失败会发出不带扩展的基础请求，因此未经额外失败关闭检查不能声称输出格式得到强制保证。本次没有向真实账户发送试探字段。

## 后续门槛

1. 首先取得该账户Messages路由的明确协议证据；不能用其他模型、API-key路由或另一协议文档替代。
2. 若确有支持，再先写实现方案：只绑定原业务session及最后输出阶段，保持Flash/off、停止和原预算；未知能力或扩展缺失立即拒绝，不静默降级。增加安装版请求捕获、会话隔离、扩展失败和严格解析反例后才考虑新候选。
3. 若不支持，不继续堆提示或换样本。结构化提交工具属于交付契约变更，须另写方案并明确审批：真实模型提交、原调用审计、独立源事实和GUI验收仍必须成立，不能偷偷用工具结果代替当前最终JSON契约。

原失败及未派发任务保持原身份。此调查不证明报告语义、真实格式约束、正式发布或P7业务已通过。
