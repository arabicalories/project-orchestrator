# 基于 OpenClaw 的项目级开发编排 Agent 方案
**版本：v1.0.1-freeze**  
**状态：实现前冻结基线**  
**目标读者：** OpenClaw 实现者 / 配置者 / 插件开发者  
**文档用途：** 直接指导实现，不是概念说明

---

## 一、需求背景

当前希望在 OpenClaw 中，围绕单个 SaaS 项目建立一个长期维护用的项目级 Agent。  
该 Agent 需要具备以下能力：

### 1. 持有项目长期上下文
包括：
- 项目规则
- 项目记忆
- review 记录
- 项目专属开发说明
- 项目控制面文档

### 2. 接收开发任务并按固定流程推进
流程需要：
- 可复用
- 可检查
- 可中断
- 可恢复

### 3. 真正改代码时不由项目编排 Agent 直接下场改
代码修改统一交给 Codex 这类执行器完成。

### 4. 状态推进不能只靠 prompt 或 skill 软约束
必须有外部强制 check 和状态机控制。

### 5. 通用开发流程可以跨项目复用
新建另一个项目 workspace 时，应尽量复用同一套开发规范和状态机工具，而不是重新写一遍。

### 6. 项目特殊规则仍然可以独立覆盖
不同项目允许在项目 workspace 中追加本地规则。

### 7. 系统第一优先级不是“尽快自动化全部”
而是：
- 先做稳
- 先做硬边界
- 先做最小闭环
- 再逐步增强

本方案面向“开发 / 维护一个项目”场景，先覆盖“项目开发任务”主链路，不追求一开始支持所有复杂能力。

---

## 二、设计目标

### 1. 项目隔离
一个项目对应一个 workspace agent。

### 2. 流程可控
Agent 每一步都基于任务状态机推进，不能随意跳步。

### 3. 代码执行隔离
项目编排 Agent 不直接修改 repo，代码改动交给 Codex 执行层。

### 4. 状态真相单一
任务状态以外部状态目录中的任务文件为准，不以会话上下文为准。

### 5. 强制检查
阶段推进必须通过插件工具校验，不能靠 skill 文字说明。

### 6. 高复用
通用开发规范和 task 工具应做成共享资产，便于给其他 workspace 或其他 OpenClaw 实例复用。

### 7. 渐进实现
必须一步步完成，上一阶段验证通过后，才能进入下一阶段。  
禁止一开始把所有能力同时接入。

### 8. 运行边界明确
项目编排 Agent 的运行权限、可见目录、执行器边界、唤醒方式都必须在实现前拍板，不在实现过程中反复摇摆。

---

## 三、非目标

本期不做以下内容：

1. 多项目统一大面板  
2. 复杂权限系统  
3. 自动部署编排  
4. 完整 A2A 多节点编排  
5. 所有任务类型的通用抽象  
6. ACP 作为第一版执行后端  
7. 复杂事件驱动回调体系  
8. 多任务并发编排的完整机制  
9. 自动发现项目注册信息  
10. 一开始就打通完整 PR 自动化链路

本期只覆盖一条主链路：

**项目开发任务的状态化编排**

---

## 四、整体方案概述

整体采用三层结构：

### A. 项目编排层
每个项目一个 workspace agent。  
该 agent 负责：

- 持有项目长期上下文
- 读取任务状态
- 决定当前该走哪一步
- 在需要时启动 Codex worker
- 接收 Codex 结果
- 执行 review
- 在需要时向用户提问
- 最终准备 PR 或输出结果
- 维护项目 workspace 中的控制面文件

### B. 共享流程层
将通用开发规范做成共享 plugin，plugin 中包含：

- shared skills
- task_* tools

其中：

#### shared skills 负责定义：
- 开发任务的标准流程
- 状态机规则的引用方式
- 每个阶段该做什么
- 何时必须调用哪个 tool
- 何时需要用户决策
- 何时启动 Codex
- 何时进入 review
- 哪些动作属于禁止事项

#### task_* tools 负责实现：
- task_init
- task_get
- task_check
- task_transition
- task_mark_need_user_decision
- task_append_note

后续可扩展：
- task_attach_codex_session
- task_collect_codex_result
- task_create_pr_record

### C. 执行与状态层
包括：

- 代码仓库 repo（放在 workspace 之外）
- 任务状态目录（外部状态真相源）
- Codex 执行器（v1 固定为 tmux worker）
- cron 唤醒机制（v1 固定使用 OpenClaw 内建 cron）

项目编排 Agent 通过 tool 与状态层交互。  
项目编排 Agent 不直接改任务状态文件，不直接改 repo。

---

## 五、关键设计原则

### 原则 1
项目编排 Agent 可以写自己的控制面文件，但不能直接改 repo 和任务状态真相源。

