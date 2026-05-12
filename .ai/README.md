# `.ai/` — 人机协作手册（与本仓库同步演进）

- **agents/**：按角色新开会话或 Composer，先 **`@` 工作流或角色文件**再描述任务。
- **rules/**：人类可读长规范；机器精简版在根目录 `.cursor/rules/*.mdc`。
- **context/**：当前事实（API、库表、目录）；改代码时同步更新。
- **workflows/**：功能 / 缺陷 / 发布流程；Orchestrator（你）按步骤切换角色。
- **templates/**：PR、ADR、需求一页纸等可复用骨架。
- **memory/**：团队共识与术语（脱敏）。私密草稿放 `memory/local/`（已 gitignore）。编辑器嵌套 Git 备忘见 [memory/vscode_git_nested_repos.md](memory/vscode_git_nested_repos.md)。

## Subagents（Cursor）

- **探索**：可用只读 Subagent 并行扫目录惯例（路由、页面封装），加快上下文收集。
- **实现**：同一需求尽量保留 **一个写入型主会话**按顺序改代码；避免多个写入 Subagent 同时改同一批文件，减少冲突。
- 全栈复合路径的顺序见 [.ai/agents/fullstack_feature.md](agents/fullstack_feature.md) 与 [.cursor/rules/fullstack-feature.mdc](../.cursor/rules/fullstack-feature.mdc)。

详见仓库根目录 [`AGENTS.md`](../AGENTS.md)。
