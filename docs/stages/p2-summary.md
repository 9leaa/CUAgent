# P2 后端与日志验收

2026-10-02，分支 p2-task-service。技术方案提交 f7911f4 先于实现。FastAPI、PostgreSQL、SQLAlchemy/Alembic、独立 Worker、客户端和执行端租约保护已实现；使用见 [后端说明](../../backend/README.md)。

## 实际证据

- 原真实任务 `63b72761-c5d9-4a39-931a-1d149f70ac87`：重复提交同 ID；API 正常退出重启后仍 QUEUED，再由独立 Worker 实际执行到 SUCCEEDED，9/30，11827 token，下载两报告 SHA/字节数一致。私有证据 `.runtime/backend/acceptance-001/`。
- 排队停止任务 `b2b4943f-08a1-46bc-ac7f-85b1899bb2fe`：STOPPED、session 为空、零调用；Worker 不领取、产物返回 404。
- 补齐工具审计后新真实任务 `286a5749-803a-4100-8aa7-e7b53729e846`：官方 session `session-c9475b95-2dfa-4398-a5a8-ad2de8407f0b`，9/30、SUCCEEDED。API 有 9 次派发及 9 次对应结果，包含 renderer 内部读取；游标续查为空，日志不含原始 args/prompt。两份下载 SHA/字节数与登记一致。证据 `.runtime/backend/acceptance-audit-001.json`。
- 新任务 input 2016、output 682、cacheRead 9472、cacheWrite 0、total 12170；官方请求实际 DeepSeek 4.1 Flash/off。货币费用缺失则 null，不猜价格。Markdown 588 字节，SHA `eb8c062e09cbb93b366be176fdc3c4862f2794f0244a8b971c9aae1fd5c7c5c9`。

## 测试与边界

真实 PostgreSQL 测试 10/10：并发幂等、单资源领取、停止不可被心跳覆盖、旧 owner/epoch 拒绝、预算不减、API 重建、输入拒绝、产物篡改及审计幂等/隐私/身份。官方注册集成 30/30（新增租约拒绝）；核心 59/59、P1 Python 12/12、VM Python 123/123。后两类不冒充本轮真实 VM 测试。TestClient 有一条 httpx 弃用提醒，不影响测试结果。

实际运行 Python 3.12.12、FastAPI 0.142.2、SQLAlchemy 2.0.54、Alembic 1.20.0、psycopg 3.3.6、PostgreSQL 16.14；精确依赖和容器摘要已固定。独立容器 cuagent-p2-postgres/55432，API/18089，不接公网、不改变既有服务。

原始任务成功只由 P1 独立验证器决定；运行停止的执行端拒绝有同版注册测试，完整进程退出/断连后的真实现场恢复和 1/8 小时运行尚未验收，留 P3。P2 resume 只接回原会话，未知副作用不重放；不把本阶段短任务宣称长时间无人值守。C3/第二人继续暂缓。