### 原则 2
skill 负责教流程，tool 负责执行硬规则。

### 原则 3
任务推进必须先读状态，再按规范决策，再执行动作，再更新状态。

### 原则 4
任何阶段跳转都必须经过 `task_transition`。  
禁止 agent 直接改任务状态文件。

### 原则 5
新项目优先复用共享 plugin。  
项目 workspace 只放本地差异化规则。

### 原则 6
实现顺序必须从“静态骨架”到“动态执行”，不能直接上完整自动化。

### 原则 7
状态机规则必须先落成机器规则表，不再散落在自然语言段落里。

### 原则 8
`task_check` 与 `task_transition` 职责边界必须硬分离：
- `task_check` = 只读诊断
- `task_transition` = 最终裁决 + 写状态

### 原则 9
项目编排 Agent 的文件系统边界必须靠 sandbox 收紧，而不是靠“不要这么做”的软约束。

### 原则 10
v1 的执行后端、唤醒机制、sandbox 边界必须先拍板，后续实现按冻结基线走，不再反复讨论基础边界。

---

## 六、系统边界与目录建议

### 1. 项目 workspace
用途：
- AGENTS.md
- MEMORY.md
- 项目 notes
- review 结论
- 项目专属 skills
- 本地说明文档
- 控制面工件

建议目录：

```text
/workspace/
  AGENTS.md
  MEMORY.md
  skills/
  notes/
  reviews/
  docs/
  specs/
  samples/
```

说明：
- `specs/`：放冻结规格文件
- `samples/`：放样例任务
- 项目编排 Agent 仅对该 workspace 有读写权限

---

### 2. 代码仓库目录
用途：
- 真正的项目代码
- git 分支与 worktree
- 测试、构建、提交等

建议：
- 放在 workspace 之外
- 默认不暴露给项目编排 Agent 的普通文件写工具
- 由 Codex 执行层使用

---

### 3. 状态目录
用途：
- 任务状态真相源
- 任务日志
- 锁
- 索引

建议目录：

```text
$OPENCLAW_STATE_DIR/project-state/<project-id>/
  tasks/
    T-001.json
    T-002.json
  logs/
  locks/
  index.json
```

说明：
- 不采用“一 repo 一个 task.json”
- 采用“一任务一个状态文件”

原因：
- 支持多个任务并行
- 支持重试、回滚、review 返工
- 支持任务历史查询
- 支持独立恢复和审计

---

## 七、角色定义

### 1. 主 Agent
职责：
- 接收用户需求
- 判断属于哪个项目
- 路由到对应项目 workspace agent
- 汇总多个项目结果
- 在跨项目层面与用户交互

不负责：
- 直接改项目代码
- 直接维护项目任务状态
- 直接做项目内部 review

---

### 2. 项目编排 Agent
职责：
- 该项目的长期“主脑”
- 读取 task 状态
- 结合 shared skills 决定当前阶段动作
- 发起 Codex 执行
- 执行 review
- 回收结果
- 发起阶段推进
- 必要时向用户提问
- 维护项目控制面文档

不负责：
- 直接维护 repo 代码变更
- 绕过 tool 直接改任务状态文件
- 直接改 task 状态真相源

---

### 3. Codex 执行层
职责：
- 按要求修改代码
- 跑测试
- 生成变更结果
- 输出 diff / summary / test result
- 写执行记录

不负责：
- 项目长期记忆
- 状态机编排
- 用户交互决策

---

## 八、项目编排 Agent 的总约束句

从本方案开始，系统总约束固定为：

**项目 agent 只负责：**  
读状态 → 依据 shared skills 判断 → 调 task_* tools 做硬检查 / 推进 → 写 workspace 控制面工件 → 调起 / 观察 Codex worker → review / 问用户

**项目 agent 不负责：**
- 直接改 repo
- 直接改 task 状态真相源
- 直接绕过 tool 推进阶段

如果后续实现偏离这句，视为设计跑偏。

---

## 九、任务状态机设计

### 1. 第一版最小阶段集

```text
intake
plan
await_user_approval
codex_run
collect
review
await_user_decision
fixback
pr_ready
done
blocked
failed
```

---

### 2. 阶段含义

#### intake
新任务刚创建，信息尚未齐全。

#### plan
生成执行计划、风险点、影响范围。

#### await_user_approval
执行前审批。  
含义：计划已产出，但执行前必须得到用户许可。

#### codex_run
已发起 Codex 开发，等待执行层完成。

#### collect
收集 Codex 结果、测试结果、变更摘要。

#### review
项目编排 Agent基于规则做 review。

#### await_user_decision
结果后决策。  
含义：review 或执行结果已产出，需用户决定后续方向。

#### fixback
review 未通过，返回给 Codex 继续修正。

