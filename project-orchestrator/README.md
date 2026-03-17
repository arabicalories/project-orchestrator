# Project Orchestrator Agent Prototype

这是一套按 `docs/project-orchestrator-agent-prd-v1.0.1-freeze.md` 落地的**项目编排原型**。

当前这套内容的近期目标不是“正式 plugin 发布”，而是先收口成一个**可持续迭代的 GitHub 私有内测仓库**：边界清晰、可继续修改、且不影响当前真实实例使用。

当前已完成 phase 1 ~ phase 6 的最小实现，并已进入“先收口 GitHub 私有内测仓库边界，再逐步演进到正式 plugin 形态”的阶段。

当前覆盖：
- 项目 workspace 模板
- shared skill 骨架
- task 状态 schema / 规则表
- 最小状态目录模板
- 两个静态样例任务
- phase 1 自检脚本
- phase 2 最小 task tools（`task_init / task_get / task_check / task_transition`）
- executor adapter（tmux runtime adapter）
- 项目 agent 统一推进器
- review / fixback / 用户介入闭环
- shell / dispatch 主入口

## 目录

- `workspace-template/`：项目 workspace agent 的静态目录骨架
- `shared-skills/project-orchestrator-dev/SKILL.md`：共享流程 skill 骨架
- `specs/`：冻结规则表、schema、样例索引
- `state-template/`：外部状态真相源目录模板
- `samples/`：正常流 / review 打回流样例任务
- `../scripts/project_orchestrator_phase1_check.py`：阶段 1 自检脚本
- `../scripts/project_orchestrator_task_tools.py`：阶段 2 最小 task tools
- `../scripts/test_project_orchestrator_phase2.py`：阶段 2 单测
- `../scripts/project_orchestrator_agent.py`：shell / dispatch 主入口
- `../scripts/project_orchestrator_instance_runner.py`：项目 agent 统一推进器
- `../scripts/project_orchestrator_review.py`：review 执行器
- `../scripts/project_orchestrator_executor.py`：tmux executor adapter
- `../scripts/test_project_orchestrator_agent_shell.py`：shell / delegation 单测
- `../scripts/test_project_orchestrator_instance_runner.py`：项目 agent 主流程单测
- `../scripts/test_project_orchestrator_review.py`：review / fixback 单测
- `shared-skills/project-orchestrator-dev/SKILL.md`：共享流程 skill 骨架

## 当前边界

当前仓库定位是：
- **项目编排原型 / 私有内测仓库收口对象**；
- 不是正式 plugin 发布物；
- 当前优先级是降低后续修改与更新阻力，而不是补齐完整发布包装。

当前实现上：
- cron 唤醒、review card 仍未作为正式默认接线收口；
- PR 交付路径在实现层已具备原型能力，但当前文档与 sample 基线**不把自动 PR 视为默认能力**；
- watcher 保留为可选 runtime 能力，不作为默认上手路径。

说明：
- 当前 GitHub 仓库默认只保留 `pa-sample` 这类示例实例；
- 本地真实项目实例属于 local-private 范畴，不应进入仓库主干，也不承担模板职责；
- 示例实例的最小占位配置格式以 `project-orchestrator/projects/pa-sample/project.json` 与 `docs/project-orchestrator-github-packaging-plan-v0.1.md` 为准；
- 后续迁移到 GitHub 私有内测仓库时，排除范围以收口方案文档中的迁移排除规则为准，不直接从当前 workspace 全量搬运；
- `scripts/project_orchestrator_agent.py` 当前定位是 shell / dispatch 入口；已注册项目的真流程推进已委派到项目 agent；
- 当前不再保留 phase3/phase5/phase6 wrapper 与 compat 模块；只保留最新主流程；
- 当前组件分层与正式/演示边界见：
  - `docs/project-orchestrator-implementation-status-v0.1.md`
  - `docs/project-orchestrator-github-packaging-plan-v0.1.md`
  - `project-orchestrator/component-manifest.json`

## 自测

```bash
python scripts/project_orchestrator_phase1_check.py
```

通过标准：
- 目录骨架完整
- 规则表可读
- 样例任务字段齐全
- 样例流转满足冻结的 allowed transitions
- 样例阶段所需工件满足/缺失预期一致
