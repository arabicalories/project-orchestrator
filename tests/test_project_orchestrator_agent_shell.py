#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_orchestrator_agent as runner
import project_orchestrator_task_tools as tools


class ProjectOrchestratorAgentShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.state_root = Path(self.tmp.name)
        patcher = mock.patch.object(tools, 'STATE_ROOT', self.state_root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.project_id = 'sample-project'

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_run_one_cycle_delegates_registered_project_to_project_agent(self) -> None:
        init = tools.task_init(projectId=self.project_id, repoId='repo-main', title='demo', goal='goal', constraints=[])
        with mock.patch.object(runner, '_try_advance_via_project_agent', return_value={
            'taskId': init['taskId'],
            'fromStage': 'intake',
            'decision': {'action': 'project-agent-advance', 'projectId': self.project_id},
            'result': {'success': True},
        }) as mocked_delegate:
            result = runner.run_one_cycle(project_id=self.project_id, task_id=init['taskId'])
        self.assertEqual(result['decision']['action'], 'project-agent-advance')
        mocked_delegate.assert_called_once_with(project_id=self.project_id, task_id=init['taskId'], executor_mode='none')

    def test_run_until_pause_or_done_uses_project_agent_loop(self) -> None:
        init = tools.task_init(projectId=self.project_id, repoId='repo-main', title='demo', goal='goal', constraints=[])

        class DummyRunner:
            def __init__(self):
                self.calls = 0
            def advance_task(self, project_id: str, task_id: str):
                self.calls += 1
                task = tools.task_get(projectId=project_id, taskId=task_id)['task']
                if task['stage'] == 'intake':
                    return tools.task_transition(projectId=project_id, taskId=task_id, targetStage='plan', reason='delegated')
                if task['stage'] == 'plan':
                    tools.inject_artifact(projectId=project_id, taskId=task_id, artifactName='plan', summary='delegated plan')
                    tools.set_user_decision(projectId=project_id, taskId=task_id, needs=True, kind='approval', reason='delegated approval')
                    return tools.task_transition(projectId=project_id, taskId=task_id, targetStage='await_user_approval', reason='delegated wait')
                return {'success': False}

        dummy = DummyRunner()
        with mock.patch.object(runner, '_get_project_instance_runner', return_value=dummy):
            result = runner.run_until_pause_or_done(project_id=self.project_id, task_id=init['taskId'], max_steps=5)
        self.assertEqual(result['finalStage'], 'await_user_approval')
        self.assertEqual(dummy.calls, 2)

    def test_non_registered_project_has_no_project_agent(self) -> None:
        self.assertIsNone(runner._get_project_instance_runner(project_id='unregistered-project', executor_mode='none'))


if __name__ == '__main__':
    unittest.main()
