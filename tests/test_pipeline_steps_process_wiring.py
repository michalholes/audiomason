from __future__ import annotations

import re
from pathlib import Path


def test_pipeline_steps_wired_into_process_book() -> None:
    txt = Path("src/audiomason/import_flow.py").read_text(encoding="utf-8")

    assert "def _process_book(" in txt
    assert "steps: list[str]" in txt, "expected _process_book to accept steps param"

    # Formatting-robust: verify that a call to _process_book(...) passes `steps`
    # somewhere in the argument list (regardless of wrapping/newlines).
    assert re.search(
        r"_process_book\([\s\S]*?\bsteps\b[\s\S]*?\)",
        txt,
    ), "expected run_import to pass steps into _process_book call"
