# 项目概览

## 仓库布局（workspace 根）

| 目录 | 说明 |
|------|------|
| [`sensoube`](../../sensoube) | Node.js + Express + Mongoose 后端 API |
| [`senso_admin`](../../senso_admin) | Vue 3 + Vite 管理后台 |

## 后端要点

- 入口：`sensoube/app.js`；环境文件：`.env.development` / `.env.production`；测试可选用 `.env.test`。
- 测试：`NODE_ENV=test` 时不连接 Mongo、不启动定时任务与 listen，便于 `jest` + `supertest`。
- 探活：`GET /api/health` → `{ "status": "ok" }`。

## 前端要点

- `senso_admin` 使用 Vite；脚本见该目录 `package.json`。

## 待 Architect 维护

- Redis / 消息队列若未在依赖中出现，请勿在实现中虚构；需先决策再引入。
