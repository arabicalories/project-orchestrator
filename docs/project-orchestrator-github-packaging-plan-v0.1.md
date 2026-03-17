# Project Orchestrator GitHub Packaging Plan v0.1

基线文档：`docs/project-orchestrator-implementation-status-v0.1.md`  
关联原型目录：`project-orchestrator/`、`scripts/project_orchestrator_*.py`

本文档用途：为 `project-orchestrator` 后续整理成 **GitHub 私有内测仓库** 提供一份可执行的收口方案，并为未来正式 plugin 发布预留演进路径。

**重要约束**：本文档当前只定义收口方案，**不要求立刻实施**，也**不应影响当前 local-private 真实实例的使用与运行链路**。

---

## 1. 背景与目标

当前 `project-orchestrator` 已具备最小项目编排原型能力，也已经进入真实需求开发验证门槛。

但当前代码组织方式仍偏内部工作区原型，存在以下问题：
- 真实实例与模板边界尚未彻底分开；
- 多处存在真实环境路径、真实账号/群标识、真实运行约定；
- 文档与代码行为存在收口差异；
- 当前工作区混有记忆、监控、消息恢复、其他技能与临时目录，不适合直接作为 GitHub 仓库边界。

因此，本阶段目标不是“正式公开发布”，而是先把相关内容收口成一个：

1. **可持续迭代**的私有内测仓库；
2. **后续修改和更新低摩擦**的目录结构；
3. **不影响当前 local-private 真实实例使用**的规划方案；
4. **未来可平滑演进到正式 plugin 发布**的中间状态。

---

## 2. 本阶段成功标准

本阶段完成的判定标准为：

1. 产出一份文件级归属清晰的收口方案文档；
2. 明确 GitHub 私有内测仓库的最小保留清单；
3. 明确 local-private 真实实例与 `pa-sample`（示例实例）的拆分原则；
4. 明确最小配置契约 v0；
5. 明确迁移顺序与非目标；
6. 在方案阶段 **不改动当前 local-private 真实实例运行链路**。

---

## 3. 当前现状与约束

### 3.1 当前已具备的能力

当前已具备：
- 冻结规则表与 schema；
- shared skill 骨架；
- task 真相源与状态流转；
- fake / tmux executor 适配；
- shell / dispatch 主入口；
- 项目 agent 实例 runner；
- review / fixback / await_user_decision 最小闭环；
- local-private 真实实例的最小实例化与真实需求开发验证门槛。

### 3.2 当前不适合直接上传 GitHub 的原因

当前不建议直接把整个 workspace 上传 GitHub，原因包括：
- 混有与本项目无关的 memory、监控、消息恢复、skills、tmp 目录；
- local-private 实例目录中含真实实例信息；
- 多处脚本内存在本机绝对路径与 OpenClaw 环境假设；
- 文档中仍存在与最新实现状态不完全一致的描述。

### 3.3 当前硬约束

后续任何收口动作都必须遵守：
- **不影响当前 local-private 真实实例继续运行与使用**；
- **不先动现有真实实例配置**；
- **先文档化，再结构调整**；
- **先私有内测仓库，再考虑正式 plugin 化**。

---

## 4. 分层设计（目标状态）

为降低后续修改和更新阻力，未来 GitHub 私有内测仓库建议按三层组织：

### A. Core 层
放置通用编排能力与冻结规则，不应依赖真实实例或本机私有环境。

职责：
- 任务状态模型与规则；
- shared policy / shared skill；
- 通用 review/fixback 语义；
- 样例、模板、schema。

**禁止出现**：
- 真实 `open_id` / `chat_id`；
- 真实 repo 路径；
- 真实 env 文件路径；
- 项目私有命名（如某个真实项目的特定路径与群）。

### B. Runtime Adapter 层
放置与 OpenClaw / tmux / GitHub / Feishu 相关的运行适配逻辑。

职责：
- executor adapter；
- instance runner 的运行时适配；
- watcher / 消息唤醒等与当前环境强相关的代码；
- GitHub PR 交付、tmux 交互、环境变量读取。

说明：
- 本层允许保留较强的 OpenClaw 内部环境假设；
- 但必须承认自己是 runtime adapter，而不是伪装成通用 core。

### C. Example Instance 层
放置示例项目实例，用于演示如何基于 core + runtime 组织一个项目 agent。

