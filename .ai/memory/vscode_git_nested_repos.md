# VS Code / Cursor：嵌套 Git 仓库相关设置备忘

在 **设置** 里可直接搜英文键名或 UI 文案，本仓库工作区示例见根目录 `.vscode/settings.json`。

## `git.autoRepositoryDetection`

控制打开文件夹时，是否**自动发现子目录里的 Git 仓库**（存在 `.git` 的文件夹），从而在「源代码管理」里出现**多个仓库根**。

- **`true`**：自动发现（常用；嵌套子仓会被扫到）。
- **`false`**：不自动扫嵌套仓，一般只当你明确只想用当前打开的这一层根仓库。
- **`subFolders`**：侧重从子文件夹发现仓库（具体行为以当前编辑器版本说明为准）。
- **`openEditors`**：与当前打开文件所在路径相关的仓库（减少无关扫描）。

需要多认几个嵌套仓时，用 **`true`** 或 **`subFolders`**；想安静、只认当前根用 **`false`**。设置 UI 可搜 **Auto Repository Detection**。

## `git.repositoryScanMaxDepth`

从工作区根向下，**最多扫几层目录**去找嵌套仓库；数值越大扫得越深，可能略增开销。本仓库工作区里常用 **`3`**，可按目录深度改大或改小。

## `git.detectSubmodules`

与 **Git 子模块** 的识别、展示有关；子模块多时保持 **`true`** 一般更省心。
