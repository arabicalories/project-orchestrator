# Project Orchestrator Public-Ready Gap Review v0.1

本文档用途：对当前 `project-orchestrator` 私有预览仓库做一次 **future public template** 方向的轻量审视，给出 `P0 / P1 / P2` 差距与最小修复建议。

这不是阻塞当前 private preview 继续使用的 gate，而是帮助后续按更稳的顺序收口。

---

```yaml
round: 1
review_mode: full
delta_scope: "n/a"
scenario: handoff
scope: "staging 仓库从 private preview 演进到 future public template 的差距"
summary: "当前仓库已经足够支撑 private preview：边界更清楚、sample 面成立、发布前检查也已接入。但如果把目标提高到 future public template，主要风险不在功能能不能跑，而在 handoff 是否成立：别人拿到仓库后，能否理解哪些是 runtime 假设、哪些是 sample 契约、哪些路径仍然只对作者机器成立。当前最大的断层集中在硬编码环境假设、文档/清单的少量漂移，以及缺少面向外部复用者的最小启动路径。"
findings:
  - severity: P0
    pattern: "runtime assumptions still hard-coded"
    why_here: "如果未来把它当模板交给另一台机器或另一个维护者，当前 runtime 脚本里的作者机器路径和 OpenClaw 约束会让 handoff 失败，且失败方式很像‘仓库看起来完整，但一跑就碎’。"
    evidence: "scripts/project_orchestrator_executor.py 中仍写死 /root/.openclaw/workspace-coordinator、/etc/openclaw/codex、/usr/local/bin/codex-worker-run；scripts/project_orchestrator_instance_runner.py 也固定 ROOT=/root/.openclaw/workspace-coordinator。"
    minimal_fix: "先不重构大架构，只把这批硬编码收口成显式 runtime config / env contract，并在 sample 文档里说明哪些值必须由本地覆盖提供。"
    impact_if_unfixed: "future public template 一旦离开作者机器，很可能直接不可迁移，或者让接手者误以为仓库支持跨环境复用。"
    mvf_steps:
      - "抽出最小运行时契约：WORKSPACE_ROOT、CODEX_ENV_DIR、CODEX_WORKER_BIN、OPENCLAW_RUNTIME_MODE。"
      - "让脚本优先读 env / config，保留当前默认值仅作为 private-preview fallback。"
      - "在 sample README 或 docs 中新增一节 runtime prerequisites，明确哪些不是开箱即用。"
    effort: M

  - severity: P1
    pattern: "manifest and real tree drift"
    why_here: "组件清单一旦和真实目录不一致，后续 handoff 会出现‘文档说 A，仓库实际是 B’的低级摩擦。"
    evidence: "component-manifest.json 里的测试路径仍指向 scripts/test_project_orchestrator_*.py，而当前仓库测试实际位于 tests/test_project_orchestrator_*.py。"
    minimal_fix: "把 component-manifest.json 的测试组件路径改成 tests/ 现状，并把 release_check 扩展为检查 manifest 中列出的关键路径是否真实存在。"

  - severity: P1
    pattern: "machine-local commands exposed in shared docs"
    why_here: "当前 README / SOP 已适合作者自己使用，但如果未来给其他人看，文档里的绝对路径会把‘你的维护路径’误写成‘模板默认路径’。"
    evidence: "README.md 与 docs/project-orchestrator-update-workflow-sop-v0.1.md 中仍直接写 /root/projects/staging/project-orchestrator-private 与 /root/.openclaw/workspace-coordinator。"
    minimal_fix: "把正文主路径改成变量化写法（如 <staging-repo>、<workspace-root>），把当前机器路径放到‘author local example’或脚注。"

  - severity: P1
    pattern: "public entrypoint still unclear"
    why_here: "现在仓库解释了它不是成品，但还没给未来复用者一个非常短的‘如果你只是想看/跑 sample，该从哪里开始’路径。"
    evidence: "README 已有 recommended reading order，但缺少面向外部复用者的 quickstart / prerequisites / supported scope。"
    minimal_fix: "补一个很短的 Quickstart for reviewers：先读哪几个文件、能跑哪条只读检查、哪些能力暂时不要尝试。"

  - severity: P2
    pattern: "docs naming still anchored in private-preview phase"
    why_here: "文档名与版本号目前够内部用，但等仓库继续长大后，implementation-status / packaging-plan / update-workflow 三件套会越来越像维护日志，而不是对外结构化文档。"
    evidence: "当前 docs 以 v0.1 内测语义为主，缺少面向 future public template 的单独总览页。"
    minimal_fix: "后续增加一份更稳的 docs index / architecture map，把‘现状文档’和‘对外阅读入口’分开。"

priority_actions:
  - "先做 P0：把 runtime 硬编码环境假设抽成最小 config / env contract。"
  - "再做低成本高收益的 P1：修 component-manifest 路径漂移，并让 release_check 校验 manifest 关键路径。"
  - "最后补一页 reviewer quickstart，把作者本机路径从主文案里降级为示例。"
decision_hint: revise_first
```

---

## 我对当前状态的判断

如果目标还是 **private preview / internal beta**，当前仓库已经够用了，而且继续迭代问题不大。

但如果目标改成 **future public template**，我不建议直接宣称“已经差不多了”。更准确的说法应该是：

- **结构边界已经基本成形**；
- **样例面已经成立**；
- **发布前检查已经有最小自动化**；
- 但 **runtime 可迁移性** 和 **外部 handoff 体验** 还没收口。

也就是说，现在最像的是：

> 一个整理得越来越像模板的 private preview，
> 而不是一个已经可以交给陌生维护者直接接手的 public-ready template。

---

## 建议的下一阶段顺序

### P0：先修运行时契约
目标：让仓库不再默认绑定作者机器。

建议收口：
- 统一 env/config 入口；
- sample 只保留占位值；
- runtime adapter 明示依赖 OpenClaw / tmux / codex / Feishu 的位置。

### P1：再修 handoff 摩擦
目标：让仓库内的说明、清单、目录彼此一致。

建议收口：
- 修 `component-manifest.json` 路径漂移；
- release_check 增加 manifest 关键路径校验；
- 文档主文案中的作者机器绝对路径变量化。

### P2：最后修对外阅读体验
目标：让未来协作者第一次打开仓库时不迷路。

建议收口：
- 增加 `docs/index` 或 architecture overview；
- 加 reviewer quickstart；
- 区分“当前现状文档”和“未来对外入口文档”。

---

## 一句话结论

**当前仓库已经适合继续做 private preview，但离 future public template 还差一层“可迁移 runtime 契约 + 低摩擦 handoff 文档”。**
