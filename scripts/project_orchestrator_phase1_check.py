#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace-coordinator')
BASE = ROOT / 'project-orchestrator'

REQUIRED_WORKSPACE_PATHS = [
    BASE / 'workspace-template/AGENTS.md',
    BASE / 'workspace-template/MEMORY.md',
    BASE / 'workspace-template/skills/README.md',
    BASE / 'workspace-template/docs/README.md',
    BASE / 'workspace-template/specs/README.md',
    BASE / 'workspace-template/samples/README.md',
    BASE / 'workspace-template/notes/README.md',
    BASE / 'workspace-template/reviews/README.md',
]

REQUIRED_STATE_PATHS = [
    BASE / 'state-template/project-state/demo-project/index.json',
    BASE / 'state-template/project-state/demo-project/tasks/README.md',
    BASE / 'state-template/project-state/demo-project/logs/README.md',
    BASE / 'state-template/project-state/demo-project/locks/README.md',
]

TASK_REQUIRED_KEYS = {
    'id', 'projectId', 'repoId', 'title', 'goal', 'constraints', 'stage',
    'needsUserDecision', 'userDecisionKind', 'userDecisionReason',
    'blockedReasonKind', 'deliveryClosure', 'codexSession', 'repoRef',
    'artifacts', 'acceptanceChecks', 'history', 'createdAt', 'updatedAt',
}

ARTIFACT_KEYS = {'plan', 'codexRunRecord', 'codexSummary', 'review', 'testResult'}


class CheckError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def assert_exists(paths: list[Path]) -> None:
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.exists()]
    if missing:
        raise CheckError(f'缺少必要路径: {missing}')


def assert_task_shape(task_path: Path, allowed_stages: set[str]) -> None:
    task = load_json(task_path)
    missing = TASK_REQUIRED_KEYS - task.keys()
    if missing:
        raise CheckError(f'{task_path.name} 缺少字段: {sorted(missing)}')
    extra = task.keys() - TASK_REQUIRED_KEYS
    if extra:
        raise CheckError(f'{task_path.name} 存在未定义字段: {sorted(extra)}')
    if task['stage'] not in allowed_stages:
        raise CheckError(f'{task_path.name} 的 stage 非法: {task["stage"]}')
    repo_ref = task['repoRef']
    for k in ('repoPath', 'branch', 'worktree'):
        if k not in repo_ref:
            raise CheckError(f'{task_path.name} 的 repoRef 缺少 {k}')
    artifacts = task['artifacts']
    if set(artifacts.keys()) != ARTIFACT_KEYS:
        raise CheckError(f'{task_path.name} 的 artifacts 键集合不匹配: {sorted(artifacts.keys())}')


def assert_scenario(scenario_path: Path, allowed: dict[str, list[str]], required_artifacts: dict[str, list[str]]) -> None:
    scenario = load_json(scenario_path)
    flow = scenario['flow']
    if len(flow) < 2:
        raise CheckError(f'{scenario_path.name} 的 flow 太短')
    for current, nxt in zip(flow, flow[1:]):
        legal = allowed.get(current, [])
        if nxt not in legal:
            raise CheckError(f'{scenario_path.name} 中存在非法跳转: {current} -> {nxt}')
    for checkpoint in scenario['checkpoints']:
        stage = checkpoint['currentStage']
        legal_targets = checkpoint['legalTargetStages']
        required_before_enter = checkpoint['requiredArtifactsBeforeEnter']
        expected_missing = checkpoint['expectedMissingArtifacts']
        declared_legal = set(allowed.get(stage, []))
        if not set(legal_targets).issubset(declared_legal):
            raise CheckError(
                f'{scenario_path.name} 中 {stage} 的 legalTargetStages 超出冻结规则: '
                f'{sorted(set(legal_targets) - declared_legal)}'
            )
        frozen_required = required_artifacts.get(stage, [])
        if required_before_enter != frozen_required:
            raise CheckError(
                f'{scenario_path.name} 中 {stage} 的 requiredArtifactsBeforeEnter 与冻结规则不一致: '
                f'{required_before_enter} != {frozen_required}'
            )
        extras = sorted(set(expected_missing) - set(frozen_required))
        if extras:
            raise CheckError(f'{scenario_path.name} 中 {stage} 的 expectedMissingArtifacts 非法: {extras}')


def main() -> None:
    assert_exists(REQUIRED_WORKSPACE_PATHS)
    assert_exists(REQUIRED_STATE_PATHS)

    allowed = load_json(BASE / 'specs/allowed-transitions.json')
    required_artifacts = load_json(BASE / 'specs/stage-required-artifacts.json')
    allowed_stages = set(allowed.keys())

    assert_task_shape(BASE / 'samples/normal-flow/task.json', allowed_stages)
    assert_task_shape(BASE / 'samples/review-fixback/task.json', allowed_stages)

    assert_scenario(BASE / 'samples/normal-flow/scenario.json', allowed, required_artifacts)
    assert_scenario(BASE / 'samples/review-fixback/scenario.json', allowed, required_artifacts)

    print('OK: phase 1 skeleton is structurally consistent')


if __name__ == '__main__':
    main()
