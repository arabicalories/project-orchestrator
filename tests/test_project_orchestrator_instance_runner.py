#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_orchestrator_instance_runner as inst
import project_orchestrator_task_tools as tools


class ProjectOrchestratorInstanceRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state_root = self.root / 'state'
        self.registry_path = self.root / 'project-orchestrator' / 'registry' / 'projects.json'
        self.workspace = self.root / 'project-orchestrator' / 'projects' / 'pa-sample'
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.root / 'repo').mkdir(parents=True, exist_ok=True)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(json.dumps({
            'version': 1,
            'projects': [{
                'projectId': 'sample-project',
                'agentId': 'pa-sample',
                'workspacePath': 'project-orchestrator/projects/pa-sample',
                'runner': 'scripts/project_orchestrator_agent.py',
                'projectSlug': 'sample-project',
                'repoPath': '/path/to/sample-repo',
                'tmuxSession': 'codex_sample',
                'status': 'active-prototype'
            }]
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        (self.workspace / 'project.json').write_text(json.dumps({
            'projectId': 'sample-project',
            'agentId': 'pa-sample',
            'repoId': 'repo-main',
            'projectSlug': 'sample-project',
            'repoPath': str(self.root / 'repo'),
            'tmuxSession': 'codex_sample',
            'resetSessionBeforeSubmit': True
        }, ensure_ascii=False, indent=2), encoding='utf-8')

        self.patchers = [
            mock.patch.object(inst, 'ROOT', self.root),
            mock.patch.object(inst, 'REGISTRY_PATH', self.registry_path),
            mock.patch.object(tools, 'STATE_ROOT', self.state_root),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self) -> None:
        for p in reversed(self.patchers):
            p.stop()
        self.tmp.cleanup()

    def test_get_registry_entry(self) -> None:
        entry = inst.get_registry_entry(agent_id='pa-sample')
        self.assertEqual(entry['projectId'], 'sample-project')

    def test_inspect_instance(self) -> None:
        with mock.patch.object(inst.runner.executor, 'read_project_env', return_value={'TMUX_SESSION': 'codex_sample'}), \
             mock.patch.object(inst.runner.executor, 'tmux_session_exists', return_value=True):
            result = inst.inspect_instance(agent_id='pa-sample')
        self.assertEqual(result['project']['agentId'], 'pa-sample')
        self.assertTrue(result['tmux']['tmux_session_exists'])

    def test_tmux_flow_is_guarded_by_default(self) -> None:
        result = inst.run_agent_demo(agent_id='pa-sample', mode='tmux-flow')
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'REAL_EXECUTOR_DISABLED')

    def test_tmux_flow_can_be_explicitly_allowed(self) -> None:
        with mock.patch.object(inst.runner, 'run_until_pause_or_done', return_value={'finalStage': 'collect'}) as mocked_run:
            result = inst.run_agent_demo(agent_id='pa-sample', mode='tmux-flow', allow_real_executor=True)
        self.assertEqual(result['finalStage'], 'collect')
        mocked_run.assert_called()

    def test_submit_real_task_prepares_repo_branch_and_dispatches_prompt(self) -> None:
        with mock.patch.object(inst, '_prepare_repo_for_task', return_value={'branch': 'feature/SAMPLE-001', 'head': 'abc123'}) as mocked_prepare, \
             mock.patch.object(inst.runner.executor, 'submit_tmux_prompt', return_value={'sessionId': 'codex_sample', 'status': 'running'}) as mocked_submit:
            result = inst.submit_real_task(agent_id='pa-sample', prompt='do a safe test prompt', title='safe test')
        self.assertEqual(result['nextStage'], 'codex_run')
        mocked_prepare.assert_called_once()
        mocked_submit.assert_called()
        self.assertFalse(mocked_submit.call_args.kwargs['reset_context'])
        self.assertTrue(mocked_submit.call_args.kwargs['clean_start'])
        self.assertIn('code_sample-project_sampleproject-001', mocked_submit.call_args.kwargs['session_name'])
        task = tools.task_get(projectId='sample-project', taskId=result['taskId'])['task']
        self.assertEqual(task['repoRef']['branch'], 'feature/SAMPLE-001')

    def test_collect_real_task_advances_to_collect_only(self) -> None:
        with mock.patch.object(inst, '_prepare_repo_for_task', return_value={'branch': 'feature/SAMPLE-001', 'head': 'abc123'}), \
             mock.patch.object(inst.runner.executor, 'submit_tmux_prompt', return_value={'sessionId': 'codex_sample', 'status': 'running'}):
            tid = inst.submit_real_task(agent_id='pa-sample', prompt='collect demo', title='collect demo')['taskId']

        def fake_collect(**kwargs):
            tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexSummary', summary='done')
            tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='testResult', summary='done')
            return tools.task_get(projectId='sample-project', taskId=tid)['task']['artifacts']

        with mock.patch.object(inst.runner.executor, 'sync_tmux_run_record', return_value={'sessionId': 'codex_sample', 'status': 'finished'}), \
             mock.patch.object(inst.runner.executor, 'collect_tmux_outputs', side_effect=fake_collect):
            tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexRunRecord', summary='ready')
            result = inst.collect_real_task(agent_id='pa-sample', task_id=tid)
        self.assertEqual(result['task']['stage'], 'collect')

    def test_advance_task_intake_moves_to_plan(self) -> None:
        init = tools.task_init(projectId='sample-project', repoId='repo-main', title='intake task', goal='goal', constraints=[])
        tid = init['taskId']
        result = inst.advance_task(agent_id='pa-sample', task_id=tid)
        self.assertTrue(result['success'])
        self.assertEqual(result['decision'], 'plan')
        self.assertEqual(result['task']['stage'], 'plan')

    def test_advance_task_plan_generates_artifact_and_moves_to_codex_run(self) -> None:
        init = tools.task_init(projectId='sample-project', repoId='repo-main', title='plan task', goal='goal', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='plan', reason='setup')
        result = inst.advance_task(agent_id='pa-sample', task_id=tid)
        self.assertTrue(result['success'])
        self.assertEqual(result['decision'], 'codex_run')
        self.assertEqual(result['task']['stage'], 'codex_run')
        self.assertIsNotNone(result['task']['artifacts']['plan'])

    def test_advance_task_codex_run_moves_to_collect_when_run_record_ready(self) -> None:
        init = tools.task_init(projectId='sample-project', repoId='repo-main', title='codex task', goal='goal', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='plan', reason='plan')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='plan', summary='plan')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='codex_run', reason='run')
        tools.set_codex_session(projectId='sample-project', taskId=tid, session={'sessionId': 'code_sample_sample-777', 'logPath': '/tmp/codex-run.log'})

        def fake_sync(**kwargs):
            tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexRunRecord', summary='ready')
            return {'sessionId': 'code_sample_sample-777', 'status': 'running'}

        with mock.patch.object(inst.runner.executor, 'sync_tmux_run_record', side_effect=fake_sync):
            result = inst.advance_task(agent_id='pa-sample', task_id=tid)
        self.assertTrue(result['success'])
        self.assertEqual(result['task']['stage'], 'collect')
        self.assertIsNotNone(result['task']['artifacts']['codexRunRecord'])

    def test_advance_task_collect_moves_to_review_when_outputs_ready(self) -> None:
        init = tools.task_init(projectId='sample-project', repoId='repo-main', title='collect task', goal='goal', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='plan', reason='plan')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='plan', summary='plan')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='codex_run', reason='run')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexRunRecord', summary='run')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='collect', reason='collect')

        def fake_collect(**kwargs):
            tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexSummary', summary='summary')
            tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='testResult', summary='done')
            return tools.task_get(projectId='sample-project', taskId=tid)['task']['artifacts']

        with mock.patch.object(inst.runner.executor, 'collect_tmux_outputs', side_effect=fake_collect):
            result = inst.advance_task(agent_id='pa-sample', task_id=tid)
        self.assertTrue(result['success'])
        self.assertEqual(result['task']['stage'], 'review')
        self.assertIsNotNone(result['task']['artifacts']['codexSummary'])

    def test_promote_review_requires_agent_call(self) -> None:
        with mock.patch.object(inst, '_prepare_repo_for_task', return_value={'branch': 'feature/SAMPLE-001', 'head': 'abc123'}), \
             mock.patch.object(inst.runner.executor, 'submit_tmux_prompt', return_value={'sessionId': 'codex_sample', 'status': 'running'}):
            tid = inst.submit_real_task(agent_id='pa-sample', prompt='collect demo', title='collect demo')['taskId']
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexRunRecord', summary='ready')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='collect', reason='manual setup')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexSummary', summary='done')
        result = inst.promote_review(agent_id='pa-sample', task_id=tid)
        self.assertTrue(result['success'])
        self.assertEqual(result['task']['stage'], 'review')

    def test_advance_task_runs_review_executor(self) -> None:
        with mock.patch.object(inst, '_prepare_repo_for_task', return_value={'branch': 'feature/SAMPLE-001', 'head': 'abc123'}), \
             mock.patch.object(inst.runner.executor, 'submit_tmux_prompt', return_value={'sessionId': 'codex_sample', 'status': 'running'}):
            tid = inst.submit_real_task(agent_id='pa-sample', prompt='collect demo', title='collect demo')['taskId']
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexRunRecord', summary='ready')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='collect', reason='manual setup')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexSummary', summary='done')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='testResult', summary='pre-existing unrelated lint issue')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='review', reason='manual review setup')
        with mock.patch('project_orchestrator_review.run_git_diff', return_value=' data/games.json | 10 ++++++++++'):
            result = inst.advance_task(agent_id='pa-sample', task_id=tid)
        self.assertTrue(result['success'])
        self.assertEqual(result['task']['stage'], 'pr_ready')

    def test_advance_task_fixback_returns_to_codex_run(self) -> None:
        init = tools.task_init(projectId='sample-project', repoId='repo-main', title='fixback task', goal='goal', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='plan', reason='plan')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='plan', summary='plan')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='codex_run', reason='run')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexRunRecord', summary='run')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexSummary', summary='summary')
        tools.set_codex_session(projectId='sample-project', taskId=tid, session={'sessionId': 'code_sample_sample-999', 'logPath': '/tmp/fixback.log'})
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='collect', reason='collect')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='review', reason='review')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='review', summary='review decision: fixback')
        tools.task_append_note(projectId='sample-project', taskId=tid, noteType='review-note', content='Please fix the review findings.')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='fixback', reason='review requests fixes')
        with mock.patch.object(inst.runner.executor, 'submit_tmux_prompt', return_value={'sessionId': 'code_sample_sample-999', 'status': 'running'}) as mocked_submit:
            result = inst.advance_task(agent_id='pa-sample', task_id=tid)
        self.assertTrue(result['success'])
        self.assertEqual(result['decision'], 'fixback')
        self.assertEqual(result['task']['stage'], 'codex_run')
        self.assertIn('Please fix the review findings.', result['fixbackPrompt'])
        self.assertIn('you may reject specific suggestions', result['fixbackPrompt'])
        self.assertEqual(result['round'], 2)
        mocked_submit.assert_called_once()


    def test_advance_task_pr_ready_executes_pr_delivery_and_closes_to_done(self) -> None:
        init = tools.task_init(projectId='sample-project', repoId='repo-main', title='pr ready task', goal='goal', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='plan', reason='plan')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='plan', summary='plan')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='codex_run', reason='run')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexRunRecord', summary='run')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='collect', reason='collect')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexSummary', summary='summary')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='review', reason='review')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='review', summary='review decision: pr_ready')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='pr_ready', reason='review passed')
        with mock.patch.object(inst, '_submit_pr_delivery', return_value={'branch': 'feature/SAMPLE-001', 'prUrl': 'https://github.com/example/repo/pull/1', 'commit': 'abc123', 'noop': False}) as mocked_delivery:
            result = inst.advance_task(agent_id='pa-sample', task_id=tid)
        self.assertTrue(result['success'])
        self.assertEqual(result['decision'], 'done')
        self.assertEqual(result['task']['stage'], 'done')
        self.assertEqual(result['task']['deliveryClosure']['kind'], 'pr-opened')
        self.assertIn('/pull/1', result['task']['deliveryClosure']['detail'])
        mocked_delivery.assert_called_once()

    def test_advance_task_waits_on_user_decision(self) -> None:
        init = tools.task_init(projectId='sample-project', repoId='repo-main', title='decision task', goal='goal', constraints=[])
        tid = init['taskId']
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='plan', reason='plan')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='plan', summary='plan')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='codex_run', reason='run')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexRunRecord', summary='run')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='collect', reason='collect')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='codexSummary', summary='summary')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='review', reason='review')
        tools.inject_artifact(projectId='sample-project', taskId=tid, artifactName='review', summary='review decision: need-user-decision')
        tools.task_mark_need_user_decision(projectId='sample-project', taskId=tid, decisionKind='result-decision', reason='need user choice')
        tools.task_transition(projectId='sample-project', taskId=tid, targetStage='await_user_decision', reason='waiting user')
        result = inst.advance_task(agent_id='pa-sample', task_id=tid)
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'WAITING_USER_DECISION')
        self.assertEqual(result['task']['stage'], 'await_user_decision')


class ProjectOrchestratorExecutorSnapshotTests(unittest.TestCase):
    def test_parse_snapshot_accepts_coordinator_ready_summary(self) -> None:
        import project_orchestrator_executor as ex
        snap = """
        Added Sliding Puzzle ...
        coordinator-ready completion summary was printed to tmux output.
        """
        parsed = ex.parse_codex_snapshot(snap)
        self.assertTrue(parsed['ready_for_review'])


if __name__ == '__main__':
    unittest.main()
