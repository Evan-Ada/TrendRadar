# 数据库摘要（MongoDB / Mongoose）

> 随模型变更更新本文；完整定义以 `sensoube/models/` 为准。

## 约定

- 集合与模型文件对应关系、重要索引、字段含义在此记录。
- 新增索引或字段时补充条目，便于前后端与 Agent 对齐。

## `api_performance_log`（Mongoose：`sensoube/models/api_performance_log.js`）

- 用途：慢请求（如耗时 ≥500ms）落库，供报表聚合。  
- 主要字段：`method`, `url`, `path`（不含 query，便于按路径聚合）, `duration_ms`, `created_at` 等。  
- 索引：`created_at`、`path`、`duration_ms`（见模型内 `index` 定义）。

## `gf_information`（Mongoose：`sensoube/models/gf_information.js`）

- 集合：女友与剧本（`roleType`：`0` 女友，`1` 剧本）等共用模型。  
- **`local_info`**：`Mixed` 类型；历史上可能为字符串。与女友相同：**按 locale 分桶**（如 `zh_CN`）。女友在 `zh_CN` 下挂多类字段；**剧本**由 `ScriptManagement` 固定写入 **`zh_CN.gf_introduction`**、**`zh_CN.first_introduction`**（管理端不选语言，默认中文桶）。

## 核心集合（待补充）

_（在此添加集合名、用途、主键/索引、关联关系）_
