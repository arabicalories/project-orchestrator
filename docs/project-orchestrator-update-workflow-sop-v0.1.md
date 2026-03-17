# Project Orchestrator Update Workflow SOP v0.1

目标仓库：`https://github.com/arabicalories/project-orchestrator.git`

> 当前这台机器的稳定推送方式默认按 HTTPS 处理；若本地 `origin` 仍是 SSH，先切到 HTTPS 再 push。

本文档用途：定义 `project-orchestrator` 后续修改与更新的标准工作流，确保：
- 不影响当前 local-private 真实实例的使用；
- 不把 workspace 中的本地私有内容、运行态和无关目录误带入 GitHub 仓库；
- 后续更新低摩擦、可重复、可检查。

---

## 1. 核心原则

当前阶段默认采用三段式结构：

1. **workspace**：真实开发源
   - 建议使用统一的 workspace 根目录：`<workspace-root>`
   - 用于真实开发、真实验证、真实实例维护。

2. **staging**：整理区
   - 用于把 workspace 中可公开到私有内测仓库的内容做一次脱敏、裁剪、归档。
   - staging 不是长期真相源，而是每次同步前的整理快照。

3. **GitHub 仓库**：整理后的发布镜像
   - 目标仓库：`https://github.com/arabicalories/project-orchestrator.git`
   - 只接收已经裁剪好的 sample / docs / core / runtime / tests 内容。

一句话规则：
**workspace 是开发源，staging 是整理区，GitHub 仓库是输出镜像。**

---

## 2. 单一真相源规则

### 2.1 通用能力的真相源
以下内容的真相源是当前 workspace：
- `project-orchestrator/specs/**`
- `project-orchestrator/shared-skills/project-orchestrator-dev/**`
- `scripts/project_orchestrator_*.py`
- `scripts/test_project_orchestrator_*.py`
- `docs/project-orchestrator-*.md`

更新顺序：
- 先在 workspace 修改并验证；
- 再同步到 staging；
- 最后同步到 GitHub 仓库。

### 2.2 示例面的真相源
以下内容构成 GitHub 私有内测仓库的示例面真相源：
- `project-orchestrator/projects/pa-sample/**`
- `project-orchestrator/registry/projects.sample.json`
- `docs/project-orchestrator-github-packaging-plan-v0.1.md`

### 2.3 local-private 真相源
以下内容永远视为本地真实环境内容：
- `project-orchestrator/projects/<local-private-instance>/**`
- `project-orchestrator/registry/projects.json`
- `runtime/**`
- `memory/**`
- 其他当前 workspace 的本地私有与运行态目录

这些内容：
- 不作为 sample 说明来源；
- 不进入 GitHub 仓库；
- 不倒灌回 `pa-sample`。

---

## 3. 改动分类规则

每次修改完成后，先判断本次改动属于哪一类：

### A 类：通用能力改动
示例：
- 状态流转、review 语义、executor 通用逻辑、watcher 通用逻辑、specs、shared skill。

处理原则：
- 默认应同步到 GitHub 仓库。

### B 类：示例面跟进改动
示例：
- `pa-sample` 配置字段更新；
- `projects.sample.json` 更新；
- 文档对 sample 的说明更新。

处理原则：
- 默认应同步到 GitHub 仓库。

### C 类：真实实例专属改动
示例：
- local-private 真实实例的真实路径、真实群、真实 env、真实运行特化。

处理原则：
- 只留在 workspace；
- 不同步到 GitHub 仓库。

### D 类：运行态 / 调试产物
示例：
- `runtime/**`
- `__pycache__/**`
- `*.log`
- `*.jsonl`
- review card 运行结果

处理原则：
- 永远不进入 GitHub 仓库。

---

## 4. 每次更新的推荐流程

### Step 1：在 workspace 完成开发与验证
在当前 workspace 完成：
- 代码修改；
- 文档更新；
- 真实验证；
- 必要的 sample 跟进。

### Step 2：判断是否需要同步到 GitHub 仓库
只有满足以下至少一项时，才进入同步流程：
- 本次改动属于 A 类（通用能力）；
- 本次改动属于 B 类（示例面跟进）；
- 当前想更新 GitHub 私有内测仓库的基线说明。

若仅属于 C / D 类，则不进入同步流程。

### Step 3：准备 staging 目录
建议使用独立目录，例如：
- `<staging-repo>`

作者本机示例：
- `/root/projects/staging/project-orchestrator-private/`

在 staging 中：
- 创建仓库骨架；
- 复制允许进入 GitHub 仓库的文件；
- 排除 local-private 与运行态内容；
- 创建或更新 `README.md`、`.gitignore`、`.ignore`。

### Step 4：在 staging 做同步前检查
至少检查以下内容：
1. 是否误带 local-private 真实实例目录；
2. 是否误带 `project-orchestrator/registry/projects.json`；
3. 是否误带 `runtime/**`、`memory/**`、`msg-recover/**`、`reports/**`、`tmp/**`；
4. sample config 是否仍然是占位值；
5. docs 是否需要同步更新；
6. `.gitignore` 与 `.ignore` 是否都存在且覆盖一致边界。

### Step 5：通过检查后再同步到 GitHub 仓库
只有当 staging 内容通过检查后，才允许：
- 初始化或更新 Git 仓库；
- commit；
- push 到 `git@github.com:arabicalories/project-orchestrator.git`。

---

## 5. staging 目录的默认职责

staging 目录的作用不是长期开发，而是：
- 承接文件搬运清单；
- 承接 sample / docs / core / runtime 的整理版；
- 在 push 前做最后一轮过滤与检查。

