# API 约定

## 版本与路径

- 现有路由包含 `/api`、`/api/v2`、`/api/v3` 等；新接口优先落在合适版本目录并与 Architect 约定一致。

## 契约维护

- 稳定契约摘要写在 [`.ai/context/api_docs.md`](../context/api_docs.md)。
- 若启用 Swagger，注释与实现保持一致。

## 响应习惯

- 错误结构尽量与现有接口一致；HTTP 状态码语义正确。
- Breaking change 需在 context 注明并提供迁移说明。
