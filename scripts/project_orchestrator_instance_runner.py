#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import project_orchestrator_agent as runner
import project_orchestrator_task_tools as tools
import project_orchestrator_watcher as watcher

DEFAULT_ROOT = Path(os.environ.get('PROJECT_ORCHESTRATOR_WORKSPACE_ROOT', '/root/.openclaw/workspace-coordinator'))
ROOT = DEFAULT_ROOT
REGISTRY_PATH = Path(os.environ.get('PROJECT_ORCHESTRATOR_REGISTRY_PATH', str(ROOT / 'project-orchestrator' / 'registry' / 'projects.json')))


def load_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or REGISTRY_PATH
    return json.loads(registry_path.read_text(encoding='utf-8'))


def get_registry_entry(*, agent_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
    registry = load_registry()
    for entry in registry.get('projects', []):
        if agent_id and entry.get('agentId') == agent_id:
            return entry
        if project_id and entry.get('projectId') == project_id:
            return entry
    raise KeyError(f'project not found in registry: agent_id={agent_id}, project_id={project_id}')


def load_project_config(entry: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / entry['workspacePath'] / 'project.json'
    return json.loads(path.read_text(encoding='utf-8'))


def inspect_instance(*, agent_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
    entry = get_registry_entry(agent_id=agent_id, project_id=project_id)
    config = load_project_config(entry)
    tmux_info = json.loads(json.dumps(runner.executor.read_project_env(config['projectSlug'], env_file=config.get('codexEnvFile'))))
    tmux_info['tmux_session_exists'] = runner.executor.tmux_session_exists(config['tmuxSession'])
    tmux_info['real_executor_allowed'] = bool(config.get('allowAutoStartExecutor'))
    return {
        'registry': entry,
        'project': config,
        'tmux': tmux_info,
    }


def _resolve_instance(agent_id: str | None, project_id: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    entry = get_registry_entry(agent_id=agent_id, project_id=project_id)
    config = load_project_config(entry)
    return entry, config


def _load_latest_note(project_id: str, task_id: str, note_type: str) -> dict[str, Any] | None:
    notes_path = tools.logs_dir(project_id) / f'{task_id}.notes.jsonl'
    if not notes_path.exists():
        return None
    latest = None
    for line in notes_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if entry.get('noteType') == note_type:
            latest = entry
    return latest


def count_fixback_rounds(task: dict[str, Any]) -> int:
    rounds = 0
    for entry in task.get('history', []):
        if entry.get('toStage') == 'fixback':
            rounds += 1
    return rounds


def build_fixback_prompt(task: dict[str, Any], round_number: int) -> str:
    project_id_value = task['projectId']
    latest_review_note = _load_latest_note(project_id_value, task['id'], 'review-note')
    review_text = (latest_review_note or {}).get('content') or '(no detailed review note found)'
    review_summary = ((task.get('artifacts') or {}).get('review') or {}).get('summary') or 'review decision: fixback'
    return (
        f"Fixback round {round_number} for task {task['id']} - {task['title']}\n\n"
        "The coordinator review did not accept the current result yet. Treat the items below as review suggestions to address or respond to.\n\n"
        f"Review summary: {review_summary}\n\n"
        "Detailed review feedback:\n"
        f"{review_text}\n\n"
        "Required response behavior:\n"
        "1. If you agree, revise the implementation with minimal scope.\n"
        "2. If you disagree, you may reject specific suggestions, but you must give concrete technical reasons.\n"
        "3. Keep the branch/task context intact.\n"
        "4. When finished, print a coordinator-ready completion summary again in the tmux pane, including what you changed and what you explicitly disagree with (if any)."
    )


def _run_repo_cmd(command: list[str], *, repo_path: str) -> str:
    env = os.environ.copy()
    env['HOME'] = '/root'
    env['GH_CONFIG_DIR'] = '/root/.config/gh'
    result = subprocess.run(command, cwd=repo_path, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result.stdout.strip()


def _prepare_repo_for_task(*, repo_path: str, branch: str) -> dict[str, Any]:
    _run_repo_cmd(['git', 'fetch', '--all', '--prune'], repo_path=repo_path)
    _run_repo_cmd(['git', 'checkout', 'main'], repo_path=repo_path)
    try:
        _run_repo_cmd(['git', 'pull', '--ff-only', 'origin', 'main'], repo_path=repo_path)
    except RuntimeError:
        # tolerate repos without tracking config as long as explicit origin/main works
        pass
    existing = _run_repo_cmd(['git', 'branch', '--list', branch], repo_path=repo_path)
    if existing.strip():
        _run_repo_cmd(['git', 'checkout', branch], repo_path=repo_path)
        _run_repo_cmd(['git', 'reset', '--hard', 'main'], repo_path=repo_path)
    else:
        _run_repo_cmd(['git', 'checkout', '-b', branch], repo_path=repo_path)
    current_branch = _run_repo_cmd(['git', 'branch', '--show-current'], repo_path=repo_path)
    head = _run_repo_cmd(['git', 'rev-parse', 'HEAD'], repo_path=repo_path)
    return {'branch': current_branch, 'head': head}


def _submit_pr_delivery(*, repo_path: str, branch: str, task: dict[str, Any]) -> dict[str, Any]:
    current_branch = _run_repo_cmd(['git', 'branch', '--show-current'], repo_path=repo_path)
    if current_branch != branch:
        existing = _run_repo_cmd(['git', 'branch', '--list', branch], repo_path=repo_path)
        if existing.strip():
            _run_repo_cmd(['git', 'checkout', branch], repo_path=repo_path)
        else:
            _run_repo_cmd(['git', 'checkout', '-b', branch], repo_path=repo_path)
    _run_repo_cmd(['git', 'add', '-A'], repo_path=repo_path)
    status = _run_repo_cmd(['git', 'status', '--short'], repo_path=repo_path)
    if not status.strip():
        pr_url = _run_repo_cmd(['gh', 'pr', 'view', branch, '--json', 'url', '--jq', '.url'], repo_path=repo_path)
        return {'branch': branch, 'prUrl': pr_url, 'commit': None, 'noop': True}
    commit_message = f"feat: {task['title'][0].lower() + task['title'][1:]}"
    _run_repo_cmd(['git', 'commit', '-m', commit_message], repo_path=repo_path)
    commit_sha = _run_repo_cmd(['git', 'rev-parse', 'HEAD'], repo_path=repo_path)
    _run_repo_cmd(['git', 'push', '-u', 'origin', branch], repo_path=repo_path)
    try:
        pr_url = _run_repo_cmd([
            'gh', 'pr', 'create',
            '--base', 'main',
            '--head', branch,
            '--title', task['title'],
            '--body', f"## Summary\n- automated delivery for {task['id']}\n\n## Validation\n- see task artifacts: plan / codexSummary / testResult / review"
        ], repo_path=repo_path)
    except RuntimeError:
        pr_url = _run_repo_cmd(['gh', 'pr', 'view', branch, '--json', 'url', '--jq', '.url'], repo_path=repo_path)
    return {'branch': branch, 'prUrl': pr_url, 'commit': commit_sha, 'noop': False}


def submit_real_task(*, agent_id: str | None = None, project_id: str | None = None, prompt: str, title: str = 'real task', constraints: list[str] | None = None) -> dict[str, Any]:
    entry, config = _resolve_instance(agent_id, project_id)
    project_id_value = config['projectId']
    task = tools.task_init(projectId=project_id_value, repoId=config['repoId'], title=title, goal=prompt, constraints=constraints or ['instance real-task'])
    branch_name = f"feature/{task['taskId']}"
    prep = _prepare_repo_for_task(repo_path=config['repoPath'], branch=branch_name)
    task_data = tools.task_get(projectId=project_id_value, taskId=task['taskId'])['task']
    task_data['repoRef']['branch'] = prep['branch']
    task_data['updatedAt'] = tools.now_iso()
    tools._atomic_write_json(tools.task_file(project_id_value, task['taskId']), task_data)
    tools.task_transition(projectId=project_id_value, taskId=task['taskId'], targetStage='plan', reason='real task bootstrap')
    tools.inject_artifact(projectId=project_id_value, taskId=task['taskId'], artifactName='plan', summary='real task prompt accepted by instance runner after repo sync and branch setup')
    tools.task_transition(projectId=project_id_value, taskId=task['taskId'], targetStage='codex_run', reason='dispatch real task to tmux executor after repo sync and branch setup')
    session_name = f"code_{config['projectSlug']}_{task['taskId'].lower()}"
    log_path = f"/var/log/openclaw-codex/{config['projectSlug']}/{task['taskId'].lower()}.log"
    session = runner.executor.submit_tmux_prompt(
        project_id=project_id_value,
        task_id=task['taskId'],
        project_slug=config['projectSlug'],
        env_file=config.get('codexEnvFile'),
        prompt=prompt,
        reset_context=False,
        session_name=session_name,
        log_path=log_path,
        clean_start=True,
    )
    watch = watcher.watcher_start(agent_id=config['agentId'], task_id=task['taskId'])
    return {
        'taskId': task['taskId'],
        'projectId': project_id_value,
        'agentId': config['agentId'],
        'codexSession': session,
        'watcher': watch,
        'nextStage': 'codex_run',
    }


def collect_real_task(*, agent_id: str | None = None, project_id: str | None = None, task_id: str) -> dict[str, Any]:
    entry, config = _resolve_instance(agent_id, project_id)
    project_id_value = config['projectId']
    session = runner.executor.sync_tmux_run_record(project_id=project_id_value, task_id=task_id, project_slug=config['projectSlug'], env_file=config.get('codexEnvFile'))
    task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
    watcher_stop = None
    if task['artifacts']['codexRunRecord'] and task['stage'] == 'codex_run':
        tools.task_transition(projectId=project_id_value, taskId=task_id, targetStage='collect', reason='run record recovered from tmux snapshot')
        runner.executor.collect_tmux_outputs(project_id=project_id_value, task_id=task_id, project_slug=config['projectSlug'], env_file=config.get('codexEnvFile'))
        task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
    if task['stage'] in {'done', 'blocked', 'failed'}:
        watcher_stop = watcher.watcher_stop(agent_id=config['agentId'], reason=f'collect-real-task reached stage={task["stage"]}')
    return {'task': task, 'codexSession': session, 'watcherStop': watcher_stop}


def promote_review(*, agent_id: str | None = None, project_id: str | None = None, task_id: str, reason: str = 'agent confirmed review readiness') -> dict[str, Any]:
    entry, config = _resolve_instance(agent_id, project_id)
    project_id_value = config['projectId']
    task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
    if task['stage'] != 'collect':
        return {'success': False, 'error': 'INVALID_STAGE', 'stage': task['stage']}
    result = tools.task_transition(projectId=project_id_value, taskId=task_id, targetStage='review', reason=reason)
    task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
    return {'success': result.get('success', False), 'task': task}


def advance_task(*, agent_id: str | None = None, project_id: str | None = None, task_id: str) -> dict[str, Any]:
    entry, config = _resolve_instance(agent_id, project_id)
    project_id_value = config['projectId']
    task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']

    if task['stage'] == 'intake':
        result = tools.task_transition(
            projectId=project_id_value,
            taskId=task_id,
            targetStage='plan',
            reason='advance-task: intake moved to plan',
        )
        advanced = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        return {
            'success': result.get('success', False),
            'decision': 'plan',
            'task': advanced,
            'watcherStop': None,
        }

    if task['stage'] == 'plan':
        if not task['artifacts'].get('plan'):
            tools.inject_artifact(
                projectId=project_id_value,
                taskId=task_id,
                artifactName='plan',
                summary='advance-task: minimal plan artifact generated',
            )
        task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        target_stage = 'await_user_approval' if task.get('needsUserDecision') else 'codex_run'
        reason = 'advance-task: plan requires explicit user approval' if target_stage == 'await_user_approval' else 'advance-task: plan complete, move to codex_run'
        result = tools.task_transition(
            projectId=project_id_value,
            taskId=task_id,
            targetStage=target_stage,
            reason=reason,
        )
        advanced = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        return {
            'success': result.get('success', False),
            'decision': target_stage,
            'task': advanced,
            'watcherStop': None,
        }

    if task['stage'] == 'codex_run':
        codex_session = task.get('codexSession') or {}
        if not codex_session:
            if not config.get('allowAutoStartExecutor'):
                return {
                    'success': False,
                    'error': 'REAL_EXECUTOR_DISABLED',
                    'stage': task['stage'],
                    'reason': 'advance-task cannot auto-start real executor when allowAutoStartExecutor=false',
                }
            session = runner.executor.start_tmux_run(
                project_id=project_id_value,
                task_id=task_id,
                project_slug=config['projectSlug'],
            )
            watcher.watcher_start(agent_id=config['agentId'], task_id=task_id)
        else:
            session = runner.executor.sync_tmux_run_record(
                project_id=project_id_value,
                task_id=task_id,
                project_slug=config['projectSlug'],
            )
        task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        transitioned = None
        if task['artifacts'].get('codexRunRecord') and task['stage'] == 'codex_run':
            transitioned = tools.task_transition(
                projectId=project_id_value,
                taskId=task_id,
                targetStage='collect',
                reason='advance-task: codex run record ready, move to collect',
            )
            task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        return {
            'success': True if transitioned is None else transitioned.get('success', False),
            'decision': task['stage'],
            'task': task,
            'codexSession': session,
            'watcherStop': None,
        }

    if task['stage'] == 'collect':
        runner.executor.collect_tmux_outputs(
            project_id=project_id_value,
            task_id=task_id,
            project_slug=config['projectSlug'],
        )
        task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        transitioned = None
        if task['artifacts'].get('codexSummary') and task['stage'] == 'collect':
            transitioned = tools.task_transition(
                projectId=project_id_value,
                taskId=task_id,
                targetStage='review',
                reason='advance-task: collect completed, move to review',
            )
            task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        return {
            'success': True if transitioned is None else transitioned.get('success', False),
            'decision': task['stage'],
            'task': task,
            'watcherStop': None,
        }

    if task['stage'] == 'review':
        import project_orchestrator_review as review_executor
        result = review_executor.run_review(agent_id=agent_id, project_id=project_id, task_id=task_id)
        advanced = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        if advanced['stage'] in {'pr_ready', 'done', 'blocked', 'failed', 'await_user_decision'}:
            watcher_stop = watcher.watcher_stop(agent_id=config['agentId'], reason=f'advance-task reached stage={advanced["stage"]}')
        else:
            watcher_stop = None
        result['watcherStop'] = watcher_stop
        return result

    if task['stage'] == 'fixback':
        round_number = count_fixback_rounds(task)
        next_round = round_number + 1
        fixback_prompt = build_fixback_prompt(task, next_round)
        codex_session = task.get('codexSession') or {}
        session_name = codex_session.get('sessionId')
        log_path = codex_session.get('logPath')
        session = runner.executor.submit_tmux_prompt(
            project_id=project_id_value,
            task_id=task_id,
            project_slug=config['projectSlug'],
            prompt=fixback_prompt,
            reset_context=False,
            session_name=session_name,
            log_path=log_path,
            clean_start=False,
        )
        tools.task_append_note(
            projectId=project_id_value,
            taskId=task_id,
            noteType='ops-note',
            content=f'advance-task: dispatched fixback round {next_round} to codex and returned task to codex_run',
        )
        result = tools.task_transition(
            projectId=project_id_value,
            taskId=task_id,
            targetStage='codex_run',
            reason=f'advance-task: fixback round {next_round} dispatched and task returned to codex_run',
        )
        advanced = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        return {
            'success': result.get('success', False),
            'decision': 'fixback',
            'task': advanced,
            'fixbackPrompt': fixback_prompt,
            'codexSession': session,
            'round': next_round,
            'watcherStop': None,
        }

    if task['stage'] == 'pr_ready':
        try:
            delivery = _submit_pr_delivery(
                repo_path=config['repoPath'],
                branch=(task.get('repoRef') or {}).get('branch') or f"feature/{task_id}",
                task=task,
            )
        except Exception as exc:
            tools.task_append_note(
                projectId=project_id_value,
                taskId=task_id,
                noteType='ops-note',
                content=f'advance-task: pr delivery failed: {exc}',
            )
            return {
                'success': False,
                'error': 'PR_DELIVERY_FAILED',
                'task': task,
                'reason': str(exc),
                'watcherStop': None,
            }
        pr_url = delivery['prUrl']
        tools.task_append_note(
            projectId=project_id_value,
            taskId=task_id,
            noteType='ops-note',
            content=f'PR created: {pr_url}',
        )
        tools.set_delivery_closure(
            projectId=project_id_value,
            taskId=task_id,
            kind='pr-opened',
            detail=f'PR opened successfully: {pr_url}',
        )
        result = tools.task_transition(
            projectId=project_id_value,
            taskId=task_id,
            targetStage='done',
            reason='advance-task: pr_ready executed commit/push/create PR successfully',
        )
        advanced = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
        watcher_stop = watcher.watcher_stop(agent_id=config['agentId'], reason='advance-task reached stage=done')
        return {
            'success': result.get('success', False),
            'decision': 'done',
            'task': advanced,
            'delivery': delivery,
            'watcherStop': watcher_stop,
        }

    if task['stage'] == 'await_user_decision':
        watcher_stop = watcher.watcher_stop(agent_id=config['agentId'], reason='advance-task waiting for user decision')
        return {
            'success': False,
            'error': 'WAITING_USER_DECISION',
            'decision': 'await_user_decision',
            'task': task,
            'watcherStop': watcher_stop,
        }

    return {'success': False, 'error': 'UNSUPPORTED_STAGE', 'stage': task['stage']}


def run_agent_demo(*, agent_id: str | None = None, project_id: str | None = None, mode: str = 'tmux-flow', review_outcome: str = 'pass', constraints: list[str] | None = None, allow_real_executor: bool = False) -> dict[str, Any]:
    entry, config = _resolve_instance(agent_id, project_id)
    project_id_value = config['projectId']

    if mode == 'tmux-flow':
        if not allow_real_executor and not config.get('allowAutoStartExecutor'):
            return {
                'success': False,
                'error': 'REAL_EXECUTOR_DISABLED',
                'reason': 'instance config does not allow auto starting real tmux executor; pass --allow-real-executor to override explicitly',
                'projectId': project_id_value,
                'agentId': config['agentId'],
            }
        init = tools.task_init(projectId=project_id_value, repoId=config['repoId'], title='instance tmux flow', goal='run instance-bound tmux executor flow', constraints=['instance demo', 'real-executor'])
        return runner.run_until_pause_or_done(project_id=project_id_value, task_id=init['taskId'], executor_mode='tmux', project_slug=config['projectSlug'], max_steps=20)

    raise ValueError(f'unsupported mode: {mode}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Project orchestrator instance runner')
    sub = parser.add_subparsers(dest='cmd', required=True)

    inspect = sub.add_parser('inspect')
    inspect.add_argument('--agent-id')
    inspect.add_argument('--project-id')

    submit = sub.add_parser('submit-real-task')
    submit.add_argument('--agent-id')
    submit.add_argument('--project-id')
    submit.add_argument('--title', default='real task')
    submit.add_argument('--prompt', required=True)
    submit.add_argument('--constraints', nargs='*', default=[])

    collect = sub.add_parser('collect-real-task')
    collect.add_argument('--agent-id')
    collect.add_argument('--project-id')
    collect.add_argument('--task-id', required=True)

    promote = sub.add_parser('promote-review')
    promote.add_argument('--agent-id')
    promote.add_argument('--project-id')
    promote.add_argument('--task-id', required=True)
    promote.add_argument('--reason', default='agent confirmed review readiness')

    advance = sub.add_parser('advance-task')
    advance.add_argument('--agent-id')
    advance.add_argument('--project-id')
    advance.add_argument('--task-id', required=True)

    demo = sub.add_parser('demo')
    demo.add_argument('--agent-id')
    demo.add_argument('--project-id')
    demo.add_argument('--mode', choices=['tmux-flow'], default='tmux-flow')
    demo.add_argument('--review-outcome', choices=['pass', 'fixback', 'need-user-decision'], default='pass')
    demo.add_argument('--constraints', nargs='*', default=[])
    demo.add_argument('--allow-real-executor', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'inspect':
        result = inspect_instance(agent_id=args.agent_id, project_id=args.project_id)
    elif args.cmd == 'submit-real-task':
        result = submit_real_task(agent_id=args.agent_id, project_id=args.project_id, prompt=args.prompt, title=args.title, constraints=args.constraints)
    elif args.cmd == 'collect-real-task':
        result = collect_real_task(agent_id=args.agent_id, project_id=args.project_id, task_id=args.task_id)
    elif args.cmd == 'promote-review':
        result = promote_review(agent_id=args.agent_id, project_id=args.project_id, task_id=args.task_id, reason=args.reason)
    elif args.cmd == 'advance-task':
        result = advance_task(agent_id=args.agent_id, project_id=args.project_id, task_id=args.task_id)
    else:
        result = run_agent_demo(agent_id=args.agent_id, project_id=args.project_id, mode=args.mode, review_outcome=args.review_outcome, constraints=args.constraints, allow_real_executor=args.allow_real_executor)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