staging 目录默认不做：
- 真实实例运行；
- 真实 runtime 状态持久化；
- 本地私有配置管理。

---

## 6. 默认同步清单

### 6.1 默认同步到 GitHub 仓库
- `docs/project-orchestrator-agent-prd-v1.0.1-freeze.md`
- `docs/project-orchestrator-implementation-status-v0.1.md`
- `docs/project-orchestrator-github-packaging-plan-v0.1.md`
- `project-orchestrator/README.md`
- `project-orchestrator/component-manifest.json`
- `project-orchestrator/specs/**`
- `project-orchestrator/shared-skills/project-orchestrator-dev/**`
- `project-orchestrator/workspace-template/**`
- `project-orchestrator/state-template/**`
- `project-orchestrator/samples/**`
- `project-orchestrator/registry/projects.sample.json`
- `project-orchestrator/projects/pa-sample/**`
- `scripts/project_orchestrator_agent.py`
- `scripts/project_orchestrator_executor.py`
- `scripts/project_orchestrator_instance_runner.py`
- `scripts/project_orchestrator_review.py`
- `scripts/project_orchestrator_task_tools.py`
- `scripts/project_orchestrator_watcher.py`
- `scripts/project_orchestrator_phase1_check.py`
- `tests/**`（或从 `scripts/test_*.py` 重组后的测试目录）

### 6.2 默认不进入 GitHub 仓库
- `project-orchestrator/projects/<local-private-instance>/**`
- `project-orchestrator/registry/projects.json`
- `runtime/**`
- `memory/**`
- `msg-recover/**`
- `progress-notify/**`
- `reports/**`
- `tmp/**`
- `**/__pycache__/**`
- `**/.pytest_cache/**`
- `**/.mypy_cache/**`
- `*.pyc`
- `*.log`
- `*.jsonl`
- `.env`
- `.env.*`

---

## 7. `.gitignore` 与 `.ignore` 规则

未来 GitHub 仓库准备阶段必须同时维护：
- `.gitignore`
- `.ignore`

### 7.1 `.gitignore`
用途：
- 让 Git 不跟踪 local-private / runtime / cache / log / env 内容。

### 7.2 `.ignore`
用途：
- 让本地工具、搜索、扫描、打包流程遵守同样的排除边界；
- 避免后续虽然 Git 忽略了，但工具仍把这些目录卷进来。

### 7.3 当前要求
- 两者的排除边界应保持一致；
- 若未来新增排除目录，应同步更新 `.gitignore` 与 `.ignore`；
- 不允许只更新其中一个。

---

## 8. 每次同步前最小检查清单

每次准备从 workspace 更新 GitHub 仓库前，至少回答这 6 个问题：

1. 这次改动属于 A / B / C / D 哪一类？
2. 是否误带真实实例目录？
3. 是否误带真实 registry 或 runtime 状态？
4. sample config 是否仍是占位值？
5. 本次是否需要同步 docs / README？
6. `.gitignore` 与 `.ignore` 是否同步？

只有这 6 条都过了，才进入 commit / push。

---

## 9. 当前默认提交策略

建议使用简洁提交类型：
- `feat:` 通用能力进入私有内测仓库
- `docs:` 文档/packaging/sample 更新
- `refactor:` 目录与结构整理
- `test:` 测试更新

不建议：
- 把真实实例改动混进 GitHub 仓库提交；
- 把运行态、日志、缓存混进提交；
- 把无关 workspace 内容混进提交。

---

## 10. 速用版（平时就按这个跑）

如果你只是想快速更新仓库，不想每次重读整篇 SOP，默认按下面 8 步执行：

1. 在 workspace 完成真实修改与验证；
2. 先判断这次是不是 A / B 类改动；若只是 local-private 或运行态改动，就不发 GitHub；
3. 把需要发布的内容同步到 staging；
4. 确认 sample 面仍然是 `pa-sample`，不要把 local-private 实例带进去；
5. 跑测试；
6. grep 一轮真实路径 / 真实群 / 真实 open_id / 真实实例名等高风险串；
7. 确认 `.gitignore` 与 `.ignore` 都已覆盖本次新增边界；
8. 在 staging 先跑发布前检查，再提交并 push：

```bash
cd <staging-repo>

python scripts/release_check.py
git status --short
git add .
git commit -m "<type>: <summary>"
HOME=/root GH_CONFIG_DIR=/root/.config/gh git push origin main
```

作者本机示例：

```bash
# author-local example
cd /root/projects/staging/project-orchestrator-private

python scripts/release_check.py
git status --short
git add .
git commit -m "<type>: <summary>"
HOME=/root GH_CONFIG_DIR=/root/.config/gh git push origin main
```

## 11. 当前结论

后续修改和更新的默认方式不是“直接在 GitHub 仓库里边想边改”，而是：

**workspace 开发 → staging 整理与检查 → GitHub 仓库同步**

这套流程的核心价值是：
- 不影响当前 local-private 真实实例的使用；
- 不把 workspace 脏数据带入 GitHub 仓库；
- 让 sample / docs / core / runtime 的更新长期保持低摩擦；
- 为未来正式 plugin 发布保留平滑演进路径。


## 12. 路径变量约定

为降低 handoff 摩擦，本文档默认使用以下占位写法：

- `<workspace-root>`：真实开发 workspace 根目录
- `<staging-repo>`：用于发布整理的 staging 仓库目录
- `<local-private-instance>`：本地真实实例目录

若需要给出作者机器示例，应明确标注为 `author-local example`，不要把作者本机路径写成模板默认路径。
