#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_orchestrator_review as review
import project_orchestrator_task_tools as tools
import project_orchestrator_instance_runner as inst


class ProjectOrchestratorReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state_root = self.root / 'state'
        self.workspace = self.root / 'project-orchestrator' / 'projects' / 'pa-sample'
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / 'project.json').write_text(json.dumps({
            'projectId': 'sample-project',
            'agentId': 'pa-sample',
            'repoId': 'repo-main',
            'projectSlug': 'sample-project',
            'repoPath': str(self.root / 'repo')
        }), encoding='utf-8')
        (self.root / 'repo').mkdir(parents=True, exist_ok=True)

        self.patchers = [
            mock.patch.object(inst, 'ROOT', self.root),
            mock.patch.object(tools, 'STATE_ROOT', self.state_root),
            mock.patch.object(inst, 'get_registry_entry', return_value={'agentId': 'pa-sample'}),
            mock.patch.object(inst, 'load_project_config', return_value={
                'projectId': 'sample-project',
                'agentId': 'pa-sample',
                'repoId': 'repo-main',
                'projectSlug': 'sample-project',
                'repoPath': str(self.root / 'repo')
            }),
        ]
        for p in self.patchers:
            p.start()

        init = tools.task_init(projectId='sample-project', repoId='repo-main', title='review task', goal='goal', constraints=[])
        self.task_id = init['taskId']
        tools.task_transition(projectId='sample-project', taskId=self.task_id, targetStage='plan', reason='plan')
        tools.inject_artifact(projectId='sample-project', taskId=self.task_id, artifactName='plan', summary='plan')
        tools.task_transition(projectId='sample-project', taskId=self.task_id, targetStage='codex_run', reason='run')
        tools.inject_artifact(projectId='sample-project', taskId=self.task_id, artifactName='codexRunRecord', summary='run')
        tools.task_transition(projectId='sample-project', taskId=self.task_id, targetStage='collect', reason='collect')
        tools.inject_artifact(projectId='sample-project', taskId=self.task_id, artifactName='codexSummary', summary='summary')
        tools.inject_artifact(projectId='sample-project', taskId=self.task_id, artifactName='testResult', summary='pre-existing unrelated lint issue')
        tools.task_transition(projectId='sample-project', taskId=self.task_id, targetStage='review', reason='review')
        self.assertEqual(tools.task_get(projectId='sample-project', taskId=self.task_id)['task']['stage'], 'review')

    def tearDown(self) -> None:
        for p in reversed(self.patchers):
            p.stop()
        self.tmp.cleanup()

    def test_run_review_advances_to_pr_ready(self) -> None:
        with mock.patch.object(review, 'run_git_diff', return_value=' data/games.json | 10 ++++++++++'):
            result = review.run_review(agent_id='pa-sample', task_id=self.task_id)
        self.assertNotIn('error', result, result)
        self.assertEqual(result['decision'], 'pr_ready')
        self.assertEqual(result['task']['stage'], 'pr_ready')
        self.assertIsNotNone(result['task']['artifacts']['review'])

    def test_build_review_summary_escalates_after_three_fixback_rounds(self) -> None:
        task = tools.task_get(projectId='sample-project', taskId=self.task_id)['task']
        task['artifacts']['codexSummary'] = None
        task['artifacts']['testResult'] = None
        task['history'].extend([
            {'toStage': 'fixback'},
            {'toStage': 'fixback'},
            {'toStage': 'fixback'},
        ])
        with mock.patch.object(review, 'run_git_diff', return_value=' data/games.json | 1 +'):
            decision, summary = review.build_review_summary(task, str(self.root / 'repo'))
        self.assertEqual(decision, 'need-user-decision')
        self.assertIn('exceeded 3 rounds', summary)


if __name__ == '__main__':
    unittest.main()
