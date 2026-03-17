#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import project_orchestrator_task_tools as tools

WORKSPACE_ROOT = Path('/root/.openclaw/workspace-coordinator')
CODEX_ENV_DIR = Path('/etc/openclaw/codex')
CODEX_WORKER_BIN = Path('/usr/local/bin/codex-worker-run')
CODEX_BIN = 'codex'


class ExecutorError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def read_project_env(project_slug: str) -> dict[str, str]:
    env_file = CODEX_ENV_DIR / f'{project_slug}.env'
    if not env_file.exists():
        raise ExecutorError(f'project env not found: {env_file}')
    values: dict[str, str] = {}
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def tmux_session_exists(session_name: str) -> bool:
    p = subprocess.run(['tmux', 'has-session', '-t', session_name], capture_output=True, text=True)
    return p.returncode == 0


def capture_tmux_pane(session_name: str, lines: int = 120) -> str:
    p = subprocess.run(['tmux', 'capture-pane', '-t', f'{session_name}:0.0', '-p'], capture_output=True, text=True, check=True)
    text = p.stdout
    if lines <= 0:
        return text
    split = text.splitlines()
    return '\n'.join(split[-lines:])


def send_tmux_text(session_name: str, text: str, submit: bool = True) -> None:
    subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0.0', '-l', '--', text], check=True)
    time.sleep(0.1)
    if submit:
        subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0.0', 'Enter'], check=True)


def wait_for_codex_prompt(session_name: str, timeout_s: float = 20.0, poll_s: float = 0.25) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    last = {'ready_for_review': False, 'resume_id': None, 'token_usage_line': None, 'prompt_visible': False, 'snapshot_tail': ''}
    while time.time() < deadline:
        if tmux_session_exists(session_name):
            snap = parse_codex_snapshot(capture_tmux_pane(session_name))
            last = snap
            if snap.get('prompt_visible'):
                return {'ok': True, 'snapshot': snap}
        time.sleep(poll_s)
    return {'ok': False, 'snapshot': last}


def reset_tmux_context(session_name: str) -> None:
    subprocess.run(['tmux', 'send-keys', '-t', f'{session_name}:0.0', 'Escape'], check=True)
    time.sleep(0.1)
    send_tmux_text(session_name, '/new', submit=True)
    time.sleep(0.3)


def parse_codex_snapshot(snapshot: str) -> dict[str, Any]:
    lines = [line.rstrip() for line in snapshot.splitlines()]
    joined = '\n'.join(lines)
    lower = joined.lower()
    ready_for_review = (
        'ready for coordinator review: yes' in lower
        or 'coordinator-ready completion summary' in lower
        or 'ready for coordinator review' in lower
        or 'requested completion summary was written into the tmux pane' in lower
        or 'create-game complete:' in lower
    )
    resume_match = re.search(r'codex resume ([a-f0-9\-]+)', joined)
    resume_id = resume_match.group(1) if resume_match else None
    token_line = next((line.strip() for line in reversed(lines) if line.strip().startswith('Token usage:')), None)
    prompt_visible = any(line.strip().startswith('› ') for line in lines)
    return {
        'ready_for_review': ready_for_review,
        'resume_id': resume_id,
        'token_usage_line': token_line,
        'prompt_visible': prompt_visible,
        'snapshot_tail': '\n'.join(lines[-40:]),
    }


def _fake_codex_session(task_id: str) -> dict[str, Any]:
    return {
        'executor': 'fake-codex',
        'sessionId': f'fake-{task_id}',
        'status': 'finished',
        'startedAt': now_iso(),
        'endedAt': now_iso(),
        'logPath': None,
        'summaryPath': f'artifacts/{task_id}/codex-summary.md',
    }


def start_fake_run(*, project_id: str, task_id: str) -> dict[str, Any]:
    session = _fake_codex_session(task_id)
    tools.set_codex_session(projectId=project_id, taskId=task_id, session=session)
    return session


