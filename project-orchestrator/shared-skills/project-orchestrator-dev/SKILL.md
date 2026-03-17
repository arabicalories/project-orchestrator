# project-orchestrator-dev

用于单项目开发任务的共享编排 skill。

## 适用范围
- 项目级开发任务
- 需要按固定状态机推进的任务
- 需要把代码执行与编排分离的任务

## 当前阶段
这是 `v1.0.1-freeze` 的 **phase 1 静态骨架**，职责仅为：
- 引用冻结规则表
- 说明每个阶段允许的动作
- 说明未来必须通过 `task_* tools` 推进

当前**不提供**真实工具写口，也不直接驱动 repo 改动。

## 唤醒后固定顺序
1. 读取任务状态
2. 识别当前 `stage`
3. 读取该阶段所需工件
4. 只从合法动作集合中选择动作
5. 若需推进阶段，未来必须走 `task_transition`

## 阶段动作骨架
- `intake`：补齐任务信息
- `plan`：生成计划、风险、影响范围
- `await_user_approval`：等待执行前审批
- `codex_run`：等待或观察执行层
- `collect`：收集 `codexRunRecord / codexSummary / testResult`
- `review`：执行 review，产出 review artifact 与后续决策
- `await_user_decision`：等待结果后决策
- `fixback`：review 未通过，把 review 结论返给执行层并要求 Codex 继续修改
- `pr_ready`：已满足可交付条件，但尚未完成交付闭环
- `done / blocked / failed`：终止或暂停态

## review 语义（新增，长期复用）
- 进入 `review` 不等于 review 已完成；`review` 是一个**必须执行**的阶段，不是纯状态名。
- review 阶段的最小输入应包括：
  - `codexRunRecord`
  - `codexSummary`
  - `testResult`（如有）
  - git 现场证据
- review 阶段必须产出：
  - `review` artifact
  - 一个明确后续决策：`fixback / await_user_decision / pr_ready`
- `review` 的本质是 **coordinator 与 Codex 的讨论/收敛阶段**，不是单向强制裁决。
- coordinator 可以给出 review 建议；Codex 可以接受，也可以给出合理理由拒绝接受；双方应继续讨论并尝试达成一致。
- 只有在 coordinator 完成 review 判断，并与执行结果达成一致后，才能进入 `pr_ready` 或其他后续阶段。
- 若多轮讨论后仍无法达成一致，则应升级到 `await_user_decision`，由用户介入拍板。
- 默认最多 3 轮讨论；超过该轮数仍未达成一致，应升级到 `await_user_decision`。
- 若 review 已进入但未产出 `review` artifact，则任务应视为“review 执行中”，不能把该状态误判为已完成。
- watcher 不负责做 review 结论；watcher 只负责 wake agent，正式推进由 agent / review executor 完成。

## 硬约束（phase 1 先写死）
- 不得直接修改 repo
- 不得直接修改 task 状态文件
- 不得跳过 `review`
- 不得从 `codex_run` 直接进入 `review`
- 不得把 `blocked` 当万能中转站

## 规则来源
- `stage-actions.json`
- `../../specs/allowed-transitions.json`
- `../../specs/stage-required-artifacts.json`
- `../../specs/task.schema.json`

## shared layer 约定
- `stage-actions.json` 负责描述“每个 stage 的默认动作策略”
- agent 主循环应优先读这个共享策略，而不是把阶段分支硬编码在项目本地代码里
- 项目本地 workspace 只允许做覆盖项，不重写整套主流程

## 后续接入顺序
- phase 2：`task_init / task_get / task_check / task_transition`
- phase 3：项目编排 agent 接入 task_* tools
- phase 4：shared skill 真正被第二个项目复用
- phase 5+：接 Codex / cron / 用户决策闭环
