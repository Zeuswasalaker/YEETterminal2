"""Read published dashboard summaries without waiting for a host rebuild."""
import json
import time
import urllib.request
from pathlib import Path
import streamlit as st

DATA = Path(__file__).parent / 'data'
ALLOWED = {'index_wari_snapshot.json', 'orange_swan_summary.json',
           'meme_swan.json', 'snapshot.json', 'founders.json', 'prestige.json',
           'whispers.json', 'whispers_candidates.json', 'refresh_status.json'}


@st.cache_data(ttl=30, show_spinner=False)
def _remote(filename):
    if filename not in ALLOWED:
        raise ValueError('Unknown dashboard file')
    url = ('https://raw.githubusercontent.com/Zeuswasalaker/YEETterminal2/main/data/'
           + filename + '?v=' + str(int(time.time() // 30)))
    request = urllib.request.Request(url, headers={'User-Agent': 'YEET-Terminal/1.0'})
    with urllib.request.urlopen(request, timeout=5) as response:
        raw = response.read(10_000_001)
    if len(raw) > 10_000_000:
        raise ValueError('Dashboard file is too large')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Dashboard file must be an object')
    return value


def revision(value):
    fields = ('published_at', 'captured_at', 'checked_at', 'flow_imported_at')
    return max((str(value.get(k, '')) for k in fields), default='')


def load(filename):
    if filename not in ALLOWED:
        raise ValueError('Unknown dashboard file')
    local = json.loads((DATA / filename).read_text())
    try:
        remote = _remote(filename)
        chosen = remote if revision(remote) > revision(local) else local
    except (OSError, ValueError, TypeError):
        chosen = local
    # Preserve the last successful publication through a temporary fetch failure.
    key = '_published_' + filename
    previous = st.session_state.get(key)
    if isinstance(previous, dict) and revision(previous) > revision(chosen):
        chosen = previous
    st.session_state[key] = chosen
    return chosen


def latest_session(label, dates, key):
    """Follow newly published sessions while allowing deliberate history browsing."""
    newest = dates[-1]
    marker = key + '_latest_available'
    if st.session_state.get(marker) != newest:
        st.session_state[key] = newest
        st.session_state[marker] = newest
    return st.selectbox(label, dates, key=key)