#### pr_ready
系统判断已满足“可提交 / 可建 PR”的条件，但最终交付闭环尚未完成。

#### done
最终交付闭环已完成。

#### blocked
有原因的暂停态。

#### failed
明确失败，不再自动重试。

---

## 十、合法跳转表

以下表为第一版正式合法跳转表：

```json
{
  "intake": ["plan", "blocked", "failed"],
  "plan": ["await_user_approval", "codex_run", "blocked", "failed"],
  "await_user_approval": ["codex_run", "blocked", "failed"],
  "codex_run": ["collect", "blocked", "failed"],
  "collect": ["review", "blocked", "failed"],
  "review": ["fixback", "await_user_decision", "pr_ready", "failed"],
  "await_user_decision": ["fixback", "pr_ready", "done", "failed"],
  "fixback": ["codex_run", "blocked", "failed"],
  "pr_ready": ["done", "failed"],
  "blocked": ["plan", "await_user_approval", "codex_run", "failed"],
  "failed": [],
  "done": []
}
```

---

### 补充解释

#### 1. intake
只能进入：
- plan
- blocked
- failed

#### 2. plan
完成后要么：
- 进入 `await_user_approval`
- 若任务无需审批则可直接进入 `codex_run`

#### 3. await_user_approval
只表示执行前审批。

#### 4. collect
只负责收结果，不做方向选择。

#### 5. review
是第一次正式判断质量与方向的阶段。

#### 6. await_user_decision
只表示结果后决策。

#### 7. blocked
可以被人工或流程恢复，但受恢复规则约束。

#### 8. done / failed
为终态。

---

### 禁止事项

禁止以下跳转：

- 任意跨阶段跳转
- 不经 review 直接从 collect 到 pr_ready
- 不经 collect 直接从 codex_run 到 review
- 不经 task_transition 直接修改 stage
- 将 blocked 当万能中转站任意跳回执行态

---

## 十一、blocked 恢复规则

### 1. 新增字段

```text
blockedReasonKind = dependency | missing-info | external-error | manual-hold | other
```

### 2. 规则

1. `blocked` 不是万能中转站  
2. `blocked` 只能恢复到：
   - 阻塞前最近一个可恢复阶段
   - 或人工显式指定的恢复阶段
3. 如果没有恢复依据，则默认只能恢复到 `plan`
4. 不允许从 `blocked` 任意跳回 `codex_run`、`collect`、`review` 等执行态，除非：
   - history 中明确记录了阻塞前阶段
   - 且该阶段被定义为可恢复
   - 或人工明确指定恢复目标
5. `blockedReasonKind` 必须在进入 `blocked` 时写入
6. 从 `blocked` 恢复时，必须写 history，说明：
   - 恢复依据
   - 恢复目标阶段
   - 操作者

### 3. 对 allowed_transitions 的解释修订

`blocked -> plan | await_user_approval | codex_run | failed` 这条表面允许仍保留，但增加硬约束：

- 若无恢复依据，`blocked` 默认只能到 `plan`
- `await_user_approval` / `codex_run` 只能在“阻塞前最近可恢复阶段”就是该阶段时才允许进入

---

## 十二、每阶段必备工件表

以下表为第一版正式必备工件表：

```json
{
  "intake": [],
  "plan": [],
  "await_user_approval": ["plan"],
  "codex_run": ["plan"],
  "collect": ["codexRunRecord"],
  "review": ["codexRunRecord", "codexSummary"],
  "await_user_decision": ["review"],
  "fixback": ["review"],
  "pr_ready": ["review"],
  "done": ["review"],
  "blocked": [],
  "failed": []
}
```

---

### 说明

1. 表中写的是“进入该阶段前必须已经存在的工件”
2. 第一版故意收得很小
3. `testResult` 暂不强制为所有任务必备工件
4. 若任务声明需要测试，则 `task_check` 应把缺失测试结果计为：
   - error，或
   - warning  
   取决于任务定义
5. `collect` 阶段最小依赖是 `codexRunRecord`
6. `review` 阶段必须至少有：
   - `codexRunRecord`
   - `codexSummary`
7. `pr_ready` / `done` 必须已有 `review`

---

## 十三、done 闭环规则

### 1. 原则

`done` 不能只靠 `review` 存在进入。

进入 `done` 必须同时满足：

1. `review` 存在
2. 且满足以下任一闭环条件：
   - 用户已明确接受结果
   - 已创建 PR，且本任务定义将“PR 已创建”视为完成
   - 已完成该任务定义中的最终交付动作

---

### 2. 新增字段建议

```json
{
  "deliveryClosure": {
    "kind": "user-accepted|pr-created|merged|manual-close|other",
    "detail": "string",
    "closedAt": "ISO-8601 string"
  }
}
```

a也可为：

```json
"deliveryClosure": null
```

---

### 3. 规则

