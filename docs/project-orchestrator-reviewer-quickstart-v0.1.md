# Project Orchestrator Reviewer Quickstart v0.1

本文档用途：给第一次打开这个仓库的协作者一条最短阅读路径。

## 这是什么

这是 `project-orchestrator` 的 **private preview / internal beta** 仓库。

你现在看到的是一个整理后的发布镜像，不是作者日常开发的完整 workspace，也不是一个开箱即用的公共安装包。

## 先不要默认假设的事

- 不要默认它能离开 OpenClaw / tmux / codex / Feishu 环境直接运行
- 不要默认 sample instance 就是生产实例
- 不要默认作者机器的本地路径是模板默认路径

## 最短阅读顺序

1. `README.md`
2. `docs/project-orchestrator-implementation-status-v0.1.md`
3. `docs/project-orchestrator-github-packaging-plan-v0.1.md`
4. `docs/project-orchestrator-public-ready-gap-review-v0.1.md`
5. `project-orchestrator/component-manifest.json`
6. `project-orchestrator/projects/pa-sample/project.json`

## 如果你只想做只读验证

在仓库根目录执行：

```bash
python scripts/release_check.py
```

它会检查：
- sample/docs 关键文件是否存在
- `.gitignore` / `.ignore` 是否对齐
- manifest 关键路径是否存在
- 是否误带真实实例标识
- phase1 结构检查与核心测试是否通过

## 现在最值得关注的点

如果你是协作者，当前最该看的不是“能不能装”，而是：

- 仓库边界是否清楚
- sample 与 local-private 是否分层
- runtime contract 是否开始从作者机器解绑
- 更新流程是否已经被文档化和脚本化

## 当前仓库最准确的定位

一句话：

> 它已经是一个可持续迭代的 private preview，
> 但还不是一个可直接移交陌生维护者接手的 public-ready template。
