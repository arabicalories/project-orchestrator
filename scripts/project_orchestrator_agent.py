#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

import project_orchestrator_executor as executor
import project_orchestrator_task_tools as tools


def _get_project_instance_runner(project_id: str, executor_mode: str = 'none'):
    try:
        import project_orchestrator_instance_runner as instance_runner
        instance_runner.get_registry_entry(project_id=project_id)
        return instance_runner
    except Exception:
        return None


def _try_advance_via_project_agent(*, project_id: str, task_id: str, executor_mode: str = 'none') -> dict[str, Any] | None:
    instance_runner = _get_project_instance_runner(project_id=project_id, executor_mode=executor_mode)
    if instance_runner is None:
        return None
    result = instance_runner.advance_task(project_id=project_id, task_id=task_id)
    task = tools.task_get(projectId=project_id, taskId=task_id)['task']
    return {
        'taskId': task_id,
        'fromStage': task['history'][-1].get('fromStage') if task.get('history') else task['stage'],
        'decision': {'action': 'project-agent-advance', 'projectId': project_id},
        'result': result,
    }


def run_one_cycle(*, project_id: str, task_id: str, executor_mode: str = 'none', **_: Any) -> dict[str, Any]:
    delegated = _try_advance_via_project_agent(project_id=project_id, task_id=task_id, executor_mode=executor_mode)
    if delegated is not None:
        return delegated
    task = tools.task_get(projectId=project_id, taskId=task_id)['task']
    return {
        'taskId': task_id,
        'fromStage': task['stage'],
        'decision': {'action': 'stop', 'reason': 'no registered project-agent flow available'},
        'result': {'success': False, 'error': 'NO_PROJECT_AGENT_FLOW', 'projectId': project_id},
    }


def run_until_pause_or_done(*, project_id: str, task_id: str, executor_mode: str = 'none', max_steps: int = 30, **_: Any) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    instance_runner = _get_project_instance_runner(project_id=project_id, executor_mode=executor_mode)
    if instance_runner is None:
        latest = tools.task_get(projectId=project_id, taskId=task_id)['task']
        return {
            'taskId': task_id,
            'finalStage': latest['stage'],
            'steps': steps,
            'error': 'NO_PROJECT_AGENT_FLOW',
            'projectId': project_id,
        }
    for _ in range(max_steps):
        result = instance_runner.advance_task(project_id=project_id, task_id=task_id)
        latest = tools.task_get(projectId=project_id, taskId=task_id)['task']
        steps.append({
            'taskId': task_id,
            'fromStage': latest['history'][-1].get('fromStage') if latest.get('history') else latest['stage'],
            'decision': {'action': 'project-agent-advance', 'projectId': project_id},
            'result': result,
        })
        if latest['stage'] in {'await_user_approval', 'await_user_decision', 'done', 'blocked', 'failed'}:
            return {'taskId': task_id, 'finalStage': latest['stage'], 'steps': steps}
    latest = tools.task_get(projectId=project_id, taskId=task_id)['task']
    return {'taskId': task_id, 'finalStage': latest['stage'], 'steps': steps, 'warning': 'max_steps reached'}


def cmd_inspect_tmux(args: argparse.Namespace) -> None:
    payload = executor.read_project_env(args.project_slug, env_file=args.env_file)
    payload['tmux_session_exists'] = executor.tmux_session_exists(payload.get('TMUX_SESSION', f'codex_{args.project_slug}'))
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description='Project orchestrator shell / dispatch runner')
    sub = parser.add_subparsers(dest='cmd', required=True)

    inspect = sub.add_parser('inspect-tmux')
    inspect.add_argument('--project-slug', required=True)
    inspect.add_argument('--env-file')
    inspect.set_defaults(func=cmd_inspect_tmux)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