1. `pr_ready`  
   含义固定为：  
   系统判断已满足“可提交 / 可建 PR”的条件，但最终交付闭环尚未完成

2. `done`  
   含义固定为：  
   最终交付闭环已完成

3. 若无 `deliveryClosure`，不得进入 `done`
4. 若任务类型要求 PR，则仅有 review 不足以进入 `done`
5. 若任务类型要求用户确认，则仅有 review 不足以进入 `done`

---

### 4. 对 stage_required_artifacts 的解释修订

`done = ["review"]` 仅表示最小工件要求。  
真正进入 `done` 还必须通过 `deliveryClosure` 规则检查。

---

## 十四、用户参与阶段绑定规则

### 1. 字段语义固定如下

#### needsUserDecision
当前任务是否正处于“必须等待用户输入”的状态。

#### userDecisionKind
```text
approval | result-decision | direction-choice | other
```

#### userDecisionReason
当前为什么必须等用户。

---

### 2. 总规则

1. 进入任一 `await_user_*` 阶段前，必须先或同时完成 `task_mark_need_user_decision`
2. 若 `needsUserDecision=false`，则不得停留在：
   - `await_user_approval`
   - `await_user_decision`
3. `await_user_approval` 只用于执行前审批
4. `await_user_decision` 只用于结果后决策
5. 从任一 `await_user_*` 阶段离开时，应清理或闭合对应的 user decision 状态

---

### 3. 规则细化

#### A. 进入 `await_user_approval`
必须满足：
- `needsUserDecision = true`
- `userDecisionKind = approval`

#### B. 进入 `await_user_decision`
必须满足：
- `needsUserDecision = true`
- `userDecisionKind = result-decision`
  或 `direction-choice`
  或 `other`

#### C. 离开任一 `await_user_*` 阶段时
若用户决策已完成，则必须：
- `needsUserDecision = false`
- `userDecisionReason` 清空或归档
- 写 history

#### D. `task_mark_need_user_decision`
职责固定为：
- 只负责写“需要用户参与”的标志与原因
- 不负责阶段推进

#### E. `task_transition`
职责固定为：
- 推进到 `await_user_*` 前，必须校验 needsUserDecision 绑定关系
- 若绑定关系不成立，则拒绝推进

---

## 十五、工件模型正式定稿

### 1. ArtifactRef 结构

所有 artifacts 字段统一采用轻量引用对象，不直接内嵌长正文。

```json
{
  "type": "plan|codexRunRecord|codexSummary|review|testResult|other",
  "path": "string",
  "summary": "string",
  "updatedAt": "ISO-8601 string"
}
```

---

### 2. 字段说明

- `type`：工件类别
- `path`：工件文件路径，建议为项目控制面 workspace 内的相对路径，或状态目录内的约定路径
- `summary`：一句话摘要
- `updatedAt`：最近更新时间

---

### 3. 统一规则

1. `task.json` 中只存 `ArtifactRef`
2. 长正文放 markdown 文件
3. 所有 tool 返回中如果涉及工件，统一返回：
   - `ArtifactRef`
   - 或 `ArtifactRef[]`
4. 不允许每个实现者自创不同工件引用结构

---

## 十六、task.json 第一版结构

```json
{
  "id": "MYSAAS-001",
  "projectId": "my-saas",
  "repoId": "repo-main",
  "title": "修复登录页表单校验问题",
  "goal": "修复登录页表单校验 bug，并补充相关测试",
  "constraints": [
    "必须通过 Codex worker 执行代码修改",
    "不得直接修改 main 分支"
  ],
  "stage": "intake",
  "needsUserDecision": false,
  "userDecisionKind": null,
  "userDecisionReason": "",
  "blockedReasonKind": null,
  "deliveryClosure": null,
  "codexSession": null,
  "repoRef": {
    "repoPath": "/repos/my-saas",
    "branch": "feature/MYSAAS-001",
    "worktree": null
  },
  "artifacts": {
    "plan": null,
    "codexRunRecord": null,
    "codexSummary": null,
    "review": null,
    "testResult": null
  },
  "acceptanceChecks": [
    "review 通过",
    "输出变更摘要"
  ],
  "history": [],
  "createdAt": "",
  "updatedAt": ""
}
```

---

### 说明

1. `taskId` 正式拍板为“项目内唯一即可”
2. 格式建议：
   - `MYSAAS-001`
   - `MYSAAS-002`
3. 不做全局唯一
4. `history` 为审计导向轻量日志
5. `userDecisionKind` 用于区分审批 / 结果后决策
6. `blockedReasonKind` 用于描述阻塞原因
7. `deliveryClosure` 用于描述最终交付闭环

---

## 十七、history 审计结构

history 第一版正式定义为轻量审计日志，不是普通聊天笔记。

