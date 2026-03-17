#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path('/root/.openclaw/workspace-coordinator')
SPEC_DIR = ROOT / 'project-orchestrator' / 'specs'
STATE_ROOT = ROOT / 'runtime' / 'project_orchestrator_state'

ALLOWED_TRANSITIONS = json.loads((SPEC_DIR / 'allowed-transitions.json').read_text(encoding='utf-8'))
STAGE_REQUIRED_ARTIFACTS = json.loads((SPEC_DIR / 'stage-required-artifacts.json').read_text(encoding='utf-8'))
TASK_SCHEMA = json.loads((SPEC_DIR / 'task.schema.json').read_text(encoding='utf-8'))
STAGES = set(ALLOWED_TRANSITIONS.keys())
VALID_CHECK_TYPES = {'transition-readiness', 'artifact-completeness', 'consistency'}
USER_DECISION_STAGES = {'await_user_approval', 'await_user_decision'}
RECOVERABLE_STAGES_FROM_BLOCKED = {'plan', 'await_user_approval', 'codex_run'}


class TaskToolError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'message': self.message, 'details': self.details}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def project_state_dir(project_id: str) -> Path:
    return STATE_ROOT / project_id


def tasks_dir(project_id: str) -> Path:
    return project_state_dir(project_id) / 'tasks'


def logs_dir(project_id: str) -> Path:
    return project_state_dir(project_id) / 'logs'


def locks_dir(project_id: str) -> Path:
    return project_state_dir(project_id) / 'locks'


def task_file(project_id: str, task_id: str) -> Path:
    return tasks_dir(project_id) / f'{task_id}.json'


def index_file(project_id: str) -> Path:
    return project_state_dir(project_id) / 'index.json'


def ensure_project_state(project_id: str) -> None:
    for path in (tasks_dir(project_id), logs_dir(project_id), locks_dir(project_id)):
        path.mkdir(parents=True, exist_ok=True)
    idx = index_file(project_id)
    if not idx.exists():
        _atomic_write_json(idx, {
            'projectId': project_id,
            'version': 1,
            'taskCount': 0,
            'tasks': [],
            'updatedAt': now_iso(),
        })


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as tf:
        json.dump(payload, tf, ensure_ascii=False, indent=2)
        tf.write('\n')
        temp_name = tf.name
    Path(temp_name).replace(path)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _artifact_ref(kind: str, task_id: str, summary: str) -> dict[str, str]:
    return {
        'type': kind,
        'path': f'artifacts/{task_id}/{kind}.md',
        'summary': summary,
        'updatedAt': now_iso(),
    }


def _next_task_id(project_id: str) -> str:
    idx = _load_json(index_file(project_id))
    prefix = ''.join(ch for ch in project_id.upper() if ch.isalnum()) or 'TASK'
    number = int(idx.get('taskCount', 0)) + 1
    return f'{prefix}-{number:03d}'


def _initial_task(project_id: str, repo_id: str, title: str, goal: str, constraints: list[str], task_id: str) -> dict[str, Any]:
    ts = now_iso()
    return {
        'id': task_id,
        'projectId': project_id,
        'repoId': repo_id,
        'title': title,
        'goal': goal,
        'constraints': constraints,
        'stage': 'intake',
        'needsUserDecision': False,
        'userDecisionKind': None,
        'userDecisionReason': '',
        'blockedReasonKind': None,
        'deliveryClosure': None,
        'codexSession': None,
        'repoRef': {
            'repoPath': f'/repos/{project_id}',
            'branch': f'feature/{task_id}',
            'worktree': None,
        },
        'artifacts': {
            'plan': None,
            'codexRunRecord': None,
            'codexSummary': None,
            'review': None,
            'testResult': None,
        },
        'acceptanceChecks': [],
        'history': [
            {
                'timestamp': ts,
                'actor': 'tool:task_init',
                'action': 'create',
                'fromStage': None,
                'toStage': 'intake',
                'reason': 'task initialized',
                'changedFieldsSummary': ['stage', 'createdAt', 'updatedAt'],
            }
        ],
        'createdAt': ts,
        'updatedAt': ts,
    }


