# API 契约摘要

> 与实现及 Swagger 同步；稳定契约写在此，避免仅靠口头约定。

## 通用

- Base URL：部署环境而定；本地默认参见后端 `PORT`（默认 `3001`）。
- 鉴权：多数 POST 需 Bearer Token（详见后端中间件与开放路由列表）。

## 运维探活

- `GET /api/health` → `200`，Body：`{ "status": "ok" }`。

## 管理端 / 数据报表（`sensoube` v3 web · `ReportCenter.js`）

路由前缀：`/api/v3/web/ReportCenter`；成功与业务错误体统一为 [`sendResponse`](../../sensoube/utils/middleware.js)（`success` + `message` + 可选 `data`）。入参时间字段均为 **snake_case**；**必填**起止时间用 `timeRangeRequiredFields`（见 `utils/validate.js`），若某接口未来需起止选填，用 `timeRangeOptionalFields` 再拼业务 schema。

| 说明 | 方法 / 路径 |
|------|-------------|
| 概览卡片 | `POST .../overview` — body：`start_time`, `end_time`（必填） |
| 活跃用户数趋势 | `POST .../trend` — body：`start_time`, `end_time`, `time_unit`（可选 hour/day，默认 day） |
| 注册趋势 | `POST .../registrations` — 同上 + `time_unit` |
| 聊天条数趋势 | `POST .../chatMessages` — 同上 + `time_unit` |
| 充值订单趋势 | `POST .../orders` — 同上 + `time_unit` |
| 注销数趋势 | `POST .../unsubscriptions` — 同上 + `time_unit` |
| 慢接口日志聚合 | `POST .../apiPerformanceLogs` — body：`start_time`, `end_time`, `limit`（可选，默认 200，最大 500） |

- **慢接口日志** 成功 `200` 的 `data`：`items`（按方法+路径聚合慢请求统计）、`slow_by_day`（按日汇总）、`start_time` / `end_time`。  
- 时间非法 / 起止颠倒：`400`，`data.error` 为 `invalid_time_format` 或 `invalid_time_range`。  
- 服务错误：`500`，`success`: false（见全局 `errorHandler`）。

## 聊天消息（`sensoube` v3 app · messaged）

- **批量软删除消息并按会话刷新列表摘要** `POST /api/v3/app/messageD/softDeleteMessagedByIds`  
  - 鉴权：需 Bearer Token（与其它非开放 POST 一致）；本地可将 `SKIP_TOKEN_VALIDATION=true` 跳过校验。  
  - Body（JSON）：
    - `ids`（string[]，必填）：`messaged` 主键 `_id`（24 位十六进制），长度 1～500，**同一数组内不可重复**  
    - `message_list_id`（string，必填）：会话 ID，对应 `messagel` 文档 `_id`，须与 `messaged.messageLid` 一致；**仅允许操作单一会话**  
  - 行为：仅当 `_id` 属于该 `message_list_id` 时软删除（`is_deleted` → `1`）；随后对该会话按可见消息（`is_deleted` 为 `0` 或 `2`）取最新一条的 `message`，写回该 `messagel` 的 `last_message` 与 `updated`。  
  - 成功 `200`（[`sendResponse`](../../sensoube/utils/middleware.js)）：`{ "success": true, "message": "...", "data": { "matched_count": number, "modified_count": number, "updated_sessions": 1 } }`  
  - 业务失败 `400`（条数与会话不匹配等）：`sendResponse` 形状，`message` 如「消息不存在或不属于该会话」  
  - 参数校验失败 `400`：`{ "success": false, "error": "请求参数验证失败", "details": [...] }`

- **会话流式聊天（SSE，通义应用 completion）** `GET /api/v3/app/messageD/streamMessagedRoleChat`  
  - Query：`messagelist_id`（必填）、`message`（必填，非空字符串）、`message_type`（可选，默认 `1`）。  
  - 响应：`text/event-stream`；增量正文为 `data: {"content":"..."}`；结束为 `data: [DONE]`；业务错误可能通过 `event: error` 推送。  
  - 说明：原路径 `GET .../chat-stream` 已更名为 `streamMessagedRoleChat`，便于全库检索且避免与其它模块的「chat-stream」重名；客户端须改用新路径。

## 剧本管理（`sensoube` v3 web · `ScriptManagement.js`）

路由前缀：`/api/v3/web/ScriptManagement`（与 axios `baseURL` 组合时以项目实际挂载为准）。成功体多为 `{ code: 200, msg, data? }`。

| 说明 | 方法 / 路径 |
|------|-------------|
| 创建剧本 | `POST .../createScript` |
| 更新剧本 | `POST .../updateScript` |
| 剧本列表 | `POST .../getScriptList` |
| 剧本详情 | `POST .../getScriptDetail`（body：`script_id`） |

- **createScript / updateScript** 的 `local_info` 与女友 **`gf_information.local_info`** 一致：按 **语言 locale 分桶**，剧本管理端**固定维护简体中文 `zh_CN`**（无需再选语言）。结构示例：  
  `{ "zh_CN": { "gf_introduction": "…", "first_introduction": "…" } }`  
  创建时若省略 `local_info` 或省略 `zh_CN`，按空字符串写入上述两键；更新时仅当 body 的 `local_info.zh_CN`（或兼容旧版的顶层 `gf_introduction` / `first_introduction`）至少传入其一字段时合并写入；合并时保留其它 locale 键；兼容库内 `local_info` 曾为 JSON 字符串或曾将两字段平铺在顶层的历史数据。

## 业务接口（待补充）

_（按模块列出路径、方法、请求/响应要点、错误码）_
