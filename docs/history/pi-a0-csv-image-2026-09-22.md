# A0 CSV 与图片链路验收摘要

日期：2026-09-22

## 固定环境

- Pi：0.86.1
- Node.js：24.9.0
- 模型：`deepseek/deepseek-flash`（命令显式选择）
- 工作区：`.runtime/workspace/a0-validation`
- 内置工具：全部关闭
- 项目工具：`workspace_list`、`workspace_read`、`workspace_write`、`workspace_csv_stats`、`workspace_image_probe`

## 本地验证

命令：

```bash
node --test agent/tests/*.test.mjs
sh -n agent/pi-local.sh
git diff --check
```

结果：31/31 Node.js 单元测试通过；启动脚本语法和 Git 空白检查通过。Pi 离线启动显示五个扩展均加载成功，没有调用模型。

## CSV 真实模型验收

输入：`a0-validation/sales.csv`，要求统计 `units` 和 `revenue`，将工具 JSON 保存为 `csv-stats.json`，生成 `csv-report.md`，再用 `workspace_read` 读回。

结果：模型调用 `workspace_csv_stats`，随后写入并读回两个产物。独立脚本 `node agent/verify-a0-csv-result.mjs` 通过：

- 行数：5
- `units`：count 5、missing 0、sum 14、min 1、max 5、mean 2.8
- `revenue`：count 4、missing 1、sum 430、min 70、max 150、mean 107.5

文件 SHA-256：

- `sales.csv`：`ff77cc7ce9aaeb8ba6d442c79abfb3e120c1344f6059e0b90165aab6d82f2731`
- `csv-stats.json`：`c3e5bb4f9d158341b8cd19cc010d85965fba6fb4bdb94a8403544223c2ada429`
- `csv-report.md`：`419f460525b54ecb521232b87be8252dfb2c1d954f827385e89bf32b4abe0f38`

## 图片真实模型验收

固定测试图为 96×64 PNG，四象限独立生成：左上红、右上蓝、左下绿、右下黄。

- 图片输入：通过 `@a0-validation/image-input-probe.png` 发送，模型按顺序正确返回四种颜色。
- 工具图片输出：模型真实调用 `workspace_image_probe`；会话记录包含 `toolCall`，对应 `toolResult` 同时含 `text` 和 `image`，模型正确返回四种颜色。
- 工具图片验收调用：599 input、47 output、2432 cache-read tokens，记录成本约 `$0.000250692`。

原始会话和生成产物保存在已忽略的 `.runtime/`，未提交凭证、原始会话或 base64 图片。

## 限制

- 当前默认模型仍显示 `deepseek-v4-pro`，它的模型清单不支持图片；本次用命令显式选择 `deepseek-flash`。默认模型固定和重启保持仍待验收。
- CSV 与图片链路是真实模型验收；路径越界是本地单元测试，尚未保存真实模型主动越界的拒绝证据。
- 未启动 VM，也未执行 Computer Use。