def _update_index_on_create(project_id: str, task_id: str) -> None:
    idx_path = index_file(project_id)
    idx = _load_json(idx_path)
    tasks = list(idx.get('tasks', []))
    tasks.append(task_id)
    idx['tasks'] = tasks
    idx['taskCount'] = len(tasks)
    idx['updatedAt'] = now_iso()
    _atomic_write_json(idx_path, idx)


def _validate_minimal_task_shape(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(TASK_SCHEMA['required'])
    missing = sorted(required - set(task.keys()))
    if missing:
        errors.append(f'missing required fields: {missing}')
        return errors
    if task.get('stage') not in STAGES:
        errors.append(f"invalid stage: {task.get('stage')}")
    artifacts = task.get('artifacts', {})
    expected_artifacts = set(TASK_SCHEMA['properties']['artifacts']['required'])
    if set(artifacts.keys()) != expected_artifacts:
        errors.append(f'invalid artifacts keys: {sorted(artifacts.keys())}')
    repo_ref = task.get('repoRef', {})
    for key in ('repoPath', 'branch', 'worktree'):
        if key not in repo_ref:
            errors.append(f'missing repoRef.{key}')
    if not isinstance(task.get('history'), list):
        errors.append('history must be a list')
    return errors


def _load_task_or_raise(project_id: str, task_id: str) -> dict[str, Any]:
    path = task_file(project_id, task_id)
    if not path.exists():
        raise TaskToolError('TASK_NOT_FOUND', f'task {task_id} not found', details={'taskId': task_id, 'projectId': project_id})
    task = _load_json(path)
    shape_errors = _validate_minimal_task_shape(task)
    if shape_errors:
        raise TaskToolError('TASK_INVALID', 'task file shape is invalid', details={'errors': shape_errors, 'taskId': task_id})
    return task


def task_init(*, projectId: str, repoId: str, title: str, goal: str, constraints: list[str]) -> dict[str, Any]:
    ensure_project_state(projectId)
    task_id = _next_task_id(projectId)
    task = _initial_task(projectId, repoId, title, goal, constraints, task_id)
    path = task_file(projectId, task_id)
    if path.exists():
        raise TaskToolError('TASK_ALREADY_EXISTS', f'task {task_id} already exists', details={'taskId': task_id})
    _atomic_write_json(path, task)
    _update_index_on_create(projectId, task_id)
    return {
        'taskId': task_id,
        'stage': 'intake',
        'taskPath': str(path),
    }


def task_get(*, projectId: str, taskId: str) -> dict[str, Any]:
    task = _load_task_or_raise(projectId, taskId)
    return {'task': task}


def _check_artifacts_for_stage(task: dict[str, Any], stage: str) -> list[str]:
    required = STAGE_REQUIRED_ARTIFACTS.get(stage, [])
    artifacts = task.get('artifacts', {})
    return [name for name in required if not artifacts.get(name)]


def _check_user_decision_binding(task: dict[str, Any], target_stage: str) -> list[str]:
    errors: list[str] = []
    if target_stage == 'await_user_approval':
        if task.get('needsUserDecision') is not True:
            errors.append('await_user_approval requires needsUserDecision=true')
        if task.get('userDecisionKind') != 'approval':
            errors.append('await_user_approval requires userDecisionKind=approval')
    elif target_stage == 'await_user_decision':
        if task.get('needsUserDecision') is not True:
            errors.append('await_user_decision requires needsUserDecision=true')
        if task.get('userDecisionKind') not in {'result-decision', 'direction-choice', 'other'}:
            errors.append('await_user_decision requires a valid result-side userDecisionKind')
    return errors


def _check_done_closure(task: dict[str, Any]) -> list[str]:
    closure = task.get('deliveryClosure')
    if not closure:
        return ['done requires deliveryClosure']
    missing = [k for k in ('kind', 'detail', 'closedAt') if not closure.get(k)]
    if missing:
        return [f'deliveryClosure missing fields: {missing}']
    return []


def _latest_recoverable_stage_before_blocked(task: dict[str, Any]) -> str | None:
    history = task.get('history', [])
    for entry in reversed(history):
        to_stage = entry.get('toStage')
        if to_stage == 'blocked':
            previous = entry.get('fromStage')
            if previous in RECOVERABLE_STAGES_FROM_BLOCKED:
                return previous
            return None
        if to_stage in RECOVERABLE_STAGES_FROM_BLOCKED:
            return to_stage
    return None


def _check_blocked_recovery(task: dict[str, Any], target_stage: str) -> list[str]:
    errors: list[str] = []
    if task.get('stage') != 'blocked':
        return errors
    if target_stage == 'failed':
        return errors
    if target_stage not in RECOVERABLE_STAGES_FROM_BLOCKED:
        errors.append(f'blocked can only recover to {sorted(RECOVERABLE_STAGES_FROM_BLOCKED)} or failed')
        return errors
    recoverable = _latest_recoverable_stage_before_blocked(task)
    if recoverable is None and target_stage != 'plan':
        errors.append('blocked without recovery basis can only recover to plan')
    elif recoverable is not None and target_stage != recoverable:
        errors.append(f'blocked can only recover to previous recoverable stage: {recoverable}')
    return errors


def task_check(*, projectId: str, taskId: str, targetStage: str | None, checkType: str) -> dict[str, Any]:
    if checkType not in VALID_CHECK_TYPES:
        raise TaskToolError('INVALID_CHECK_TYPE', f'unsupported checkType: {checkType}', details={'checkType': checkType})
    task = _load_task_or_raise(projectId, taskId)

    errors: list[str] = []
    warnings: list[str] = []
    missing_artifacts: list[str] = []

    if checkType in {'consistency', 'artifact-completeness'}:
        current_missing = _check_artifacts_for_stage(task, task['stage'])
        missing_artifacts.extend(current_missing)
        if current_missing:
            warnings.append(f"current stage {task['stage']} missing artifacts: {current_missing}")
        if task['stage'] in USER_DECISION_STAGES and task.get('needsUserDecision') is not True:
            errors.append(f"{task['stage']} requires needsUserDecision=true")

    if checkType in {'consistency', 'transition-readiness'} and targetStage is not None:
        if targetStage not in STAGES:
            errors.append(f'invalid targetStage: {targetStage}')
        else:
            current_stage = task['stage']
            legal_targets = ALLOWED_TRANSITIONS.get(current_stage, [])
            if targetStage not in legal_targets:
                errors.append(f'illegal transition: {current_stage} -> {targetStage}')
            target_missing = _check_artifacts_for_stage(task, targetStage)
            missing_artifacts.extend(x for x in target_missing if x not in missing_artifacts)
            if target_missing:
                errors.append(f'target stage {targetStage} missing artifacts: {target_missing}')
            errors.extend(_check_user_decision_binding(task, targetStage))
            if targetStage == 'done':
                errors.extend(_check_done_closure(task))
            errors.extend(_check_blocked_recovery(task, targetStage))

    return {
        'passed': not errors,
        'errors': errors,
        'warnings': warnings,
        'missingArtifacts': missing_artifacts,
    }


def _transition_history_entry(from_stage: str, to_stage: str, reason: str) -> dict[str, Any]:
    return {
        'timestamp': now_iso(),
        'actor': 'tool:task_transition',
        'action': 'transition',
        'fromStage': from_stage,
        'toStage': to_stage,
        'reason': reason,
        'changedFieldsSummary': ['stage', 'updatedAt'],
    }


def task_transition(*, projectId: str, taskId: str, targetStage: str, reason: str) -> dict[str, Any]:
    check = task_check(projectId=projectId, taskId=taskId, targetStage=targetStage, checkType='transition-readiness')
    if not check['passed']:
        return {
            'success': False,
            'fromStage': task_get(projectId=projectId, taskId=taskId)['task']['stage'],
            'toStage': targetStage,
            'errors': check['errors'],
        }

    task = _load_task_or_raise(projectId, taskId)
    updated = copy.deepcopy(task)
    from_stage = task['stage']
    updated['stage'] = targetStage
    updated['updatedAt'] = now_iso()

    if from_stage in USER_DECISION_STAGES and targetStage != from_stage:
        updated['needsUserDecision'] = False
        updated['userDecisionReason'] = ''
        updated['userDecisionKind'] = None

    updated['history'].append(_transition_history_entry(from_stage, targetStage, reason))
    _atomic_write_json(task_file(projectId, taskId), updated)

    return {
        'success': True,
        'fromStage': from_stage,
        'toStage': targetStage,
        'errors': [],
    }


# Test helpers kept intentionally small for phase 2.
def inject_artifact(*, projectId: str, taskId: str, artifactName: str, summary: str | None = None) -> None:
    task = _load_task_or_raise(projectId, taskId)
    if artifactName not in task['artifacts']:
        raise TaskToolError('INVALID_ARTIFACT', f'unknown artifact: {artifactName}', details={'artifactName': artifactName})
    task['artifacts'][artifactName] = _artifact_ref(artifactName, taskId, summary or f'{artifactName} ready')
    task['updatedAt'] = now_iso()
    _atomic_write_json(task_file(projectId, taskId), task)


def set_codex_session(*, projectId: str, taskId: str, session: dict[str, Any] | None) -> None:
    task = _load_task_or_raise(projectId, taskId)
    task['codexSession'] = session
    task['updatedAt'] = now_iso()
    _atomic_write_json(task_file(projectId, taskId), task)


def task_mark_need_user_decision(*, projectId: str, taskId: str, decisionKind: str, reason: str) -> dict[str, Any]:
    if decisionKind not in {'approval', 'result-decision', 'direction-choice', 'other'}:
        raise TaskToolError('INVALID_DECISION_KIND', f'unsupported decisionKind: {decisionKind}', details={'decisionKind': decisionKind})
    task = _load_task_or_raise(projectId, taskId)
    task['needsUserDecision'] = True
    task['userDecisionKind'] = decisionKind
    task['userDecisionReason'] = reason
    task['updatedAt'] = now_iso()
    task['history'].append({
        'timestamp': now_iso(),
        'actor': 'tool:task_mark_need_user_decision',
        'action': 'mark_need_user_decision',
        'fromStage': task['stage'],
        'toStage': task['stage'],
        'reason': reason,
        'changedFieldsSummary': ['needsUserDecision', 'userDecisionKind', 'userDecisionReason', 'updatedAt'],
    })
    _atomic_write_json(task_file(projectId, taskId), task)
    return {'success': True}


def task_append_note(*, projectId: str, taskId: str, noteType: str, content: str) -> dict[str, Any]:
    task = _load_task_or_raise(projectId, taskId)
    notes_path = logs_dir(projectId) / f'{taskId}.notes.jsonl'
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        'timestamp': now_iso(),
        'taskId': taskId,
        'projectId': projectId,
        'noteType': noteType,
        'content': content,
    }
    with notes_path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    if noteType in {'review-note', 'ops-note'}:
        task['history'].append({
            'timestamp': now_iso(),
            'actor': 'tool:task_append_note',
            'action': 'append_note',
            'fromStage': task['stage'],
            'toStage': task['stage'],
            'reason': noteType,
            'changedFieldsSummary': ['notes'],
        })
        task['updatedAt'] = now_iso()
        _atomic_write_json(task_file(projectId, taskId), task)
    return {'success': True, 'notePath': str(notes_path)}


