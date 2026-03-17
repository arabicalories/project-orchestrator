# Instance Notes

## 目的
`pa-sample` 用于说明一个项目实例的最小文件结构与配置形态，不用于承接真实项目。

## 设计边界
本示例实例：
- 使用占位 `projectId / agentId / repoPath / tmuxSession / messageTarget`；
- 不持有真实 open_id、chat_id、repo 路径、env 文件路径；
- 不作为真实运行真相源；
- 不与任何 local-private 真实实例共享职责。

## review 阶段语义（继承通用语义）
- `review` 是讨论/收敛阶段，不是单向强制接受阶段；
- `fixback` 表示当前讨论结论是“请 Codex 再改一轮”；
- `await_user_decision` 表示讨论无法继续自动收敛，需要用户介入。

## runtime 说明
- watcher、自动 PR、review card 等能力在真实环境中属于 runtime adapter 能力；
- `pa-sample` 不把这些能力当成默认承诺；
- 若要在真实环境运行，应通过 local-private override 注入真实配置。
