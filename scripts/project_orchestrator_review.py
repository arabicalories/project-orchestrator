#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import project_orchestrator_instance_runner as inst
import project_orchestrator_task_tools as tools

ROOT = Path('/root/.openclaw/workspace-coordinator')


def run_git_diff(repo_path: str) -> str:
    p = subprocess.run(['git', 'diff', '--stat'], cwd=repo_path, capture_output=True, text=True, check=True)
    return p.stdout.strip()


def count_fixback_rounds(task: dict[str, Any]) -> int:
    rounds = 0
    for entry in task.get('history', []):
        if entry.get('toStage') == 'fixback':
            rounds += 1
    return rounds


def build_review_summary(task: dict[str, Any], repo_path: str) -> tuple[str, str]:
    diff_stat = run_git_diff(repo_path)
    codex_summary = (task.get('artifacts', {}).get('codexSummary') or {}).get('summary', '')
    test_result = (task.get('artifacts', {}).get('testResult') or {}).get('summary', '')

    lines = [
        f"Task: {task['id']}",
        f"Title: {task['title']}",
        "",
        "Evidence:",
        f"- codexSummary: {codex_summary}",
        f"- testResult: {test_result}",
        "",
        "Git diff stat:",
        diff_stat or '(no diff stat)',
    ]

    decision = 'pr_ready'
    if not task.get('artifacts', {}).get('codexSummary'):
        decision = 'fixback'
    elif 'unrelated' in test_result.lower() or 'pre-existing' in test_result.lower():
        decision = 'pr_ready'
    elif not diff_stat:
        decision = 'need-user-decision'

    if decision == 'fixback' and count_fixback_rounds(task) >= 3:
        decision = 'need-user-decision'
        lines.extend([
            '',
            'Escalation:',
            '- review/fixback discussion exceeded 3 rounds without consensus',
            '- escalate to user decision',
        ])

    return decision, '\n'.join(lines)


def run_review(*, agent_id: str | None = None, project_id: str | None = None, task_id: str) -> dict[str, Any]:
    entry, config = inst._resolve_instance(agent_id, project_id)
    project_id_value = config['projectId']
    task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
    if task['stage'] != 'review':
        return {'success': False, 'error': 'INVALID_STAGE', 'stage': task['stage']}

    decision, review_text = build_review_summary(task, config['repoPath'])
    tools.inject_artifact(projectId=project_id_value, taskId=task_id, artifactName='review', summary=f'review decision: {decision}')
    tools.task_append_note(projectId=project_id_value, taskId=task_id, noteType='review-note', content=review_text)

    if decision == 'pr_ready':
        result = tools.task_transition(projectId=project_id_value, taskId=task_id, targetStage='pr_ready', reason='review passed and ready for next delivery step')
    elif decision == 'fixback':
        result = tools.task_transition(projectId=project_id_value, taskId=task_id, targetStage='fixback', reason='review requests additional fixes')
    else:
        tools.task_mark_need_user_decision(projectId=project_id_value, taskId=task_id, decisionKind='result-decision', reason='review requires user decision')
        result = tools.task_transition(projectId=project_id_value, taskId=task_id, targetStage='await_user_decision', reason='review needs user decision')

    task = tools.task_get(projectId=project_id_value, taskId=task_id)['task']
    return {
        'success': result.get('success', False),
        'decision': decision,
        'task': task,
        'reviewSummary': review_text,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Project orchestrator review executor')
    parser.add_argument('--agent-id')
    parser.add_argument('--project-id')
    parser.add_argument('--task-id', required=True)
    args = parser.parse_args()
    result = run_review(agent_id=args.agent_id, project_id=args.project_id, task_id=args.task_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
