"""Regression coverage for stale dashboard publications and session selection."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import published_data


class PublishedDataTests(unittest.TestCase):
    def test_retains_last_successful_snapshot_during_fetch_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'index_wari_snapshot.json').write_text(json.dumps({'captured_at': '2026-11-13', 'sessions': []}))
            state = {}
            newer = {'captured_at': '2026-11-17', 'sessions': []}
            with patch.object(published_data, 'DATA', Path(directory)), patch.object(published_data.st, 'session_state', state):
                with patch.object(published_data, '_remote', return_value=newer):
                    self.assertEqual(published_data.load('index_wari_snapshot.json'), newer)
                with patch.object(published_data, '_remote', side_effect=OSError('temporary failure')):
                    self.assertEqual(published_data.load('index_wari_snapshot.json'), newer)

    def test_new_session_selected_but_history_remains_browsable(self):
        code = f'''import sys
sys.path.insert(0, {str(ROOT)!r})
import published_data, streamlit as st
dates=st.session_state.get('dates',['2026-11-13'])
published_data.latest_session('Session',dates,'session')
'''
        app = AppTest.from_string(code).run()
        app.session_state['dates'] = ['2026-11-13', '2026-11-17']
        app.run()
        self.assertEqual(app.selectbox[0].value, '2026-11-17')
        app.selectbox[0].set_value('2026-11-13').run()
        self.assertEqual(app.selectbox[0].value, '2026-11-13')


if __name__ == '__main__':
    unittest.main()
