# P2 最小任务后端技术方案（实现前）

2026-10-02，分支 `p2-task-service`，基于已推送 P1 `7d0bb3f`。目标：提交资料取得 task ID，独立 Worker 调用已验证日报流程，离开页面后仍可查询事件、用量与核对后的产物。复用官方 Harness 主循环、P1 oracle 和原 30 次总账，实际推理固定 DeepSeek 4.1 Flash / off。

## 组件和运行环境

FastAPI 提供 HTTP；PostgreSQL 持久任务、执行尝试、事件、用量、产物索引和资源执行权；SQLAlchemy 2 管短事务、Alembic 管版本；独立 Python Worker 调用现有 TypeScript Desktop RPC 适配器。数据库使用独立 Docker 容器/卷，绑定 127.0.0.1:55432，API 绑定 127.0.0.1:18089。启动前检查端口与容器名，不改现有 suixinji/digital-human PostgreSQL 或 Redis。

第一版仍要求本机官方 Desktop/Host 就绪；只启用 daily-report 模板，不接宿主 GUI。Worker 在原 App 全局 idle 时正常切换批准配置，单任务结束后恢复原 A1 配置。暂不追求每个任务零重启；启动开销单独记录，后续才评估动态注册。没有 API 进程内 BackgroundTasks 长任务。

## 接口与存储

- POST /tasks：接收日期、1–3 份记录与 1–2 份 CSV 的受限文本，服务器分配路径；不接受客户端绝对目录。Idempotency-Key 对应请求正文哈希，同 key 同正文返回原任务，不同正文 409。
- GET /tasks、GET /tasks/{id}：分页和任务状态、预算/用量、错误码、产物引用。
- GET /tasks/{id}/events：有序 cursor 查询，必要时 SSE 包装；无需把原始模型全文放 API 日志。
- POST /tasks/{id}/stop：持久记录停止请求，执行端关闭新派发，再取消原官方会话并保留在途事实。
- POST /tasks/{id}/resume：重新领取同一任务/账本，检查原 session 与产物；不新建预算、不重放未知写入。P2 先支持中断后接回原会话并核验，需生成新模型续接或现场恢复的情形留 BLOCKED/UNVERIFIED，P3 完善。
- GET /tasks/{id}/artifacts/{name}：只允许登记且 SHA 一致的 report.json/report.md；失败产物保留私有目录，不作为“已核对报告”下载。

API 使用本地专用 Bearer token，凭证位于忽略的 0600 环境文件。受限任务请求可保存数据库中供准备恢复，原始轨迹和产物放私有磁盘，数据库保存引用与 SHA；不把凭证、完整提示或个人材料写入普通事件。模型不能写数据库、审计、oracle 或控制文件。

新增调度状态 QUEUED、STOP_REQUESTED、STOPPED；沿用 RUNNING/SUCCEEDED/FAILED/BLOCKED/UNVERIFIED 的业务含义。只有独立验证成功才 SUCCEEDED。任务关联固定 task_id/run_id/session_id；attempt 表用于执行领取记录，不代表另开 Agent 任务或新预算。准备/派发意图先持久化，超时先查同一请求身份。

## 领取、停止和恢复

领取通过 PostgreSQL 短事务 SELECT FOR UPDATE SKIP LOCKED；资源表确保一个 Harness/VM 资源同时只有一个 owner/epoch。数据库事务不跨整个模型执行；本机 Worker 另持跨进程文件锁，避免数据库连断后两个执行者直接重启同一 App。

批准任务可带私有 controlPath/epoch。后端心跳更新租约；A1 请求/工具最终准入检查租约未过期、epoch 正确、任务未停止。读取和写入前都检查；内部 renderer 读取仍扣原总账。停止标志在同 epoch 不可被延迟心跳覆盖；旧 epoch 写控制文件应拒绝。既有 A1 配置没有 controlPath 时维持原行为，新增任务不能通过缺一个控制字段降级。

Worker 进程退出不说明 Desktop 会话已终止；新 Worker 必须查同一 session，不自动重新 prompt。P2 对原始副作用不明保留 UNKNOWN/UNVERIFIED；恢复需旧 owner 已退出、资源执行权重获、预算连续。完整现场恢复、1/8 小时连续运行与无进展检测属于 P3，不提前声明。

## 验证与交付

先真实独立 PostgreSQL 集成：迁移/重启、同 key 并发提交、冲突正文、两连接竞争领取、过期 owner 拒绝、停止与租约、产物路径与 SHA、事件 cursor。执行端同版官方工具注册测控制文件缺失/过期/停止/epoch 拒绝与内部调用计数；不靠 mock 宣称真实桌面安全。

然后独立 API/Worker 进程实测：提交合法日报→取得 ID→API 正常重启→任务仍在→Worker 实际调用 Flash/off→独立验证→GET 状态/事件/用量→下载报告与原产物 SHA 相同；另测排队停止、重复提交没有新 session/新账本。只有这一整条闭环通过才收口 P2。更新 README、启动例子、故障与未测项，验证后推送阶段及默认分支。

设计依据：[PostgreSQL 队列锁](https://www.postgresql.org/docs/current/sql-select.html)、[FastAPI BackgroundTasks 适用范围](https://fastapi.tiangolo.com/tutorial/background-tasks/)、[SQLAlchemy 事务边界](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)。版本在依赖锁及实际运行记录中固定，不将文档版本等同部署版本。