def set_user_decision(*, projectId: str, taskId: str, needs: bool, kind: str | None, reason: str) -> None:
    task = _load_task_or_raise(projectId, taskId)
    task['needsUserDecision'] = needs
    task['userDecisionKind'] = kind
    task['userDecisionReason'] = reason
    task['updatedAt'] = now_iso()
    _atomic_write_json(task_file(projectId, taskId), task)


def set_delivery_closure(*, projectId: str, taskId: str, kind: str, detail: str) -> None:
    task = _load_task_or_raise(projectId, taskId)
    task['deliveryClosure'] = {
        'kind': kind,
        'detail': detail,
        'closedAt': now_iso(),
    }
    task['updatedAt'] = now_iso()
    _atomic_write_json(task_file(projectId, taskId), task)


def mark_blocked(*, projectId: str, taskId: str, blockedReasonKind: str, fromStage: str) -> None:
    task = _load_task_or_raise(projectId, taskId)
    task['blockedReasonKind'] = blockedReasonKind
    task['stage'] = 'blocked'
    task['updatedAt'] = now_iso()
    task['history'].append({
        'timestamp': now_iso(),
        'actor': 'system',
        'action': 'transition',
        'fromStage': fromStage,
        'toStage': 'blocked',
        'reason': blockedReasonKind,
        'changedFieldsSummary': ['stage', 'blockedReasonKind', 'updatedAt'],
    })
    _atomic_write_json(task_file(projectId, taskId), task)
