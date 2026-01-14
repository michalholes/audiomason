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


def _issue(n, state, closedAt=None, body="BODY", title=None):
    return {
        "number": n,
        "title": title or f"T{n}",
        "state": state,
        "labels": [],
        "assignees": [],
        "milestone": None,
        "createdAt": "2020-01-01T00:00:00Z",
        "updatedAt": "2020-01-02T00:00:00Z",
        "closedAt": closedAt,
        "body": body,
    }


def test_ordering_open_ascending():
    issues = [_issue(3, "OPEN"), _issue(1, "OPEN"), _issue(2, "OPEN")]
    open_issues, closed_issues = sync.split_and_sort(issues)
    assert [i["number"] for i in open_issues] == [1, 2, 3]
    assert closed_issues == []


def test_ordering_closed_desc_by_closedAt_then_number():
    issues = [
        _issue(1, "CLOSED", closedAt="2020-01-03T00:00:00Z"),
        _issue(2, "CLOSED", closedAt="2020-01-04T00:00:00Z"),
        _issue(3, "CLOSED", closedAt="2020-01-04T00:00:00Z"),
    ]
    open_issues, closed_issues = sync.split_and_sort(issues)
    assert open_issues == []
    assert [i["number"] for i in closed_issues] == [3, 2, 1]


def test_rendering_stability_byte_identical():
    issues = [_issue(1, "OPEN", body="Hello\n\nWorld")]
    a = sync.render_archive("Open Issues", issues)
    b = sync.render_archive("Open Issues", issues)
    assert a == b
    assert a.endswith("\n")


def test_yaml_export_includes_referenced_commit():
    calls = []

    def _run(cmd):
        calls.append(cmd)
        if cmd[:2] == ["gh", "api"]:
            path = cmd[-1]

            # IMPORTANT: pagination adds query params; and issue core path is a prefix
            # of the comments/timeline endpoints. So we must match those first.
            if "comments" in path:
                return "[]"
            if "timeline" in path:
                # paginate: page=1 has events, page>=2 is empty
                if "page=1" not in path:
                    return "[]"
                return (
                    '[{"id":1,"event":"referenced","created_at":"2020-01-03T00:00:00Z","actor":{"login":"z","id":3},'
                    '"commit_id":"78542b4","commit_url":"https://example/commit/78542b4"}]'
                )

            if path.startswith("repos/o/r/issues/96"):
                return (
                    '{"number":96,"title":"T96","state":"CLOSED","html_url":"u","created_at":"2020-01-01T00:00:00Z",'
                    '"updated_at":"2020-01-02T00:00:00Z","closed_at":"2020-01-03T00:00:00Z","user":{"login":"x","id":1},'
                    '"closed_by":{"login":"y","id":2},"labels":[],"assignees":[],"milestone":null,"body":"B"}'
                )

            return "[]"
        raise AssertionError(cmd)

    issues = [{"number": 96}]
    y = sync.build_all_issues_yaml("o/r", issues, _run)
    assert "78542b4" in y
    assert "referenced" in y
    assert y.endswith("\n")


def test_sort_by_created_at_tiebreak_id():
    items = [
        {"id": 2, "created_at": "2020-01-01T00:00:00Z"},
        {"id": 1, "created_at": "2020-01-01T00:00:00Z"},
    ]
    out = sync._sort_by_created_at(items)
    assert [i["id"] for i in out] == [1, 2]
