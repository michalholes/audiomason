from pathlib import Path


def test_pipeline_steps_wired_into_process_book():
    s = Path("src/audiomason/import_flow.py").read_text(encoding="utf-8")

    assert "def _process_book(" in s
    assert "steps: list[str]" in s, "expected _process_book to accept steps param"
    assert "_process_book(" in s and ", steps)" in s, "expected run_import to pass steps into _process_book call"
