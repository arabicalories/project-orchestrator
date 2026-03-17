#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_orchestrator_task_tools as tools


class ProjectOrchestratorPhase2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name)
        patcher = mock.patch.object(tools, 'STATE_ROOT', self.state_root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.project_id = 'my-saas'

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_task_init_creates_task_and_index(self) -> None:
        result = tools.task_init(
            projectId=self.project_id,
            repoId='repo-main',
            title='修复登录页表单校验问题',
            goal='修复 bug',
            constraints=['必须通过 Codex worker 执行代码修改'],
        )
        self.assertEqual(result['stage'], 'intake')
        task_path = Path(result['taskPath'])
        self.assertTrue(task_path.exists())

        task = json.loads(task_path.read_text(encoding='utf-8'))
        self.assertEqual(task['stage'], 'intake')
        self.assertEqual(task['history'][0]['actor'], 'tool:task_init')

        index = json.loads((self.state_root / self.project_id / 'index.json').read_text(encoding='utf-8'))
        self.assertEqual(index['taskCount'], 1)
        self.assertEqual(index['tasks'], [result['taskId']])

    def test_task_get_is_read_only(self) -> None:
        init = tools.task_init(
            projectId=self.project_id,
            repoId='repo-main',
            title='A',
            goal='B',
            constraints=[],
        )
        task = tools.task_get(projectId=self.project_id, taskId=init['taskId'])['task']
        self.assertEqual(task['id'], init['taskId'])
        self.assertEqual(task['stage'], 'intake')

    def test_task_check_rejects_illegal_transition(self) -> None:
        init = tools.task_init(projectId=self.project_id, repoId='repo-main', title='A', goal='B', constraints=[])
        check = tools.task_check(
            projectId=self.project_id,
            taskId=init['taskId'],
            targetStage='review',
            checkType='transition-readiness',
        )
        self.assertFalse(check['passed'])
        self.assertTrue(any('illegal transition' in err for err in check['errors']))

    def test_task_transition_requires_artifacts(self) -> None:
        init = tools.task_init(projectId=self.project_id, repoId='repo-main', title='A', goal='B', constraints=[])
        tid = init['taskId']
        ok = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='plan', reason='start planning')
        self.assertTrue(ok['success'])

        fail = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='codex_run', reason='run codex')
        self.assertFalse(fail['success'])
        self.assertTrue(any('missing artifacts' in err for err in fail['errors']))

        tools.inject_artifact(projectId=self.project_id, taskId=tid, artifactName='plan')
        ok2 = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='codex_run', reason='run codex')
        self.assertTrue(ok2['success'])

    def test_task_transition_to_await_user_approval_requires_binding(self) -> None:
        init = tools.task_init(projectId=self.project_id, repoId='repo-main', title='A', goal='B', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='plan', reason='start planning')

        fail = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='await_user_approval', reason='need approval')
        self.assertFalse(fail['success'])
        self.assertTrue(any('needsUserDecision=true' in err for err in fail['errors']))

        tools.inject_artifact(projectId=self.project_id, taskId=tid, artifactName='plan')
        tools.set_user_decision(projectId=self.project_id, taskId=tid, needs=True, kind='approval', reason='执行前审批')
        ok = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='await_user_approval', reason='need approval')
        self.assertTrue(ok['success'])

    def test_task_transition_to_done_requires_delivery_closure(self) -> None:
        init = tools.task_init(projectId=self.project_id, repoId='repo-main', title='A', goal='B', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='plan', reason='plan')
        tools.inject_artifact(projectId=self.project_id, taskId=tid, artifactName='plan')
        tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='codex_run', reason='run')
        tools.inject_artifact(projectId=self.project_id, taskId=tid, artifactName='codexRunRecord')
        tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='collect', reason='collect')
        tools.inject_artifact(projectId=self.project_id, taskId=tid, artifactName='codexSummary')
        tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='review', reason='review')
        tools.inject_artifact(projectId=self.project_id, taskId=tid, artifactName='review')
        tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='pr_ready', reason='ready')

        fail = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='done', reason='done')
        self.assertFalse(fail['success'])
        self.assertTrue(any('deliveryClosure' in err for err in fail['errors']))

        tools.set_delivery_closure(projectId=self.project_id, taskId=tid, kind='pr-created', detail='PR opened')
        ok = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='done', reason='done')
        self.assertTrue(ok['success'])

    def test_blocked_without_recovery_basis_only_allows_plan(self) -> None:
        init = tools.task_init(projectId=self.project_id, repoId='repo-main', title='A', goal='B', constraints=[])
        tid = init['taskId']
        tools.mark_blocked(projectId=self.project_id, taskId=tid, blockedReasonKind='missing-info', fromStage='intake')

        fail = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='codex_run', reason='resume')
        self.assertFalse(fail['success'])
        self.assertTrue(any('only recover to plan' in err for err in fail['errors']))

        ok = tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='plan', reason='resume safely')
        self.assertTrue(ok['success'])

    def test_task_transition_writes_history(self) -> None:
        init = tools.task_init(projectId=self.project_id, repoId='repo-main', title='A', goal='B', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId=self.project_id, taskId=tid, targetStage='plan', reason='plan')
        task = tools.task_get(projectId=self.project_id, taskId=tid)['task']
        self.assertEqual(task['history'][-1]['actor'], 'tool:task_transition')
        self.assertEqual(task['history'][-1]['fromStage'], 'intake')
        self.assertEqual(task['history'][-1]['toStage'], 'plan')


if __name__ == '__main__':
    unittest.main()
