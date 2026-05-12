# 工作流：功能开发（第一阶段）

## 输入

- 需求简述或 Issue；若有设计链接一并附上。

## 步骤（Orchestrator 按序切换会话 / `@` 角色文件）

1. **Architect**（`.ai/agents/architect.md`）  
   - 产出：`design/<feature>/architecture.md`（或等价路径）；必要时列出接口与数据变更要点。

2. **Backend**（`.ai/agents/backend.md`）  
   - 仅在 `sensoube/` 实现；更新 `.ai/context/api_docs.md`、`db_schema.md`（若有变更）。

3. **Frontend**（`.ai/agents/frontend.md`）  
   - 仅在 `senso_admin/` 实现。

4. **QA**（`.ai/agents/qa.md`）  
   - 补充/更新测试；在 `sensoube/` 执行 `npm test`。

5. **Reviewer**（`.ai/agents/reviewer.md`）  
   - 阻塞项必须先修复再回到对应步骤。

6. **DevOps**（仅在涉及部署/镜像/CI 时）  

## Definition of Done

- [ ] 契约文档已与代码一致（`.ai/context`）
- [ ] `npm test` 通过（后端有改动时）
- [ ] Reviewer 无阻塞项

## 变体：全栈小需求（单会话复合）

若需求影响面局部、不必单独设计闸门，可用复合角色 **在同一会话内** 先后实现后端与前端（仍需更新 `.ai/context` 并跑测）：

- Agent：[`.ai/agents/fullstack_feature.md`](../agents/fullstack_feature.md)
- 可选 Cursor 规则（按需 `@`）：[`.cursor/rules/fullstack-feature.mdc`](../../.cursor/rules/fullstack-feature.mdc)

严格分会话审计时仍用上文步骤与单角色 Backend / Frontend。
