# Project Orchestrator Implementation Status v0.1

基线文档：`docs/project-orchestrator-agent-prd-v1.0.1-freeze.md`

本文档用途：说明当前 `project-orchestrator` 的实现状态、真流程边界与实例化进度，并作为后续整理成 **GitHub 私有内测仓库** 的现状基线。本文档不是正式 plugin 发布说明。

---

## 1. 当前实现边界

已完成：
- phase 1：静态骨架
- phase 2：最小 task tools
- phase 3：agent 主循环
- phase 4：shared skills 接线与第二项目复用
- phase 5：executor adapter（fake + tmux runtime inspect）
- phase 6：用户决策与 review/fixback 最小闭环

未完成（按当前私有内测仓库收口语义）：
- cron 唤醒正式默认接线
- review card 正式默认接线
- sample / local-private 边界彻底收口
- GitHub 私有内测仓库目录边界整理
- plugin/tool 正式封装

---

## 2. 组件分层（当前）

### A. 规则与模板层
位于 `project-orchestrator/`

- `specs/`
  - 冻结规则表与 schema
- `shared-skills/project-orchestrator-dev/`
  - 共享 skill 骨架
  - `stage-actions.json` 作为共享阶段动作策略
- `workspace-template/`
  - 项目 agent 的 workspace 模板
- `state-template/`
  - 外部状态目录模板
- `samples/`
  - 正常流 / review-fixback 样例任务

### B. 正式原型层（当前最接近正式实现）
位于 `scripts/`

- `project_orchestrator_task_tools.py`
  - `task_init`
  - `task_get`
  - `task_check`
  - `task_transition`
  - `task_mark_need_user_decision`
  - `task_append_note`
  - 以及少量测试辅助写口

- `project_orchestrator_executor.py`
  - fake executor adapter
  - tmux runtime adapter（最小读/启动/同步接口）

### C. orchestrator runner 层
位于 `scripts/`

- `project_orchestrator_agent.py`
  - shell / dispatch 入口
  - 对已注册项目只做识别、委派、停点返回

- `project_orchestrator_instance_runner.py`
  - 项目 agent 统一推进器
  - 当前承载已注册项目的真流程推进

- `project_orchestrator_review.py`
  - review / fixback / 用户介入升级执行器

### D. 测试层
位于 `scripts/`

- `project_orchestrator_phase1_check.py`
- `test_project_orchestrator_phase2.py`
- `test_project_orchestrator_agent_shell.py`
- `test_project_orchestrator_instance_runner.py`
- `test_project_orchestrator_review.py`

---

## 3. 正式 vs demo 的当前判定

### 可视为“正式原型”的部分
这些已经承载冻结规则，不建议随意推翻：

1. `project-orchestrator/specs/*`
2. `project-orchestrator/shared-skills/project-orchestrator-dev/stage-actions.json`
3. `scripts/project_orchestrator_task_tools.py`
4. `scripts/project_orchestrator_executor.py`

### 当前仍属于原型/兼容层的部分
当前已删除 phase3/5/6 wrapper 与 compat 模块，不再保留原型/兼容 runner 并存结构。

当前统一入口关系为：
- `scripts/project_orchestrator_agent.py`：shell / dispatch
- `scripts/project_orchestrator_instance_runner.py`：项目 agent 真流程推进器

后续仍需补：
- cron 唤醒正式接线
- review card 正式接线
- 自动 PR 的默认基线收口与 sample 语义对齐

---

## 4. 当前命名建议

当前已完成 phase wrapper 收口，不再保留 phase3/5/6 runner 文件。

当前命名分工为：
- `project_orchestrator_task_tools.py`：状态真相源
- `project_orchestrator_executor.py`：执行器适配层
- `project_orchestrator_agent.py`：shell / dispatch
- `project_orchestrator_instance_runner.py`：项目 agent 统一推进器
- `project_orchestrator_review.py`：review 执行器

---

## 5. 进入 A（实例化项目 agent）前的最小前置条件

创建本地真实实例前，建议先满足：

1. 有统一入口（而不是 phase3/5/6 三个 runner 并存）
2. 明确目标项目的 project config：
   - `projectId`
   - `repoPath`
   - `projectSlug`
   - `workspace path`
   - 是否默认 require approval
3. 明确与现有 codex runtime 的最小接线边界：
   - 先只读 / inspect
   - 再启动
   - 最后再考虑 watchdog/card

---

## 6. tmux 会话隔离原则

当前项目编排方案中，tmux 执行层默认采用：

**一项目一 tmux session**，不共用全局单 session。

原因：
- 项目上下文隔离更清楚
- 不同项目的 Codex 会话不容易串台
- watchdog / 日志 / 恢复定位更简单
- 与 `projectSlug -> TMUX_SESSION` 的映射天然一致