职责：
- 示例 project config；
- 示例 README；
- 示例本地覆盖；
- 示例 instance notes。

说明：
- GitHub 内测仓库应优先保留 `pa-sample`；
- 本地真实实例应留在本地环境，不承担模板说明职责。

---

## 5. 文件归属表（v0）

下表给出当前相关文件的建议归属。该表是未来迁移时的真相源之一。

| 路径 | 当前状态 | 目标归属 | 备注 |
|---|---|---|---|
| `project-orchestrator/specs/` | 已在用 | core | 保留 |
| `project-orchestrator/shared-skills/project-orchestrator-dev/` | 已在用 | core | 保留 |
| `project-orchestrator/workspace-template/` | 已在用 | core | 保留 |
| `project-orchestrator/state-template/` | 已在用 | core | 保留 |
| `project-orchestrator/samples/` | 已在用 | core | 保留 |
| `project-orchestrator/component-manifest.json` | 已在用 | core | 保留，可继续作为组件清单 |
| `project-orchestrator/README.md` | 已在用 | core | 需按内测仓库定位重写边界说明 |
| `project-orchestrator/registry/projects.json` | 当前含真实实例 | local-private | 当前继续服务本地真实实例，不建议直接进 GitHub |
| `project-orchestrator/registry/projects.sample.json` | 示例 registry | example | GitHub 侧默认保留的 sample registry |
| `project-orchestrator/projects/<local-private-instance>/project.json` | 真实实例配置 | local-private | 不建议直接进 GitHub |
| `project-orchestrator/projects/<local-private-instance>/README.md` | 真实实例说明 | local-private | 不建议直接进 GitHub |
| `project-orchestrator/projects/<local-private-instance>/AGENTS.md` | 真实实例说明 | local-private | 不建议直接进 GitHub |
| `project-orchestrator/projects/<local-private-instance>/MEMORY.md` | 真实实例记忆 | local-private | 不建议直接进 GitHub |
| `project-orchestrator/projects/<local-private-instance>/docs/instance-notes.md` | 真实实例说明 | local-private | 不建议直接进 GitHub |
| `project-orchestrator/projects/<local-private-instance>/skills/project-overrides.json` | 真实实例本地覆盖 | local-private | 不建议直接进 GitHub |
| `scripts/project_orchestrator_task_tools.py` | 已在用 | core 或 runtime 边界件 | 当前偏通用，可优先保留；后续可视需要下沉到 core 子目录 |
| `scripts/project_orchestrator_review.py` | 已在用 | core 或 runtime 边界件 | review 语义偏通用，执行环境偏 runtime |
| `scripts/project_orchestrator_executor.py` | 已在用 | runtime | 明确是适配层 |
| `scripts/project_orchestrator_agent.py` | 已在用 | runtime | shell / dispatch 入口 |
| `scripts/project_orchestrator_instance_runner.py` | 已在用 | runtime | 项目 agent 统一推进器 |
| `scripts/project_orchestrator_watcher.py` | 已在用 | runtime | 与当前环境强相关 |
| `scripts/project_orchestrator_phase1_check.py` | 已在用 | test/tooling | 可保留 |
| `scripts/test_project_orchestrator_*.py` | 已在用 | test | 保留 |
| `docs/project-orchestrator-implementation-status-v0.1.md` | 已在用 | docs | 保留 |
| `docs/project-orchestrator-agent-prd-v1.0.1-freeze.md` | 已在用 | docs | 保留 |
| `runtime/project_orchestrator_state/` | 运行态 | local-private | 不进入 GitHub 主干 |

### 5.1 当前文件归属硬规则

在正式迁移前，先约定以下硬规则：

1. `core` 层文件不得再引入真实项目私有标识；
2. `local-private` 文件不得作为 GitHub 模板说明来源；
3. `runtime` 层允许使用 OpenClaw / tmux / GH / Feishu 运行假设，但需要在文档中明示；
4. 未来做目录调整时，应优先移动 example 与 local-private 边界，避免先动 local-private 真实实例链路。
5. `registry/projects.json` 在未来必须分流为两类：
   - GitHub 仓库内只保留 **sample registry**；
   - 本地真实环境保留 **local-private registry**；
   - 真实 registry 不得作为 GitHub 仓库默认内容。
6. `project.json` 类配置文件未来也必须分流为两类：
   - example 配置：只允许占位值与示例值；
   - local-private 配置：允许真实路径、真实 ID、真实运行目标；
   - 禁止把真实实例配置直接复制到 GitHub 仓库作为示例。

