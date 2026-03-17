#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_orchestrator_watcher as watcher


class ProjectOrchestratorWatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.watch_root = self.root / 'runtime' / 'project_orchestrator' / 'watchers'
        self.watch_root.mkdir(parents=True, exist_ok=True)
        self.patchers = [mock.patch.object(watcher, 'WATCH_ROOT', self.watch_root)]
        for p in self.patchers:
            p.start()

    def tearDown(self) -> None:
        for p in reversed(self.patchers):
            p.stop()
        self.tmp.cleanup()

    def test_start_writes_state(self) -> None:
        with mock.patch.object(watcher.inst, 'get_registry_entry', return_value={'agentId': 'pa-sample'}), \
             mock.patch.object(watcher.inst, 'load_project_config', return_value={'projectId': 'sample-project', 'projectSlug': 'sample-project', 'tmuxSession': 'codex_sample'}), \
             mock.patch.object(watcher.tools, 'task_get', return_value={'task': {'codexSession': {'sessionId': 'codex_sample_sample-003'}}}), \
             mock.patch.object(watcher, 'run', return_value=mock.Mock(returncode=0)):
            result = watcher.watcher_start(agent_id='pa-sample', task_id='SAMPLE-003')
        self.assertTrue(result['success'])
        self.assertTrue((self.watch_root / 'pa-sample.active_task.json').exists())
        saved = json.loads((self.watch_root / 'pa-sample.active_task.json').read_text(encoding='utf-8'))
        self.assertIn('lastWakeMarker', saved)

    def test_tick_auto_stops_on_review(self) -> None:
        state = {
            'agentId': 'pa-sample', 'projectId': 'sample-project', 'projectSlug': 'sample-project', 'taskId': 'SAMPLE-003', 'active': True
        }
        (self.watch_root / 'pa-sample.active_task.json').write_text(json.dumps(state), encoding='utf-8')
        with mock.patch.object(watcher.tools, 'task_get', return_value={'task': {'stage': 'review'}}), \
             mock.patch.object(watcher.inst, 'get_registry_entry', return_value={'agentId': 'pa-sample'}), \
             mock.patch.object(watcher.inst, 'load_project_config', return_value={'projectSlug': 'sample-project', 'tmuxSession': 'codex_sample'}), \
             mock.patch.object(watcher, 'watcher_stop', return_value={'success': True}):
            result = watcher.watcher_tick(agent_id='pa-sample')
        self.assertEqual(result['stage'], 'review')
        self.assertTrue(result['stopped'])
        self.assertEqual(result['decision'], 'terminal_stage')

    def test_tick_wakes_agent_even_when_still_running(self) -> None:
        state = {
            'agentId': 'pa-sample', 'projectId': 'sample-project', 'projectSlug': 'sample-project', 'taskId': 'SAMPLE-003', 'active': True, 'lastWakeMarker': ''
        }
        (self.watch_root / 'pa-sample.active_task.json').write_text(json.dumps(state), encoding='utf-8')
        with mock.patch.object(watcher.tools, 'task_get', return_value={'task': {'stage': 'codex_run'}}), \
             mock.patch.object(watcher.inst, 'get_registry_entry', return_value={'agentId': 'pa-sample'}), \
             mock.patch.object(watcher.inst, 'load_project_config', return_value={'projectSlug': 'sample-project', 'tmuxSession': 'codex_sample'}), \
             mock.patch.object(watcher.inst.runner.executor, 'read_project_env', return_value={'TMUX_SESSION': 'codex_sample'}), \
             mock.patch.object(watcher.inst.runner.executor, 'tmux_session_exists', return_value=True), \
             mock.patch.object(watcher.inst.runner.executor, 'capture_tmux_pane', return_value='working...'), \
             mock.patch.object(watcher.inst.runner.executor, 'parse_codex_snapshot', return_value={'ready_for_review': False, 'resume_id': None, 'token_usage_line': None, 'prompt_visible': False, 'snapshot_tail': 'working...'}), \
             mock.patch.object(watcher, 'wake_coordinator', return_value={'ok': True}):
            result = watcher.watcher_tick(agent_id='pa-sample')
        self.assertEqual(result['stage'], 'codex_run')
        self.assertFalse(result['stopped'])
        self.assertEqual(result['decision'], 'wake_agent')

    def test_tick_wakes_agent_when_signal_is_ready(self) -> None:
        state = {
            'agentId': 'pa-sample', 'projectId': 'sample-project', 'projectSlug': 'sample-project', 'taskId': 'SAMPLE-003', 'active': True, 'lastWakeMarker': ''
        }
        (self.watch_root / 'pa-sample.active_task.json').write_text(json.dumps(state), encoding='utf-8')
        with mock.patch.object(watcher.tools, 'task_get', return_value={'task': {'stage': 'codex_run'}}), \
             mock.patch.object(watcher.inst, 'get_registry_entry', return_value={'agentId': 'pa-sample'}), \
             mock.patch.object(watcher.inst, 'load_project_config', return_value={'projectSlug': 'sample-project', 'tmuxSession': 'codex_sample'}), \
             mock.patch.object(watcher.inst.runner.executor, 'read_project_env', return_value={'TMUX_SESSION': 'codex_sample'}), \
             mock.patch.object(watcher.inst.runner.executor, 'tmux_session_exists', return_value=True), \
             mock.patch.object(watcher.inst.runner.executor, 'capture_tmux_pane', return_value='done'), \
             mock.patch.object(watcher.inst.runner.executor, 'parse_codex_snapshot', return_value={'ready_for_review': True, 'resume_id': 'abc', 'token_usage_line': None, 'prompt_visible': True, 'snapshot_tail': 'done'}), \
             mock.patch.object(watcher, 'wake_coordinator', return_value={'ok': True}):
            result = watcher.watcher_tick(agent_id='pa-sample')
        self.assertEqual(result['decision'], 'wake_agent')
        self.assertFalse(result['stopped'])


if __name__ == '__main__':
    unittest.main()