```json
{
  "timestamp": "ISO-8601 string",
  "actor": "user|project-agent|tool:task_transition|tool:task_check|codex|system",
  "action": "string",
  "fromStage": "string|null",
  "toStage": "string|null",
  "reason": "string",
  "changedFieldsSummary": ["string"]
}
```

---

### 规则

1. `task_transition` 必须写 history
2. `task_init` 必须写 history
3. 关键失败、blocked、用户决策写入 history
4. 纯说明性长文本不写 history，放 notes 或 markdown 工件
5. history 以审计为主，不承载长正文

---

## 十八、shared skills 设计

shared skills 的职责：

- 定义通用开发流程
- 告诉项目编排 Agent 每轮该如何思考
- 告诉 Agent 何时必须调用 task_* tool
- 告诉 Agent 何时必须调用 Codex
- 告诉 Agent 哪些文件属于工件，哪些属于控制面
- 引用冻结的规则表，而不是自己重新“解释规则”

---

### shared skills 应包含

#### 1. 任务循环规则
每次唤醒后必须：
- 先读取 task 状态
- 识别当前 stage
- 读取对应工件
- 只选择当前阶段允许的动作

#### 2. 阶段行动规范
例如：
- 若 `stage=intake`，则补充任务信息或生成 plan
- 若 `stage=plan`，则输出计划并判断是否需用户审批
- 若 `stage=codex_run`，则不得直接改状态，需等待或收集结果
- 若 `stage=review`，则必须输出 review 结论并再决定是否 transition

#### 3. 工具调用规范
例如：
- 读取任务必须调用 `task_get`
- 推进阶段必须调用 `task_transition`
- 需要校验必须调用 `task_check`
- 需要用户拍板时必须调用 `task_mark_need_user_decision`

#### 4. 禁止事项
例如：
- 不得直接修改任务状态文件
- 不得在未生成 plan 时启动 Codex
- 不得跳过 review 进入 pr_ready
- 不得直接在 repo 执行代码修改，除非通过指定执行器

#### 5. 输出工件规范
例如：
- plan 要有目标、风险、步骤、影响范围
- review 要有通过 / 不通过结论和理由
- Codex 回收结果要有变更摘要和测试结论

---

### shared skills 不应包含

- 项目业务规则
- 某个项目的目录结构细节
- 某个项目的分支命名特殊要求
- 某个项目的部署命令
- 某个项目的 PR 模板细节

---

## 十九、workspace 专属 skills 设计

workspace skills 只负责项目差异，例如：

- 该项目使用 pnpm
- 该项目测试命令为 `pnpm test`
- 该项目 PR 模板要求
- 该项目哪些目录不能自动改
- 该项目部署需要人工确认
- 该项目常见风险点

---

### 原则

1. 通用流程不在 workspace 重写
2. 只放覆盖项和补充项
3. 项目特有规则不应污染 shared plugin

---

## 二十、task_* tools 精确定义

### 1. task_init

#### 职责
- 创建新任务状态文件
- 生成初始 history
- 初始化最小字段

#### 输入
```json
{
  "projectId": "string",
  "repoId": "string",
  "title": "string",
  "goal": "string",
  "constraints": ["string"]
}
```

#### 输出
```json
{
  "taskId": "string",
  "stage": "intake",
  "taskPath": "string"
}
```

#### 副作用
- 写新任务状态文件
- 写初始 history

---

### 2. task_get

#### 职责
- 只读获取当前任务完整状态

#### 输入
```json
{
  "taskId": "string"
}
```

#### 输出
```json
{
  "task": { "...完整任务对象...": true }
}
```

#### 副作用
- 无

---

### 3. task_check

#### 职责
- 只读诊断
- 基于规则表检查“当前任务在当前上下文下是否满足推进条件”
- 不写状态
- 不给建议路径
- 不做任何副作用

#### 输入
```json
{
  "taskId": "string",
  "targetStage": "string|null",
  "checkType": "transition-readiness|artifact-completeness|consistency"
}
```

#### 推荐语义
- `targetStage` 为空时：做当前一致性检查
- `targetStage` 不为空时：做“是否具备推进到该阶段的条件”检查

#### 输出
```json
{
  "passed": true,
  "errors": [],
  "warnings": [],
  "missingArtifacts": []
}
```

#### 规则
- `errors` = 阻止推进
- `warnings` = 不阻止，但提示风险
- `missingArtifacts` = 明确缺失项
- 不返回 `suggestedNextStage`
- 不写 history
- 不改 `task.json`

---

### 4. task_transition

#### 职责
- 唯一合法阶段推进入口
- 校验是否合法
- 校验必备工件
- 若合法则写状态和 history

#### 输入
```json
{
  "taskId": "string",
  "targetStage": "string",
  "reason": "string"
}
```