示例：
- `sample-project -> codex_sample`（示例命名）

因此项目编排层与执行层的默认对应关系应为：
- 一项目一 project agent
- 一项目一 tmux session

## 7. A 阶段当前进度

当前已验证“本地真实实例 + 示例实例”双层结构，并补了实例级调用壳。

这里需要明确：
- 本地真实实例属于 local-private 范畴；
- 它当前承担真实项目承接与流程执行职责；
- 它不是未来 GitHub 私有内测仓库中的默认模板实例；
- GitHub 仓库中的示例职责应由 `pa-sample` 这类 sample instance 承担；
- 示例 registry 已独立为 `project-orchestrator/registry/projects.sample.json`，用于承载 sample instance 的最小条目。

本地真实实例当前状态：
- local-private registry 条目已存在
- local-private project config 已存在
- unified runner 已绑定
- instance runner 已存在：`scripts/project_orchestrator_instance_runner.py`

当前实例 runner 已支持：
- 实例级 inspect
- 显式推进当前任务一轮（`advance-task`）
- 读取已有 tmux runtime 元信息

但仍未按默认基线正式收口：
- cron
- review card
- 自动 PR 默认语义
- 自动启动真实 tmux executor

## 8. A 阶段新增进展（真实需求开发验证门槛）

在本地真实实例与实例 runner 绑定后，又完成了两层关键推进：

### 8.1 项目承接群配置
- 本地真实实例可补充独立项目消息目标；
- 真实配置仅保存在 local-private 配置与说明中，不进入仓库主干。

### 8.2 真实 tmux 回收闭环
- `project_orchestrator_executor.py` 已补充：
  - tmux pane capture
  - prompt 下发
  - pane snapshot 解析
  - 从 pane 中提取 `Ready for coordinator review: yes` / `codex resume <id>` / `Token usage`
- `project_orchestrator_instance_runner.py` 已补充：
  - `submit-real-task`
  - `collect-real-task`

### 8.3 已验证结果
- 对真实 tmux task 执行回收后，任务可从：
  - `codex_run -> collect -> review`
- 可回收到：
  - `codexRunRecord`
  - `codexSummary`
  - `testResult`
- 可提取执行元信息：
  - `resumeId`
  - token usage 行
  - pane snapshot tail

### 8.4 当前判断
这意味着系统状态已从：
- “真实执行链路已接通，但结果回收未闭环”

推进到：
- “已达到可实际进行项目真实需求开发验证的门槛”

补充边界说明：
- 当前实现层已经具备 PR 交付原型路径，但在 GitHub 私有内测仓库的默认基线中，**不把自动 PR 视为默认能力**；
- 自动 PR、watcher、review card 等能力应在 runtime 层按开关或运行环境决定，而不是作为 sample / 模板的默认承诺。

仍未按默认基线正式收口：
- cron
- review card
- sample / local-private 边界
- 自动启动真实 executor（仍保持默认关闭，只能显式放行）

## 9. 当前结论

当前系统已经具备“最小项目编排链路”的技术骨架，并且已达到真实需求开发验证门槛。

## 9.1 最新实现状态（2026-03-16）
- 已删除 old/compat 流程文件：
  - `scripts/project_orchestrator_compat.py`
  - `scripts/project_orchestrator_agent_phase3.py`
  - `scripts/project_orchestrator_agent_phase5.py`
  - `scripts/project_orchestrator_agent_phase6.py`
- 已同步删除旧 phase 测试：
  - `scripts/test_project_orchestrator_phase3.py`
  - `scripts/test_project_orchestrator_phase5.py`
  - `scripts/test_project_orchestrator_phase6.py`
- 当前仅保留的新主流程结构：
  - `scripts/project_orchestrator_agent.py`：shell / dispatch
  - `scripts/project_orchestrator_instance_runner.py`：项目 agent 真流程推进器
  - `scripts/project_orchestrator_review.py`：review / fixback / 用户介入升级执行器
  - `scripts/project_orchestrator_task_tools.py`：状态真相源
  - `scripts/project_orchestrator_executor.py`：tmux executor adapter
- 同时新增新的 shell 测试：
  - `scripts/test_project_orchestrator_agent_shell.py`
- 新流程测试集当前为：
  - `scripts/test_project_orchestrator_agent_shell.py`
  - `scripts/test_project_orchestrator_instance_runner.py`
  - `scripts/test_project_orchestrator_review.py`
- 最新新流程回归结果：
  - `python -m unittest scripts/test_project_orchestrator_agent_shell.py scripts/test_project_orchestrator_instance_runner.py scripts/test_project_orchestrator_review.py`
  - `Ran 21 tests ... OK`
