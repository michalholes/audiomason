import importlib.util
from pathlib import Path


def _load_sync_module():
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "sync_issues_archive.py"
    spec = importlib.util.spec_from_file_location("sync_issues_archive", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sync = _load_sync_module()


def _issue(n, state, closedAt=None, body='BODY', title=None):
    return {
        'number': n,
        'title': title or f'T{n}',
        'state': state,
        'labels': [],
        'assignees': [],
        'milestone': None,
        'createdAt': '2020-01-01T00:00:00Z',
        'updatedAt': '2020-01-02T00:00:00Z',
        'closedAt': closedAt,
        'body': body,
    }


def test_ordering_open_ascending():
    issues = [_issue(3, 'OPEN'), _issue(1, 'OPEN'), _issue(2, 'OPEN')]
    open_issues, closed_issues = sync.split_and_sort(issues)
    assert [i['number'] for i in open_issues] == [1, 2, 3]
    assert closed_issues == []


def test_ordering_closed_desc_by_closedAt_then_number():
    issues = [
        _issue(1, 'CLOSED', closedAt='2020-01-03T00:00:00Z'),
        _issue(2, 'CLOSED', closedAt='2020-01-04T00:00:00Z'),
        _issue(3, 'CLOSED', closedAt='2020-01-04T00:00:00Z'),
    ]
    open_issues, closed_issues = sync.split_and_sort(issues)
    assert open_issues == []
    assert [i['number'] for i in closed_issues] == [3, 2, 1]


def test_rendering_stability_byte_identical():
    issues = [_issue(1, 'OPEN', body='Hello\n\nWorld')]
    a = sync.render_archive('Open Issues', issues)
    b = sync.render_archive('Open Issues', issues)
    assert a == b
    assert a.endswith('\n')