#### 输出
```json
{
  "success": true,
  "fromStage": "string",
  "toStage": "string",
  "errors": []
}
```

#### 规则
- 内部必须基于：
  - `allowed_transitions`
  - `stage_required_artifacts`
  做校验
- 失败时不写状态
- 成功时只改状态与 history
- 第一版不允许附带副作用
- 不自动创建 plan
- 不自动发消息
- 不自动绑定 codex session
- 不自动生成任何工件

#### 补充
- 推进到 `await_user_*` 前，必须校验 user-decision 绑定规则
- 推进到 `done` 前，必须校验 `deliveryClosure` 闭环规则
- 从 `blocked` 恢复时，必须校验 blocked 恢复规则

---

### 5. task_mark_need_user_decision

#### 职责
- 将任务标记为需要用户参与
- 写明原因和类型

#### 输入
```json
{
  "taskId": "string",
  "decisionKind": "approval|result-decision|direction-choice|other",
  "reason": "string"
}
```

#### 输出
```json
{
  "success": true
}
```

#### 副作用
- 更新 `needsUserDecision`
- 更新 `userDecisionKind`
- 更新 `userDecisionReason`
- 写 history

#### 规则
- 只负责设置用户决策状态
- 不负责阶段推进

---

### 6. task_append_note

#### 职责
- 往控制面笔记或状态注记中追加结构化记录
- 不负责阶段推进

#### 输入
```json
{
  "taskId": "string",
  "noteType": "plan-note|review-note|ops-note|other",
  "content": "string"
}
```

#### 输出
```json
{
  "success": true
}
```

#### 副作用
- 写 notes 工件或约定的补充记录
- 可写 history，也可不写，视 noteType 决定

---

### 最终一句硬约束

`task_check = 只读诊断`  
`task_transition = 最终裁决 + 写状态`  

两者职责不允许混淆。

---

## 二十一、强制检查机制

目标：
让“阶段推进”脱离 skill 软约束，变成硬规则控制。

### 方法

1. skill 只负责描述“应该怎么做”
2. 真正的阶段变更只能通过 `task_transition`
3. `task_transition` 内部执行硬检查
4. 检查不通过则拒绝推进

---

### 需要检查的典型内容

- 当前 stage 是否允许跳到 targetStage
- 计划文件是否存在
- review 结论是否存在
- 测试结果是否存在
- 是否已获取用户审批
- 是否已绑定了用户决策状态
- 是否缺关键工件
- `blocked` 是否满足恢复依据
- `done` 是否满足交付闭环

---

### 原则

- Agent 可以发起推进请求
- 插件工具负责最终裁决
- 任何“自己改 task.json”都视为绕过流程

这部分是本方案的核心。

---

## 二十二、sandbox 与权限策略

### 1. 为什么需要 sandbox
目的是限制项目编排 Agent 的工具可见范围，避免误碰宿主机其他目录。

### 2. 正式拍板
v1 正式拍板：**项目 workspace agent 必须运行在 sandbox 中。**

### 3. 推荐配置
- `workspaceAccess = rw`
- 只允许读写当前 workspace
- 不额外挂 repo 路径
- 不额外挂 task 状态目录

### 4. 结果边界

#### 项目编排 Agent 可以：
- 修改 AGENTS.md
- 修改 MEMORY.md
- 写 review.md、notes、workspace skills
- 写项目控制面文档

#### 项目编排 Agent 不可以直接：
- 修改 repo 文件
- 修改 task 状态真相源
- 通过文件路径绕过 task_* tools

### 5. 说明
- sandbox 不是所有 workspace agent 都必须开
- 但对“项目编排 agent”这类需要强边界控制的 agent，v1 方案明确要求必须开
- 这是本方案的硬要求，不再是可选项

---

## 二十三、Codex 执行接入方案

### 1. v1 执行后端正式拍板
v1 固定为：**tmux worker**

### 2. 为什么不是 ACP 作为 v1
不是否定 ACP。  
ACP 是 OpenClaw 官方支持 Codex 等外部 coding harness 的标准链路，这一点成立。

但本方案第一优先级是：
- 项目状态机先做硬
- 编排层与执行层解耦
- OpenClaw 异常时，Codex 不应直接中断

因此，v1 先选：
**tmux worker + 状态机回收**

ACP 可作为 v1.1 或后续适配层，不在本补丁实现范围内。

### 3. 抽象要求
虽然 v1 固定 tmux worker，但项目编排层不得依赖 tmux 细节。  
必须抽象出统一的执行记录对象。

---

### 4. CodexRunRecord 最小结构

```json
{
  "executor": "tmux-codex",
  "sessionId": "string",
  "status": "running|finished|failed",
  "startedAt": "ISO-8601 string",
  "endedAt": "ISO-8601 string|null",
  "logPath": "string|null",
  "summaryPath": "string|null"
}
```

