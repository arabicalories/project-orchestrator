# Project Orchestrator Docs Index v0.1

本文档用途：给 `project-orchestrator` 私有预览仓库提供一个稳定的文档入口，帮助读者快速判断“我现在该看哪一份”。

## 先给结论

如果你是第一次打开这个仓库，默认按下面顺序阅读：

1. `README.md`
2. `docs/project-orchestrator-reviewer-quickstart-v0.1.md`
3. `docs/project-orchestrator-implementation-status-v0.1.md`
4. `docs/project-orchestrator-github-packaging-plan-v0.1.md`
5. `docs/project-orchestrator-update-workflow-sop-v0.1.md`
6. `docs/project-orchestrator-public-ready-gap-review-v0.1.md`

## 文档地图

### 1. Reviewer entry
- `docs/project-orchestrator-reviewer-quickstart-v0.1.md`
- 适合：第一次看仓库的协作者
- 作用：告诉你这是什么、不该先假设什么、最短阅读路径是什么

### 2. Current implementation truth
- `docs/project-orchestrator-implementation-status-v0.1.md`
- 适合：想知道当前已经做到哪里的人
- 作用：定义当前实现边界、组件分层、原型状态、真实链路进度

### 3. Packaging / repo-boundary plan
- `docs/project-orchestrator-github-packaging-plan-v0.1.md`
- 适合：想知道为什么仓库这样分层、为什么不直接公开 workspace 的人
- 作用：解释 core / runtime / example / local-private 的边界与收口方案

### 4. Update workflow
- `docs/project-orchestrator-update-workflow-sop-v0.1.md`
- 适合：准备继续更新 GitHub 仓库的人
- 作用：定义 `workspace -> staging -> GitHub` 的标准更新流程

### 5. Gap review / next-stage focus
- `docs/project-orchestrator-public-ready-gap-review-v0.1.md`
- 适合：想知道“离 future public template 还差什么”的人
- 作用：按 `P0 / P1 / P2` 给出当前差距与最小修复方向

### 6. Frozen baseline / deep design reference
- `docs/project-orchestrator-agent-prd-v1.0.1-freeze.md`
- 适合：需要回看早期冻结设计、规则定义和术语边界的人
- 作用：作为深层设计基线，不适合作为第一次阅读入口

## 按角色看文档

### 如果你是 reviewer
先看：
- `README.md`
- `docs/project-orchestrator-reviewer-quickstart-v0.1.md`
- `docs/project-orchestrator-public-ready-gap-review-v0.1.md`

### 如果你是后续维护者
先看：
- `docs/project-orchestrator-implementation-status-v0.1.md`
- `docs/project-orchestrator-update-workflow-sop-v0.1.md`
- `project-orchestrator/component-manifest.json`

### 如果你是要继续做 packaging 收口的人
先看：
- `docs/project-orchestrator-github-packaging-plan-v0.1.md`
- `docs/project-orchestrator-public-ready-gap-review-v0.1.md`
- `scripts/release_check.py`

## 当前建议

这份 docs index 的目标不是替代其他文档，而是：

- 提供稳定入口
- 减少文档数量增长后的迷路感
- 把“现状、更新、gap、基线”四类文档分开

一句话：

> 以后如果 README 只能挂一个文档入口，优先挂这份 docs index。
