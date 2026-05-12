# TrendRadar — Agent 速览

面向在本仓库工作的 AI / 协作者：新会话请先读本文件或 `@AGENTS.md`，再按需 `@` 具体代码。详细功能与部署以根目录 [`README.md`](README.md) 为准。

## 项目是什么

- **TrendRadar**：多平台热榜 + RSS 聚合、关键词 / AI 筛选、报告（HTML 等）、多渠道通知；可选 **MCP 服务** 供外部客户端调用。
- **技术栈**：Python ≥ **3.12**（见 `pyproject.toml`），依赖管理推荐 **uv**，AI 统一走 **LiteLLM**（`openai/模型名` + 兼容 OpenAI 的 `api_base` 等）。

## 目录导航（二开从哪看）

| 路径 | 说明 |
|------|------|
| [`trendradar/__main__.py`](trendradar/__main__.py) | CLI 入口：`python -m trendradar`（调度、爬取、分析、推送、报告） |
| [`trendradar/core/`](trendradar/core/) | 配置加载 `loader.py`、调度 `scheduler.py`、业务分析编排等 |
| [`trendradar/crawler/`](trendradar/crawler/) | 热榜抓取、RSS 拉取与解析 |
| [`trendradar/ai/`](trendradar/ai/) | `client.py`（LiteLLM 调用与 `[LLM]` 日志）、`filter.py`、`analyzer.py`、`translator.py` |
| [`trendradar/storage/`](trendradar/storage/) | 本地 SQLite 等存储抽象 |
| [`trendradar/report/`](trendradar/report/) | HTML 等报告生成 |
| [`trendradar/notification/`](trendradar/notification/) | 通知渲染、分批、各渠道发送 |
| [`mcp_server/server.py`](mcp_server/server.py) | MCP 服务入口：`python -m mcp_server.server` |
| [`config/`](config/) | `config.yaml`、`timeline.yaml`、`frequency_words.txt`、各类 prompt 文本 |
| [`docker/`](docker/) | 镜像、compose、`manage.py`（容器内运维） |
| [`output/`](output/) | 运行产物（HTML、db 等），勿提交敏感数据 |
| [`.cursor/rules/*.mdc`](.cursor/rules/) | 本仓库 Cursor 规则（安全、前后端约定等） |
| [`.ai/`](.ai/) | 协作手册与模板；**若其中 `context/project_overview.md` 与当前单仓布局不符，以本 `AGENTS.md` 与真实目录为准** |

## 环境与启动

**安装依赖**（在仓库根目录）：

```bash
# 推荐：已安装 uv 时
uv sync

# 或：pip 安装 uv 后
python -m pip install uv
python -m uv sync
```

**主程序（抓取 → 筛选 / 分析 → 报告 / 通知）**：

```powershell
# Windows 建议先设 UTF-8，避免控制台编码问题
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe -m trendradar
```

```bash
# 类 Unix / 已配置好终端编码时
uv run python -m trendradar
```

**常用子命令**：`--doctor`（体检）、`--show-schedule`（调度状态）、`--test-notification`（测通知）。

**MCP 服务**：

```powershell
$env:PYTHONUTF8="1"
.\.venv\Scripts\python.exe -m mcp_server.server
# HTTP 示例见 start-http.bat / start-http.sh
```

**一键脚本（Windows）**：[`setup-windows.bat`](setup-windows.bat)（检查 Python、安装 uv、同步依赖、提示配置路径）。

## 配置要点（勿把密钥写进版本库）

- **主配置**：[`config/config.yaml`](config/config.yaml)（推送、平台、RSS、AI、存储等）。
- **AI**：LiteLLM 要求 `model` 为 **`provider/model`**（例如兼容 OpenAI 的第三方：`openai/实际模型名`）；`api_key` 优先用环境变量 **`AI_API_KEY`**，避免将真实 Key 提交到 Git。
- **Cursor MCP 本地文件**：`.cursor/mcp.json` 已在 [`.gitignore`](.gitignore) 中忽略；模板见 [`.cursor/mcp.json.example`](.cursor/mcp.json.example)，复制后本地填写。

## 日志与排查

- 每次大模型请求：`trendradar/ai/client.py` 会打印 **`[LLM] 请求开始` / `请求成功` / `请求失败`**，可按 `label`（如 `ai_filter_classify_batch`、`ai_analysis`、`ai_translation`）区分阶段。
- 官方文档与排错仍以 [`README.md`](README.md) 及其中链接为主。

## Docker

- 编排与说明见 [`docker/`](docker/) 与 README 的 Docker 章节；容器内常通过环境变量与挂载的 `config/` 运行。

## 上游与合规（简述）

- 若本仓库基于上游衍生，请遵守上游 **LICENSE**，并在对外 README 中说明衍生关系；具体条文见仓库内许可证文件。

## 给后续 Agent 的一句话

改业务逻辑优先读 **`trendradar/__main__.py` → `core/` → `crawler/` / `ai/` / `report/` / `notification/`**；改对外工具读 **`mcp_server/`**；改行为与数据源读 **`config/config.yaml`** 与 **`config/timeline.yaml`**。
