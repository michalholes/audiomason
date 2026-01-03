from __future__ import annotations

from pathlib import Path

import audiomason.state as state
from audiomason.state import Opts


def test_choose_all_sources_prompts_author_per_source(monkeypatch, tmp_path: Path):
    # Create two sources that COLLIDE on Path.stem ("Foo.Bar" -> "Foo", "Foo.Baz" -> "Foo").
    # BUG #70: when selecting "a" (all), stage_run previously used slug(src.stem), which could collide
    # and cause per-source state/answers to leak.
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    s1 = drop_root / "Foo.Bar"
    s2 = drop_root / "Foo.Baz"
    s1.mkdir()
    s2.mkdir()
    # one mp3 each so book detection finds __ROOT_AUDIO__
    (s1 / "01.mp3").write_bytes(b"x")
    (s2 / "01.mp3").write_bytes(b"y")

    import audiomason.import_flow as imp

    # Patch path resolvers to our tmp layout (avoid depending on paths.py contract details)
    monkeypatch.setattr(imp, 'get_drop_root', lambda cfg: drop_root)
    monkeypatch.setattr(imp, 'get_stage_root', lambda cfg: stage_root)
    monkeypatch.setattr(imp, 'get_archive_root', lambda cfg: archive_root)
    monkeypatch.setattr(imp, 'get_output_root', lambda cfg: output_root)

    # Avoid touching audio conversion / network lookups
    monkeypatch.setattr(imp, 'convert_m4a_in_place', lambda *a, **k: None)

    # Ensure we do not leak global state into other tests
    old_opts = getattr(state, 'OPTS', None)
    old_debug = getattr(state, 'DEBUG', False)
    old_verbose = getattr(state, 'VERBOSE', False)
    try:
        # Deterministic, non-interactive run (no prompts except prompt())
        state.OPTS = Opts(
            yes=True,
            dry_run=True,
            quiet=True,
            publish=False,
            wipe_id3=False,
            loudnorm=False,
            q_a='2',
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=True,
            split_chapters=True,
            ff_loglevel='warning',
            cpu_cores=None,
            json=False,
        )
        state.DEBUG = False
        state.VERBOSE = False

        # prompt() sequence: choose source -> author1 -> title1 -> author2 -> title2
        answers = iter(["a", "Author One", "Book One", "Author Two", "Book Two"])
        prompt_calls = []

        def fake_prompt(msg: str, default: str = "") -> str:
            prompt_calls.append((msg, default))
            return next(answers)

        monkeypatch.setattr(imp, 'prompt', fake_prompt)
        monkeypatch.setattr(imp, 'prompt_yes_no', lambda *a, **k: False)

        imp.run_import(cfg={})

        # Assert author prompt happened once per source (2 sources)
        author_prompts = [c for c in prompt_calls if c[0] == '[source] Author']
        assert len(author_prompts) == 2
        # Deterministic order: menu order (sorted by name.lower()) => Foo.Bar then Foo.Baz
        assert author_prompts[0][1] == 'Foo.Bar'
        assert author_prompts[1][1] == 'Foo.Baz'
    finally:
        state.OPTS = old_opts
        state.DEBUG = old_debug
        state.VERBOSE = old_verbose
