from __future__ import annotations

from pathlib import Path

import audiomason.state as state
from audiomason import import_flow


def test_process_book_dry_run_summary_includes_pipeline_steps(
    tmp_path: Path,
) -> None:
    prev_opts = state.OPTS
    try:
        state.OPTS = state.Opts(dry_run=True)

        stage_run = tmp_path / "stage"
        stage_run.mkdir()
        dest_root = tmp_path / "dest"
        final_root = tmp_path / "final"

        b = import_flow.BookGroup(
            label="B",
            group_root=tmp_path / "g",
            stage_root=tmp_path / "s",
        )
        steps = ["rename", "tags", "cover"]

        import_flow._process_book(
            1,
            1,
            b,
            stage_run,
            dest_root,
            author="Author",
            title="Title",
            out_title="Title",
            wipe=False,
            cover_mode="skip",
            overwrite=False,
            cfg={},
            final_root=final_root,
            steps=steps,
        )

        summary = stage_run / "Author - Title.dryrun.txt"
        assert summary.exists()
        txt = summary.read_text(encoding="utf-8")
        assert "Pipeline steps: rename -> tags -> cover" in txt
    finally:
        state.OPTS = prev_opts
