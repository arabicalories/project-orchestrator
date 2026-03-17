# pa-sample

这是 `project-orchestrator` 在 GitHub 私有内测仓库中的**最小示例实例**。

它的职责不是承接真实项目，而是说明：
- 一个项目 agent 实例的目录大致长什么样；
- 最小 `project.json` 应包含哪些字段；
- 示例实例与真实实例应该如何分层。

## 当前定位
- **示例实例，不是真实项目实例**
- **使用占位值，不包含真实环境信息**
- **不要求直接跑通真实任务流**

## 当前接线（示例）
- sample project config：`project-orchestrator/projects/pa-sample/project.json`
- shell / dispatch runner：`scripts/project_orchestrator_agent.py`
- project agent runner：`scripts/project_orchestrator_instance_runner.py`

## 当前不承诺
- 不承诺开箱即用跑通真实 repo
- 不承诺包含真实 Feishu / tmux / GitHub 环境配置
- 不承诺已经接通 cron / review card / watcher 默认路径

## 说明
如果要接入真实项目，应在本地环境中基于此结构创建 **local-private 实例**，并使用真实覆盖配置替换占位值，而不是直接修改本示例文件承载生产配置。