### 5. 说明
- `artifacts.codexRunRecord` 记录该对象的 `ArtifactRef`
- collect 阶段基于此对象回收结果

---

### 6. collect 阶段职责
collect 只做：
- 读取 `codexRunRecord`
- 判断 worker 是否完成
- 若完成，收集：
  - `codexSummary`
  - `testResult`
  - 等工件引用
- 不做 review 判断
- 不做用户方向决策

---

## 二十四、cron 使用规格

### 1. 正式拍板
v1 使用 OpenClaw 内建 cron 作为唯一标准唤醒机制。

### 2. 职责边界
cron 的职责是：
- 定时唤醒项目编排 agent
- 让它执行一轮：
  - 读状态
  - 观察 worker
  - collect / review / 推进

cron 不负责：
- 直接推进业务状态
- 直接改 task.json
- 替代 task_transition

### 3. 第一版建议
默认检查间隔：
- `codex_run` 阶段：每 3 分钟
- `blocked` 或 `await_user_*` 阶段：不自动频繁轮询

### 4. 原因
cron 是持久化调度器，适合做“定时唤醒 agent”动作。

---

## 二十五、主 Agent 路由规格

v1 明确采用：**静态项目注册表**  
不做自动发现。

### ProjectRegistryEntry

```json
{
  "projectId": "my-saas",
  "workspaceAgentId": "agent-mysaas",
  "workspaceLabel": "project-mysaas",
  "repoId": "repo-main"
}
```

### 主 Agent 职责
- 根据 `projectId` 查表
- 将任务路由给对应项目 agent
- 不猜测
- 不扫描
- 不自动发现

---

## 二十六、项目编排 Agent 的运行循环

每次被唤醒时，必须按以下顺序执行：

### 步骤 1
读取 task 状态。  
不得跳过。

### 步骤 2
识别当前 stage。

### 步骤 3
按 shared skills 规则判断该阶段允许的动作集合。

### 步骤 4
读取必要工件。

### 步骤 5
选一个动作执行。  
动作类型可能包括：
- 生成 plan
- 请求用户审批
- 启动 Codex
- 回收结果
- 调用 task_check
- 调用 task_transition
- 输出 review
- 标记 blocked
- 请求用户决策

### 步骤 6
记录结果。  
必要时写 review、notes、history。

### 步骤 7
若需推进阶段，则调用 task_transition。  
不得直接改状态文件。

### 步骤 8
若任务未完成，则等待下一次消息或定时唤醒。

---

## 二十七、通知与用户干预

用户可通过以下两类入口参与：

1. 主会话  
2. 项目 Agent 的项目频道

---

### 规则建议

- 主会话负责派单、跨项目汇总、升级决策
- 项目频道负责项目内部讨论、review 反馈、是否接受该次方案

---

### 项目编排 Agent 在以下情况必须主动询问用户

- 计划不明确
- 方案存在明显分叉
- review 不通过且有多种修复方向
- 需要手工决定是否创建 PR
- 有高风险改动

---

### 项目编排 Agent 在以下情况应自动继续

- 任务状态明确
- 阶段合法
- 所需工件齐全
- 不需要人工拍板

---

## 二十八、复用与迁移方案

目标：
让这套机制不仅能给一个 workspace 用，也能给其他项目或其他 OpenClaw 用。

### 推荐复用单位
一个正式 plugin 包。

plugin 中包含：
1. shared skills
2. task_* tools
3. 可选默认配置或说明文档

---

### 项目级差异保留在

- 项目 workspace 的 AGENTS.md
- 项目 workspace 的 MEMORY.md
- 项目 workspace 的 skills/
- 项目自己的 repo 信息

---

### 迁移到另一个 workspace

1. 安装同一个 plugin  
2. 新建项目 workspace agent  
3. 放入项目自己的 AGENTS.md / MEMORY.md  
4. 配置该项目 repo 标识  
5. 开始创建任务

---

### 迁移到另一台 OpenClaw

1. 安装 plugin 包  
2. 启用 plugin  
3. 创建对应 workspace agent  
4. 接入该实例的 repo 与 Codex 执行层

---

## 二十九、阶段 1 必须具备的样例任务

### 样例 A：正常流

**目标：**  
修复登录页校验问题

**流转：**
```text
intake
→ plan
→ await_user_approval
→ codex_run
→ collect
→ review
→ pr_ready
→ done
```

---

### 样例 B：review 打回流

**目标：**  
修复上传组件边界条件 bug

**流转：**
```text
intake
→ plan
→ codex_run
→ collect
→ review
→ fixback
→ codex_run
→ collect
→ review
→ await_user_decision
→ pr_ready
→ done
```

---

### 要求