---

## 6. GitHub 私有内测仓库最小保留清单（v0）

### 6.1 建议保留

建议未来 GitHub 私有内测仓库至少保留：

- `project-orchestrator/specs/`
- `project-orchestrator/shared-skills/project-orchestrator-dev/`
- `project-orchestrator/workspace-template/`
- `project-orchestrator/state-template/`
- `project-orchestrator/samples/`
- `project-orchestrator/component-manifest.json`
- `project-orchestrator/README.md`
- `project-orchestrator/registry/projects.sample.json`
- `scripts/project_orchestrator_task_tools.py`
- `scripts/project_orchestrator_executor.py`
- `scripts/project_orchestrator_agent.py`
- `scripts/project_orchestrator_instance_runner.py`
- `scripts/project_orchestrator_review.py`
- `scripts/project_orchestrator_watcher.py`
- `scripts/project_orchestrator_phase1_check.py`
- `scripts/test_project_orchestrator_*.py`
- `docs/project-orchestrator-agent-prd-v1.0.1-freeze.md`
- `docs/project-orchestrator-implementation-status-v0.1.md`
- 本文档

### 6.2 建议排除

建议不进入未来 GitHub 私有内测仓库主干：

- 真实实例目录：
  - `project-orchestrator/projects/<local-private-instance>/**`
- 真实 registry / 运行态目录：
  - `project-orchestrator/registry/projects.json`
  - `runtime/project_orchestrator_state/**`
  - `runtime/review_cards/**`
  - `runtime/project_orchestrator/**`
- 当前 workspace 其他无关目录：
  - `memory/**`
  - `msg-recover/**`
  - `progress-notify/**`
  - `reports/**`
  - `tmp/**`
  - 其他无关 skills / monitor / 临时项目目录
- 缓存与临时产物：
  - `**/__pycache__/**`
  - `**/.pytest_cache/**`
  - `**/.mypy_cache/**`
  - `*.pyc`
  - `*.log`
  - `*.jsonl`
- 任何真实环境 `.env`、日志、运行态文件、临时目录

### 6.3 必须脱敏的内容

即便进入 GitHub 私有内测仓库，也应默认脱敏：

- `open_id`
- `chat_id`
- 真实 repo 路径
- 真实 env 文件路径
- 真实 tmux session 名（若具有环境耦合或暴露价值）
- 真实项目群 / 默认回复目标
- 任何未来可能转公开后不宜暴露的环境标识

---

## 7. 真实实例与示例实例拆分策略

### 7.1 原则

未来不建议把 local-private 真实实例直接作为 GitHub 模板实例。

建议采用：
- 本地保留：local-private 真实实例
- GitHub 保留：`pa-sample`（示例实例）

### 7.2 各自职责

#### local-private 真实实例
职责：
- 真实项目承接；
- 持有真实运行配置；
- 继续服务当前真实项目；
- 不承担模板展示职责。

#### `pa-sample`
职责：
- 作为示例 instance 演示如何接入 project-orchestrator；
- 使用占位配置与示例文档；
- 不携带真实项目标识；
- 作为 GitHub 内测仓库默认 example instance。

### 7.3 避免双份维护的规则

为避免 local-private 真实实例与 `pa-sample` 双份维护，约定：

1. 通用能力只在 `core/runtime` 层演进；
2. `pa-sample` 只保留最小示例配置，不承载真实业务特化；
3. local-private 真实实例不再承担文档样例职责；
4. 当通用配置字段变更时，只同步 example schema / sample config，不要求在 GitHub 中复制真实实例说明。

---

## 8. 最小配置契约 v0

本阶段不追求完整配置系统，只定义当前高频、最容易造成环境耦合的字段。

### 8.1 建议字段

