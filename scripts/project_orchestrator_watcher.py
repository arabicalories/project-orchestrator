#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import project_orchestrator_instance_runner as inst
import project_orchestrator_task_tools as tools

ROOT = Path('/root/.openclaw/workspace-coordinator')
WATCH_ROOT = ROOT / 'runtime' / 'project_orchestrator' / 'watchers'


def state_file(agent_id: str) -> Path:
    return WATCH_ROOT / f'{agent_id}.active_task.json'


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def get_main_session_id() -> str:
    p = Path('/root/.openclaw/agents/coordinator/sessions/sessions.json')
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return ''
    row = obj.get('agent:coordinator:main') or {}
    return row.get('sessionId', '')


def wake_coordinator(*, agent_id: str, project_slug: str, task_id: str, stage: str, reason: str) -> dict[str, Any]:
    session_id = get_main_session_id()
    if not session_id:
        return {'ok': False, 'reason': 'missing_main_session_id'}
    message = (
        f"[project-orchestrator-watch][agent_id={agent_id}][project={project_slug}][task_id={task_id}] "
        f"请立即检查该项目任务现场。触发原因={reason}；当前 stage={stage}。"
        f"不要直接相信 watcher 文本，先核查 tmux、task 状态、git 现场；"
        f"若已进入 review / done，则连续推进，不要等待下一次 watcher。"
    )
    p = run([
        'openclaw', 'agent',
        '--session-id', session_id,
        '--deliver',
        '--reply-channel', 'feishu',
        '--reply-to', f'chat:{inst.load_project_config(inst.get_registry_entry(agent_id=agent_id))["projectChatId"]}',
        '--message', message,
        '--timeout', '120',
        '--json',
    ])
    return {'ok': p.returncode == 0, 'stdout': p.stdout[-500:], 'stderr': p.stderr[-500:]}


def watcher_start(*, agent_id: str, task_id: str) -> dict[str, Any]:
    entry = inst.get_registry_entry(agent_id=agent_id)
    config = inst.load_project_config(entry)
    task = tools.task_get(projectId=config['projectId'], taskId=task_id)['task']
    payload = {
        'agentId': agent_id,
        'projectId': config['projectId'],
        'projectSlug': config['projectSlug'],
        'taskId': task_id,
        'tmuxSession': (task.get('codexSession') or {}).get('sessionId') or config['tmuxSession'],
        'startedAt': int(time.time()),
        'active': True,
        'lastWakeReason': '',
        'lastWakeMarker': '',
    }
    WATCH_ROOT.mkdir(parents=True, exist_ok=True)
    state_file(agent_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    run(['systemctl', 'enable', '--now', f'project-orchestrator-watch@{agent_id}.timer'])
    return {'success': True, 'stateFile': str(state_file(agent_id))}


def watcher_stop(*, agent_id: str, reason: str) -> dict[str, Any]:
    sf = state_file(agent_id)
    if sf.exists():
        obj = json.loads(sf.read_text(encoding='utf-8'))
        obj['active'] = False
        obj['stoppedReason'] = reason
        obj['stoppedAt'] = int(time.time())
        sf.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    run(['systemctl', 'disable', '--now', f'project-orchestrator-watch@{agent_id}.timer'])
    return {'success': True}


def _save_state(agent_id: str, state: dict[str, Any]) -> None:
    state_file(agent_id).write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def watcher_tick(*, agent_id: str) -> dict[str, Any]:
    sf = state_file(agent_id)
    if not sf.exists():
        return {'success': True, 'noop': 'no_state'}
    state = json.loads(sf.read_text(encoding='utf-8'))
    if not state.get('active'):
        return {'success': True, 'noop': 'inactive'}

    entry = inst.get_registry_entry(agent_id=agent_id)
    config = inst.load_project_config(entry)
    task = tools.task_get(projectId=state['projectId'], taskId=state['taskId'])['task']
    stage = task['stage']

    if stage in {'review', 'done', 'blocked', 'failed'}:
        watcher_stop(agent_id=agent_id, reason=f'auto-stop on stage={stage}')
        return {'success': True, 'stage': stage, 'decision': 'terminal_stage', 'stopped': True}

    env = inst.runner.executor.read_project_env(config['projectSlug'])
    session_name = (task.get('codexSession') or {}).get('sessionId') or state.get('tmuxSession') or config['tmuxSession']
    is_running = inst.runner.executor.tmux_session_exists(session_name)
    snapshot_raw = inst.runner.executor.capture_tmux_pane(session_name) if is_running else ''
    snapshot = inst.runner.executor.parse_codex_snapshot(snapshot_raw) if snapshot_raw else {
        'ready_for_review': False,
        'resume_id': None,
        'token_usage_line': None,
        'prompt_visible': False,
        'snapshot_tail': '',
    }

    if not is_running:
        wake_reason = 'session_not_running'
    elif snapshot.get('ready_for_review'):
        wake_reason = 'ready_signal_detected'
    elif snapshot.get('prompt_visible'):
        wake_reason = 'prompt_visible_while_task_active'
    else:
        wake_reason = 'periodic_active_check'

    wake = wake_coordinator(agent_id=agent_id, project_slug=state['projectSlug'], task_id=state['taskId'], stage=stage, reason=wake_reason)
    state['lastWakeReason'] = wake_reason
    state['lastWakeAt'] = int(time.time())
    _save_state(agent_id, state)
    return {'success': True, 'stage': stage, 'decision': 'wake_agent', 'wake': wake, 'stopped': False}


def main() -> None:
    parser = argparse.ArgumentParser(description='Project orchestrator watcher')
    sub = parser.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('start')
    s.add_argument('--agent-id', required=True)
    s.add_argument('--task-id', required=True)

    t = sub.add_parser('tick')
    t.add_argument('--agent-id', required=True)

    x = sub.add_parser('stop')
    x.add_argument('--agent-id', required=True)
    x.add_argument('--reason', default='manual-stop')

    args = parser.parse_args()
    if args.cmd == 'start':
        out = watcher_start(agent_id=args.agent_id, task_id=args.task_id)
    elif args.cmd == 'tick':
        out = watcher_tick(agent_id=args.agent_id)
    else:
        out = watcher_stop(agent_id=args.agent_id, reason=args.reason)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