- 这两个样例必须在阶段 1 就写成静态样例文件
- 阶段 2 实现 tool 时直接拿这两个样例验证
- 样例不只是流转路径，最好同时附带：
  - 当前 stage
  - 合法 targetStage
  - 需要的 artifacts
  - 缺失时预期的 check 输出

---

## 三十、实现顺序

必须按顺序做，不允许一开始把所有能力一起实现。

### 阶段 1：静态骨架
先做：
1. 项目 workspace agent
2. 项目目录骨架
3. shared skills 文档骨架
4. task 状态文件 schema
5. 最小状态目录结构
6. 两个样例任务

**验收标准：**
- 能手动创建任务状态文件
- 能手动读取并理解阶段
- skills 文档能指导流程
- 两个样例任务能覆盖正常流与 review 打回流

---

### 阶段 2：最小 task tools
再做：
1. task_init
2. task_get
3. task_transition
4. task_check 的最小版本

**验收标准：**
- task 状态只能通过 tool 推进
- 非法阶段跳转能被拒绝
- 能返回清晰错误原因
- 可根据样例任务验证通过 / 失败路径

---

### 阶段 3：项目编排 Agent 接入 task tools
再做：
1. 项目编排 Agent 每轮先 task_get
2. 根据 stage 选择动作
3. 需要推进时调用 task_transition

**验收标准：**
- 不依赖手工改状态
- Agent 能按状态机推进至少一条完整假任务

---

### 阶段 4：接入 shared skills
再做：
1. 将通用流程逻辑移到 shared skills
2. 在 workspace 中只保留项目特有差异

**验收标准：**
- 第二个项目能复用同一套 shared skills
- 项目特例能在 workspace 中覆盖

---

### 阶段 5：接入 Codex 执行层
再做：
1. 启动 Codex
2. 绑定任务
3. 回收执行结果
4. 写入 collect / review 所需工件

**验收标准：**
- 至少跑通一条真实开发任务
- 能从 `codex_run` 进入 `collect/review`

---

### 阶段 6：补强用户决策与 review 闭环
再做：
1. await_user_approval
2. await_user_decision
3. fixback

**验收标准：**
- review 不通过时能返工
- 用户可以在关键节点介入

---

### 阶段 7：增强项
最后再做：
1. 定时检查增强
2. 多任务并发
3. tmux worker 完善
4. 更复杂的恢复与重试
5. ACP adapter

**原因：**  
这些属于增强项，不应阻塞主链路先跑通。

---

## 三十一、关键验收标准

1. 新建一个项目 workspace 后，可开始维护该项目  
2. 项目编排 Agent 能维护 AGENTS.md、MEMORY.md、项目 notes  
3. 项目编排 Agent 不能直接修改任务状态真相源  
4. 任务状态只能通过 task_* tools 推进  
5. 同一套 shared skills 和 task tools 能被第二个项目复用  
6. 代码执行层和项目编排层分离  
7. 至少一条真实任务能完整经历：

```text
intake -> plan -> codex_run -> collect -> review -> pr_ready/done
```

---

## 三十二、给 OpenClaw 的实现要求

1. 先搭阶段 1 到阶段 3 的最小系统，不要先接 Codex 真执行  
2. 每完成一个阶段，都要提供：
   - 当前目录结构
   - 当前配置说明
   - 当前 task 状态机说明
   - 当前已支持和未支持的能力
3. 不要一次生成所有插件、所有工具、所有自动化  
4. 每次实现只新增一小层能力，并用真实任务样例验证  
5. 所有关键状态推进逻辑都要保留可观察日志  
6. 实现必须以 v1.0.1-freeze 为基线，不在实现过程中重新讨论已冻结的基础边界

---

## 三十三、冻结结论

v1.0.1-freeze 是实现前冻结基线。  
以下内容已正式冻结：

1. 状态机合法跳转表  
2. 每阶段必备工件表  
3. artifact 引用结构  
4. task_* tool 精确定义  
5. blocked 恢复规则  
6. done 闭环规则  
7. await_user_* 与 needsUserDecision 绑定规则  
8. v1 执行后端 = tmux worker  
9. v1 唤醒机制 = OpenClaw cron  
10. 项目 workspace agent 必须运行在 sandbox 中  
11. repo 与 task 状态真相源不暴露给项目编排 agent

冻结后，不再继续讨论基础边界。  
后续工作进入实现阶段。

---

## 三十四、最终一句话总结

本方案要实现的不是“一个会写代码的大模型”，  
而是一套：

**项目级编排 Agent + 共享开发规范 + 外部执行器 + 强制状态机检查**

的开发系统。

项目上下文归项目 workspace。  
通用开发规范归 shared plugin。  
代码修改归 Codex worker。  
状态推进归 task_* tools。  
实现时必须先做骨架，再做 tool，再做编排，再接执行层，逐步完成。