| 字段 | 用途 | 备注 |
|---|---|---|
| `projectId` | 项目标识 | 必填 |
| `agentId` | 项目 agent 标识 | 必填 |
| `projectSlug` | 与 runtime / repo / tmux 对应的项目短名 | 必填 |
| `repoId` | repo 抽象标识 | 必填 |
| `repoPath` | 本地 repo 路径 | runtime 或 local-private 覆盖 |
| `workspacePath` | 项目 workspace 路径 | 必填 |
| `tmuxSession` | 默认 tmux session 名 | runtime 或 local-private 覆盖 |
| `tmuxIsolationMode` | tmux 隔离策略 | 如 `per-task-session` |
| `codexEnvFile` | runtime env 文件路径 | local-private 覆盖 |
| `messageChannel` | 消息通道 | 如 `feishu` |
| `messageTarget` | 默认项目消息目标 | sample 中用占位符 |
| `defaultReplyTarget` | 默认回复目标 | sample 中用占位符 |
| `allowAutoStartExecutor` | 是否允许自动启动真实 executor | 默认建议 false |
| `allowCron` | 是否允许 cron | 默认建议 false |
| `allowReviewCard` | 是否允许 review card | 默认建议 false |
| `allowAutoPR` | 是否允许自动 PR | 默认建议 false，或必须文档与行为一致 |

### 8.2 配置语义规则

约定：
- 示例实例中只使用占位值；
- 真实路径、真实 ID、真实群配置只存在于 local-private 配置；
- 若代码行为已支持自动 PR / review card / cron，则文档必须反映真实开关语义；
- 配置入口应集中，不继续在脚本中分散新增新的私有环境读口。

### 8.2.1 `pa-sample/project.json` 最小占位格式（当前基线）

当前 `pa-sample/project.json` 作为 GitHub 私有内测仓库中的默认示例配置，最小占位格式基线如下：

| 字段 | 示例值 | 说明 |
|---|---|---|
| `projectId` | `sample-project` | 示例项目 ID |
| `agentId` | `pa-sample` | 示例项目 agent ID |
| `workspaceLabel` | `project-sample` | 示例 workspace label |
| `workspacePath` | `project-orchestrator/projects/pa-sample` | 示例实例目录 |
| `runner` | `scripts/project_orchestrator_agent.py` | 当前统一 shell / dispatch 入口 |
| `runnerMode` | `prototype` | 当前原型模式 |
| `projectSlug` | `sample` | 示例项目短名 |
| `repoPath` | `/path/to/sample-repo` | 占位 repo 路径，真实环境必须覆盖 |
| `repoId` | `repo-sample` | 占位 repo 抽象 ID |
| `tmuxSession` | `codex_sample` | 占位 tmux session |
| `tmuxIsolationMode` | `per-task-session` | 默认示例隔离策略 |
| `codexEnvFile` | `/path/to/sample.env` | 占位 env 文件路径 |
| `messageChannel` | `feishu` | 示例消息通道 |
| `messageTarget` | `chat:oc_sample` | 占位项目消息目标 |
| `projectChatId` | `oc_sample` | 占位项目群 ID |
| `defaultReplyTarget` | `user:ou_sample` | 占位默认回复目标 |
| `defaultReplyOpenId` | `ou_sample` | 占位默认回复 open_id |
| `allowAutoStartExecutor` | `false` | 默认关闭 |
| `allowCron` | `false` | 默认关闭 |
| `allowReviewCard` | `false` | 默认关闭 |
| `allowAutoPR` | `false` | 默认关闭，显式开启 |

补充规则：
- 以上值中，凡是路径、ID、目标、session 名，默认都视为**占位值**；
- `pa-sample/project.json` 不得演化成真实实例配置；
- 若 sample 配置字段发生变更，应优先同步本文档与 `pa-sample/project.json`，而不是从 local-private 真实实例倒推。 

### 8.3 配置来源优先级

为避免配置收口后再次退化为“脚本各自偷读环境变量”，未来执行时统一采用以下优先级：

1. **sample default config**
   - GitHub 仓库中的默认示例配置；
   - 只承载通用默认值与占位值；
   - 不包含真实环境信息。
2. **local-private override**
   - 本地真实环境的覆盖配置；
   - 用于注入真实 repoPath、真实 tmuxSession、真实 message target、真实 env 文件路径等；
   - 是真实实例运行的主要配置来源。
3. **runtime ephemeral override**
   - 仅用于单次运行、调试或显式放行；
   - 优先级最高，但不应回写到 sample default。

补充约束：
- 不允许新增“只在脚本内部直接读某个私有环境变量，且未在配置契约中声明”的新入口；
- 若确有必要读取 runtime env，也应在配置契约或 runtime adapter 文档中显式登记；
- `pa-sample` 只消费 sample default；local-private 真实实例消费 local-private override。

---

## 9. 迁移顺序（建议）

本计划只定义顺序，不要求本轮立刻执行。