- 非侵入 CLI 验证结果：
  - `python scripts/project_orchestrator_instance_runner.py inspect --agent-id pa-sample` 正常（示例）
  - `python scripts/project_orchestrator_instance_runner.py demo --agent-id pa-sample --mode tmux-flow` 在未放行时正确返回 `REAL_EXECUTOR_DISABLED`
- 当前结论更新为：
  - old compat / phase wrapper 已删除；
  - 当前只保留最新主流程；
  - `coordinator/shell` 负责分发，项目实例 runner 负责项目真流程推进。

## 10. 新增硬流程约束（2026-03-16）

### 10.1 只允许保留最新一个流程
- 这是**硬标准**，不是软约束。
- 理论上不应再存在 old 真流程。
- 允许保留的 old 仅限：
  - 文件名兼容
  - 命令兼容入口
  - wrapper / 转发壳
- 不允许保留的 old 包括：
  - 自己判断 stage
  - 自己决定 transition
  - 自己执行一套和最新流程并行的推进逻辑
  - 成为第二套真相源
- 最终目标是：
  - **唯一阶段推进真相源 = 最新统一流程 / 统一推进器**
  - old main loop 不再拥有独立推进权

### 10.2 coordinator 与项目 agent 的职责硬分层
- 新增硬约束：任务下发后，主流程应把任务**转交给项目 agent**，而不是继续由 coordinator 混合执行项目内部流程。
- 当前目标职责划分：
  - `coordinator`：
    - 接收用户任务
    - 识别目标项目
    - 创建/下发任务
    - 把流程执行权转交给对应项目 agent
    - 在需要用户介入时承担桥接与汇总
  - 项目实例 agent：
    - 独立执行从 `intake` 到 `done / await_user_decision` 的完整项目流程
    - 负责 review / fixback / 与 Codex 讨论收敛
    - 无法收敛时再升级给用户
- 因此目标状态不是“coordinator + 项目 agent 混合推进”，而是：
  - **coordinator = dispatch layer**
  - **project agent = 唯一项目流程执行者**

### 10.3 收口方向
- 后续收口不只是“代码层统一推进器”，还包括“职责层统一”：
  1. 删除 old 真流程；
  2. 保留兼容 wrapper 但剥离其推进权；
  3. 让统一推进器成为唯一阶段推进真相源；
  4. 让 coordinator 从项目细节执行者退回为分发/桥接角色；
  5. 让项目实例 agent 成为其所属项目的唯一全流程执行主体。

### 10.4 当前文件清单（按真权分类）

#### A. 真流程 / 真权文件
这些文件当前仍承载真实执行权：
- `scripts/project_orchestrator_task_tools.py`
  - 任务状态真相源；所有状态变更仍必须经过这里。
- `scripts/project_orchestrator_executor.py`
  - Codex/tmux 执行层真接口。
- `scripts/project_orchestrator_instance_runner.py`
  - 当前项目 agent 的统一推进器；已覆盖 `intake -> ... -> done/await_user_decision` 的项目流程推进。
- `scripts/project_orchestrator_review.py`
  - review 执行器；承载 review/fixback/用户介入升级的关键判断。
- `scripts/project_orchestrator_watcher.py`
  - 观测/wake 入口；虽不再拥有阶段推进权，但仍是运行时触发链的真入口之一。

#### B. shell / dispatch 文件
这些文件当前保留为主流程壳或分发层：
- `scripts/project_orchestrator_agent.py`
  - 当前职责是：
    - 识别已注册项目；
    - 对已注册项目把单步/整段循环都委派给项目 agent（`project_orchestrator_instance_runner.py`）；
    - 对 fake/compat 流量保留兼容壳。
  - 结论：它已不再是已注册项目的真执行者，而是 shell / dispatch 层。

#### C. old/compat 残留
- 当前已删除：
  - `scripts/project_orchestrator_compat.py`
  - `scripts/project_orchestrator_agent_phase3.py`
  - `scripts/project_orchestrator_agent_phase5.py`
  - `scripts/project_orchestrator_agent_phase6.py`
- 也已同步删除对应旧测试：
  - `scripts/test_project_orchestrator_phase3.py`
  - `scripts/test_project_orchestrator_phase5.py`
  - `scripts/test_project_orchestrator_phase6.py`

### 10.5 当前结论（A 阶段核查结果）
- **对已注册项目路径而言，old 真流程已经被删除，不再保留文件形态残留**。
- 当前唯一主流程结构为：
  - `project_orchestrator_agent.py`：shell / dispatch
  - `project_orchestrator_instance_runner.py`：项目 agent 真流程推进器
  - `project_orchestrator_review.py`：review / fixback / 用户介入升级执行器
- 因此 A 阶段核查结论更新为：
  - 已注册项目真权已收口到项目 agent；
  - old compat / wrapper 已删除；
  - 当前进入“只保留最新流程”的状态。