def sync_fake_run_record(*, project_id: str, task_id: str) -> dict[str, Any]:
    task = tools.task_get(projectId=project_id, taskId=task_id)['task']
    session = task.get('codexSession')
    if not session:
        session = start_fake_run(project_id=project_id, task_id=task_id)
    if not task['artifacts']['codexRunRecord']:
        tools.inject_artifact(projectId=project_id, taskId=task_id, artifactName='codexRunRecord', summary='fake codex run record ready')
    return session


def collect_fake_outputs(*, project_id: str, task_id: str) -> dict[str, Any]:
    task = tools.task_get(projectId=project_id, taskId=task_id)['task']
    if not task['artifacts']['codexSummary']:
        tools.inject_artifact(projectId=project_id, taskId=task_id, artifactName='codexSummary', summary='fake codex summary ready')
    if not task['artifacts']['testResult']:
        tools.inject_artifact(projectId=project_id, taskId=task_id, artifactName='testResult', summary='fake test result ready')
    return tools.task_get(projectId=project_id, taskId=task_id)['task']['artifacts']


def _tmux_run_record(*, project_slug: str, task_id: str, env: dict[str, str], status: str, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    record = {
        'executor': 'tmux-codex',
        'sessionId': env.get('TMUX_SESSION', f'codex_{project_slug}'),
        'status': status,
        'startedAt': now_iso(),
        'endedAt': None if status == 'running' else now_iso(),
        'logPath': env.get('CODEX_LOG') or env.get('LOG_DIR'),
        'summaryPath': f'artifacts/{task_id}/codex-summary.md',
    }
    if snapshot:
        record['resumeId'] = snapshot.get('resume_id')
        record['tokenUsageLine'] = snapshot.get('token_usage_line')
    return record


def start_tmux_run(*, project_id: str, task_id: str, project_slug: str, session_name: str | None = None, log_path: str | None = None, clean_start: bool = False) -> dict[str, Any]:
    env = read_project_env(project_slug)
    session_name = session_name or env.get('TMUX_SESSION', f'codex_{project_slug}')
    log_path = log_path or env.get('CODEX_LOG') or str(Path(env.get('LOG_DIR', f'/var/log/openclaw-codex/{project_slug}')) / f'{task_id}.log')
    if not tmux_session_exists(session_name):
        if clean_start:
            workdir = env.get('WORKDIR')
            model = env.get('CODEX_MODEL', 'gpt-5.4')
            reasoning = env.get('CODEX_REASONING', 'high')
            full_access = env.get('CODEX_FULL_ACCESS', 'true') == 'true'
            cmd = f"cd {workdir} && HOME=/root GH_CONFIG_DIR=/root/.config/gh {CODEX_BIN} --no-alt-screen -m {model} -c model_reasoning_effort=\"{reasoning}\""
            if full_access:
                cmd += ' --dangerously-bypass-approvals-and-sandbox'
            subprocess.run(['tmux', 'new-session', '-d', '-s', session_name, cmd], check=True)
        else:
            subprocess.run(['tmux', 'new-session', '-d', '-s', session_name, f"/usr/local/bin/codex-launcher '{project_slug}'"], check=True)
        subprocess.run(['tmux', 'pipe-pane', '-t', f'{session_name}:0.0', '-o', f"cat >> '{log_path}'"], check=True)
    status = 'running' if tmux_session_exists(session_name) else 'failed'
    snapshot = parse_codex_snapshot(capture_tmux_pane(session_name)) if status == 'running' else None
    session = _tmux_run_record(project_slug=project_slug, task_id=task_id, env=env, status=status, snapshot=snapshot)
    session['sessionId'] = session_name
    session['logPath'] = log_path
    tools.set_codex_session(projectId=project_id, taskId=task_id, session=session)
    return session


def submit_tmux_prompt(*, project_id: str, task_id: str, project_slug: str, prompt: str, reset_context: bool = False, session_name: str | None = None, log_path: str | None = None, clean_start: bool = False) -> dict[str, Any]:
    env = read_project_env(project_slug)
    session_name = session_name or env.get('TMUX_SESSION', f'codex_{project_slug}')
    if not tmux_session_exists(session_name):
        start_tmux_run(project_id=project_id, task_id=task_id, project_slug=project_slug, session_name=session_name, log_path=log_path, clean_start=clean_start)
    wait_for_codex_prompt(session_name)
    if reset_context:
        reset_tmux_context(session_name)
        wait_for_codex_prompt(session_name)
    send_tmux_text(session_name, prompt, submit=True)
    time.sleep(0.3)
    snapshot = parse_codex_snapshot(capture_tmux_pane(session_name))
    session = _tmux_run_record(project_slug=project_slug, task_id=task_id, env=env, status='running', snapshot=snapshot)
    session['sessionId'] = session_name
    if log_path:
        session['logPath'] = log_path
    session['lastPrompt'] = prompt
    tools.set_codex_session(projectId=project_id, taskId=task_id, session=session)
    return session


def sync_tmux_run_record(*, project_id: str, task_id: str, project_slug: str) -> dict[str, Any]:
    task = tools.task_get(projectId=project_id, taskId=task_id)['task']
    session = task.get('codexSession')
    if not session:
        session = start_tmux_run(project_id=project_id, task_id=task_id, project_slug=project_slug)
    session_name = session['sessionId']
    is_running = tmux_session_exists(session_name)
    snapshot_raw = capture_tmux_pane(session_name) if is_running else ''
    snapshot = parse_codex_snapshot(snapshot_raw) if snapshot_raw else None
    session = dict(session)
    session['status'] = 'running' if is_running else ('finished' if task['artifacts']['codexRunRecord'] else 'failed')
    session['endedAt'] = None if is_running else now_iso()
    if snapshot:
        session['resumeId'] = snapshot.get('resume_id')
        session['tokenUsageLine'] = snapshot.get('token_usage_line')
        session['snapshotTail'] = snapshot.get('snapshot_tail')
    tools.set_codex_session(projectId=project_id, taskId=task_id, session=session)
    if snapshot and snapshot.get('ready_for_review') and not task['artifacts']['codexRunRecord']:
        summary = 'tmux codex run record ready'
        if snapshot.get('resume_id'):
            summary += f" | resume={snapshot['resume_id']}"
        tools.inject_artifact(projectId=project_id, taskId=task_id, artifactName='codexRunRecord', summary=summary)
    elif not is_running and not task['artifacts']['codexRunRecord']:
        tools.inject_artifact(projectId=project_id, taskId=task_id, artifactName='codexRunRecord', summary='tmux codex run record ready (session exited)')
    return session


def collect_tmux_outputs(*, project_id: str, task_id: str, project_slug: str) -> dict[str, Any]:
    task = tools.task_get(projectId=project_id, taskId=task_id)['task']
    env = read_project_env(project_slug)
    session = task.get('codexSession') or {}
    snapshot_tail = session.get('snapshotTail') or ''
    token_usage = session.get('tokenUsageLine') or 'token-usage-unavailable'
    if not task['artifacts']['codexSummary']:
        summary = f'tmux codex summary from {env.get("CODEX_LOG", "log")}'
        if snapshot_tail:
            summary += f' | snapshot captured'
        tools.inject_artifact(projectId=project_id, taskId=task_id, artifactName='codexSummary', summary=summary)
    if not task['artifacts']['testResult']:
        summary = 'tmux test/result signal unavailable in this prototype'
        if token_usage:
            summary += f' | {token_usage}'
        tools.inject_artifact(projectId=project_id, taskId=task_id, artifactName='testResult', summary=summary)
    return tools.task_get(projectId=project_id, taskId=task_id)['task']['artifacts']