### Phase A：文档冻结
先完成：
1. 本文档；
2. 更新 `project-orchestrator/README.md` 的内测边界说明；
3. 对齐实现状态文档与真实行为边界。

最小验收标准：
- 本文档完成并经 review 确认；
- `project-orchestrator/README.md` 明确写出“当前为私有内测原型，不是正式 plugin 发布物”；
- 文档中不再出现与当前代码行为冲突的边界描述（尤其是 auto PR / review card / cron）。

### Phase B：示例实例抽离
再做：
1. 新增 `pa-sample`；
2. 将 GitHub 仓库中的示例说明切换到 `pa-sample`；
3. 保留 local-private 真实实例在本地，不动现有真实实例。

最小验收标准：
- GitHub 仓库中存在可读的 `pa-sample` 示例实例；
- `pa-sample` 中不含真实 open_id / chat_id / repoPath / env 文件路径；
- local-private 真实实例仍保留在本地并可继续服务当前项目；
- 仓库默认示例说明已切换为 `pa-sample`。

### Phase C：配置收口
再做：
1. 把高频环境字段收口到统一配置契约；
2. 清理分散在脚本中的新增环境读口；
3. 明确 sample config 与 local-private config 的边界。

最小验收标准：
- 配置来源优先级（sample default / local-private / runtime ephemeral）已在实现与文档中一致；
- 新增环境字段必须先进入配置契约或 runtime adapter 说明；
- 核心脚本不再继续增加未登记的私有环境读口；
- `pa-sample` 与 local-private 真实实例使用的配置来源边界清楚。

### Phase D：仓库边界整理
再做：
1. 确定 GitHub 私有内测仓库目录；
2. 只迁移最小保留清单；
3. 根据第 6.2 节迁移排除规则增加 `.gitignore` 与本地态排除规则；
4. 再考虑更完整的打包/安装体验。

最小验收标准：
- GitHub 仓库只包含最小保留清单内的目录与文件；
- local-private、runtime state、真实实例目录均未进入仓库主干；
- `.gitignore` 已覆盖运行态、日志、缓存、临时目录；
- 仓库在不依赖 local-private 真配置的前提下，仍可被理解和继续迭代。

---

## 10. 本阶段明确不做

为避免范围膨胀，本阶段明确不做：

- 不修改当前 local-private 真实实例的运行链路；
- 不立即把当前 workspace 整体迁移到 GitHub；
- 不立即抽离正式 plugin 安装包；
- 不立即追求公开发布质量；
- 不立即重写所有 runtime 代码；
- 不要求一步完成通用化。

---

## 11. 执行前待确认清单（v0.2 基线）

以下条目已按当前讨论形成**默认结论**。若后续没有新的强理由推翻，执行阶段应直接以这些结论为准，避免再次回到结构空转。

### 11.1 已确认的默认结论

1. `allowAutoPR`：**默认 false，显式开启**
   - 理由：当前优先级是低摩擦迭代，不是最大自动化；
   - 该默认值也最容易与示例实例、私有内测仓库边界保持一致。

2. watcher：**保留代码，但不作为默认上手路径**
   - 私有内测仓库第一版保留 watcher 相关代码与测试；
   - 但文档默认路径不以 watcher 作为最小上手链路；
   - watcher 作为可选 runtime 能力存在，而不是 sample 的必经能力。

3. `pa-sample`：**只做最小示例实例，不要求真实跑通完整任务**
   - 第一版只要求：
     - sample `project.json`
     - sample `README.md`
     - sample `instance-notes.md`
     - sample `skills/project-overrides.json`
   - 目标是让人看懂如何接入，而不是逼迫当前 runtime 立即完全通用化。

4. sample registry：**保留一个最小示例条目**
   - GitHub 仓库中保留 `sample registry`；
   - 默认只包含一个示例实例条目（如 `pa-sample`）；
   - 不包含真实 repoPath、真实 chat/open_id、真实 env 路径、真实群目标。

5. 配置系统：**先定最小配置契约，不急着重构成完整配置框架**
   - 第一阶段目标是配置语义清晰、来源边界清晰；
   - 不要求现在就把实现重构成完整独立配置系统；
   - 先避免继续新增分散读口，再逐步收口实现。

### 11.2 仍可后续再确认的问题

1. `task_tools / review` 最终归到 core 还是 runtime 边界层？
   - 当前阶段不阻碍文档冻结与示例实例抽离；
   - 可在后续目录重构时再决定最终落位。

---

## 12. 当前结论

当前最合理的路径不是立即“发布”，而是：

1. 先把相关内容规划成一个 **低摩擦、可持续迭代** 的私有内测仓库；
2. 用 `pa-sample` 承接模板/示例职责；
3. 把 local-private 真实实例留在本地，继续服务真实项目；
4. 先解决边界、脱敏、配置、文档一致性，再逐步演进到正式 plugin 发布。

这条路径的核心收益不是“更好看”，而是：
**后续继续修改、继续更新、继续演进时阻力最小，且不干扰当前真实使用。**

### 12.1 v0.2 执行基线（当前默认采纳）

除非后续出现新的强反例，否则当前执行阶段默认采纳以下基线：

- `allowAutoPR=false`，显式开启；
- watcher 保留，但不作为默认上手路径；
- `pa-sample` 只做最小示例实例，不要求完整真实跑通；
- GitHub 仓库保留最小 `sample registry`；
- 先落实最小配置契约，不急于做完整配置框架；
- 当前一切收口动作都不得影响现有 local-private 真实实例使用。

### 12.2 第一批实际整理任务清单（v0）

当前建议先执行一批**低风险、低耦合、不影响现有 local-private 真实实例运行链路**的整理动作，为后续私有内测仓库收口铺路。

#### T1. 对齐核心 README / 状态文档边界
目标：
- 对齐 `project-orchestrator/README.md` 与 `docs/project-orchestrator-implementation-status-v0.1.md`；
- 明确当前目标是 GitHub 私有内测仓库收口，而不是正式 plugin 发布；
- 明确 local-private 真实实例不是模板实例。

完成标准：
- 文档不再误导后续整理动作；
- 文档边界与当前代码行为不冲突。

#### T2. 新建 `pa-sample` 最小示例骨架
目标：
- 正式分离“真实实例”和“示例实例”；
- 新建 `project-orchestrator/projects/pa-sample/` 最小目录骨架。

最小文件建议：
- `project-orchestrator/projects/pa-sample/project.json`
- `project-orchestrator/projects/pa-sample/README.md`
- `project-orchestrator/projects/pa-sample/docs/instance-notes.md`
- `project-orchestrator/projects/pa-sample/skills/project-overrides.json`

完成标准：
- `pa-sample` 可读、边界清晰；
- 不含真实环境值；
- 不要求真实跑通完整任务。

#### T3. 拆出最小 sample registry
目标：
- 让 GitHub 仓库使用示例 registry，而不是继续依附真实 registry。

建议做法：
- 新增示例 registry 文件（如 `project-orchestrator/registry/projects.sample.json`）；
- 仅包含 `pa-sample` 示例条目；
- 不修改现有真实 `projects.json`。

完成标准：
- sample registry 独立存在；
- 不影响现有本地真实 registry。

#### T4. 明确 GitHub 排除清单
目标：
- 在真正迁移仓库前，先明确哪些内容永远不应进入 GitHub 主干。

当前结果：
- 第 6.2 节已经补成“迁移排除规则”风格；
- 已覆盖真实实例目录、真实 registry、runtime 状态、review cards、memory/msg-recover/reports/tmp、缓存与临时产物。

完成标准：
- 文档内存在清晰排除清单；
- 后续可直接转化为 `.gitignore` / 迁移排除规则；
- 后续实际迁移时不需要再临时补想“哪些目录不该带走”。

#### T5. 定义 sample config 最小占位格式
目标：
- 约束 `pa-sample/project.json` 的字段和占位风格，避免 sample 配置随意演化。

当前结果：
- 已完成一版 `pa-sample/project.json`；
- 已在第 8.2.1 节把 sample config 最小占位格式写成当前基线。

完成标准：
- 看到 sample config 即能区分占位值与真实值位；
- 不再需要从真实实例配置反推 sample；
- 后续 sample 配置变更有明确的文档同步锚点。

#### 建议执行顺序
1. T1：文档对齐
2. T2：新建 `pa-sample` 骨架
3. T3：新建 sample registry
4. T5：定义 sample config 占位格式
5. T4：固化 GitHub 排除清单

说明：
- 先 A（文档补齐）再 B（执行 T1）是当前最稳路径；
- 这批任务的目标不是立即迁移仓库，而是为未来迁移拆雷、减阻。
