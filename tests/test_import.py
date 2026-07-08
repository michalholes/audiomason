from __future__ import annotations

from pathlib import Path

import audiomason.state as state
from audiomason.state import Opts


def test_choose_all_sources_prompts_author_per_source(monkeypatch, tmp_path: Path):
    # Create two sources that COLLIDE on Path.stem
    # ("Foo.Bar" -> "Foo", "Foo.Baz" -> "Foo").
    # BUG #70: when selecting "a" (all), stage_run previously used
    # slug(src.stem), which could collide and cause per-source
    # state/answers to leak.
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
    monkeypatch.setattr(imp, "get_drop_root", lambda cfg: drop_root)
    monkeypatch.setattr(imp, "get_stage_root", lambda cfg: stage_root)
    monkeypatch.setattr(imp, "get_archive_root", lambda cfg: archive_root)
    monkeypatch.setattr(imp, "get_output_root", lambda cfg: output_root)

    # Avoid touching audio conversion / network lookups
    monkeypatch.setattr(imp, "convert_m4a_in_place", lambda *a, **k: None)

    # Ensure we do not leak global state into other tests
    old_opts = getattr(state, "OPTS", None)
    old_debug = getattr(state, "DEBUG", False)
    old_verbose = getattr(state, "VERBOSE", False)
    try:
        # Deterministic, non-interactive run (no prompts except prompt())
        state.OPTS = Opts(
            yes=True,
            dry_run=False,
            quiet=True,
            publish=False,
            wipe_id3=False,
            loudnorm=False,
            q_a="2",
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=True,
            clean_inbox_mode="no",
            split_chapters=True,
            ff_loglevel="warning",
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

        monkeypatch.setattr(imp, "prompt", fake_prompt)
        monkeypatch.setattr(imp, "prompt_yes_no", lambda *a, **k: False)

        imp.run_import(cfg={})

        # Assert author prompt happened once per source (2 sources)
        author_prompts = [c for c in prompt_calls if str(c[0]).startswith("[source] Author")]
        assert len(author_prompts) == 2
        # Deterministic order: menu order (sorted by name.lower()) => Foo.Bar then Foo.Baz
        assert author_prompts[0][1] == "Foo.Bar"
        assert author_prompts[1][1] == "Foo.Baz"
    finally:
        state.OPTS = old_opts
        state.DEBUG = old_debug
        state.VERBOSE = old_verbose


def test_clean_inbox_noninteractive_ask_fails_fast(monkeypatch, tmp_path: Path):
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    src = drop_root / "Foo.Bar"
    src.mkdir()
    (src / "01.mp3").write_bytes(b"x")

    import pytest

    import audiomason.import_flow as imp
    from audiomason.util import AmExitError

    monkeypatch.setattr(imp, "get_drop_root", lambda cfg: drop_root)
    monkeypatch.setattr(imp, "get_stage_root", lambda cfg: stage_root)
    monkeypatch.setattr(imp, "get_archive_root", lambda cfg: archive_root)
    monkeypatch.setattr(imp, "get_output_root", lambda cfg: output_root)

    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(
            yes=True,
            dry_run=False,
            quiet=True,
            publish=False,
            wipe_id3=False,
            loudnorm=False,
            q_a="2",
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=True,
            clean_inbox_mode="ask",
            split_chapters=True,
            ff_loglevel="warning",
            cpu_cores=None,
            json=False,
        )
        with pytest.raises(AmExitError):
            imp.run_import(cfg={}, src_path=Path("Foo.Bar"))
    finally:
        state.OPTS = old_opts


def test_clean_inbox_yes_deletes_processed_source(monkeypatch, tmp_path: Path):
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    src = drop_root / "Foo.Bar"
    src.mkdir()
    (src / "01.mp3").write_bytes(b"x")

    import audiomason.import_flow as imp

    monkeypatch.setattr(imp, "get_drop_root", lambda cfg: drop_root)
    monkeypatch.setattr(imp, "get_stage_root", lambda cfg: stage_root)
    monkeypatch.setattr(imp, "get_archive_root", lambda cfg: archive_root)
    monkeypatch.setattr(imp, "get_output_root", lambda cfg: output_root)

    # Avoid any prompts; keep deterministic.
    monkeypatch.setattr(imp, "prompt_yes_no", lambda *a, **k: False)
    monkeypatch.setattr(imp, "_choose_books", lambda cfg, books, default_ans="1": books)

    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(
            yes=True,
            dry_run=False,
            quiet=True,
            publish=False,
            wipe_id3=False,
            loudnorm=False,
            q_a="2",
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=True,
            clean_inbox_mode="yes",
            split_chapters=True,
            ff_loglevel="warning",
            cpu_cores=None,
            json=False,
        )
        imp.run_import(cfg={}, src_path=Path("Foo.Bar"))
        assert not src.exists()
    finally:
        state.OPTS = old_opts


def test_clean_inbox_prompt_never_happens_during_process_when_selecting_all_sources(
    monkeypatch, tmp_path: Path
):
    # Issue #88 regression: when selecting 'a' (all sources),
    # clean_inbox prompt must NOT occur mid-PROCESS.
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    s1 = drop_root / "Src.One"
    s2 = drop_root / "Src.Two"
    s1.mkdir()
    s2.mkdir()
    (s1 / "01.mp3").write_bytes(b"x")
    (s2 / "01.mp3").write_bytes(b"x")

    import audiomason.import_flow as imp

    events: list[str] = []

    answers = iter(["a"])

    def fake_prompt(msg: str, default: str = "") -> str:
        if str(msg).startswith("[source] Author"):
            events.append(f"author:{default}")
            return default
        if str(msg).startswith("[book"):
            return default
        if str(msg).startswith("Choose source number"):
            return next(answers)
        return default

    def fake_pf(cfg, key: str, q: str, default_no: bool = True):
        events.append(f"pf:{key}")
        return False

    def fake_process(*args, **kwargs):
        events.append(f"process:{getattr(imp, '_SOURCE_PREFIX', '')}")
        return None

    monkeypatch.setattr(imp, "get_drop_root", lambda cfg: drop_root)
    monkeypatch.setattr(imp, "get_stage_root", lambda cfg: stage_root)
    monkeypatch.setattr(imp, "get_archive_root", lambda cfg: archive_root)
    monkeypatch.setattr(imp, "get_output_root", lambda cfg: output_root)

    monkeypatch.setattr(imp, "convert_m4a_in_place", lambda *a, **k: None)
    monkeypatch.setattr(imp, "_process_book", fake_process)
    monkeypatch.setattr(imp, "prompt", fake_prompt)
    monkeypatch.setattr(imp, "prompt_yes_no", lambda *a, **k: False)
    monkeypatch.setattr(imp, "_pf_prompt_yes_no", fake_pf)
    monkeypatch.setattr(imp, "_choose_books", lambda cfg, books, default_ans="1": books)

    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(
            debug=False,
            yes=False,
            quiet=False,
            dry_run=False,
            config=None,
            publish=None,
            wipe_id3=None,
            source_prefix=None,
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=False,
            clean_inbox_mode="ask",
            split_chapters=True,
            ff_loglevel="warning",
            cpu_cores=None,
            json=False,
        )
        imp.run_import(cfg={})
    finally:
        state.OPTS = old_opts

    assert events.count("pf:clean_inbox") == 1
    first_process = next((i for i, e in enumerate(events) if e.startswith("process:")), None)
    assert first_process is not None
    assert events.index("pf:clean_inbox") < first_process


def test_choose_all_sources_runs_all_preflights_before_any_processing(monkeypatch, tmp_path: Path):
    # BUG #70: selecting 'a' must run preflight for ALL sources first,
    # then processing for ALL sources.
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    # Two sources
    s1 = drop_root / "Src.One"
    s2 = drop_root / "Src.Two"
    s1.mkdir()
    s2.mkdir()
    (s1 / "01.mp3").write_bytes(b"x")
    (s2 / "01.mp3").write_bytes(b"x")

    import audiomason.import_flow as imp

    events: list[tuple[str, str]] = []

    # prompt sequence:
    # - choose source => 'a'
    # - author for src1
    # - author for src2
    answers = iter(["a", "Src.One", "Src.Two"])

    def fake_prompt(msg: str, default: str = "") -> str:
        if str(msg).startswith("[source] Author"):
            # record "preflight" at the author prompt boundary
            events.append(("preflight", str(default)))
        return next(answers)

    def fake_process(*args, **kwargs):
        # _SOURCE_PREFIX is set to src.name at top of per-source loop
        events.append(("process", str(getattr(imp, "_SOURCE_PREFIX", ""))))
        return None

    monkeypatch.setattr(imp, "get_drop_root", lambda cfg: drop_root)
    monkeypatch.setattr(imp, "get_stage_root", lambda cfg: stage_root)
    monkeypatch.setattr(imp, "get_archive_root", lambda cfg: archive_root)
    monkeypatch.setattr(imp, "get_output_root", lambda cfg: output_root)

    # Avoid external tooling in tests
    monkeypatch.setattr(imp, "convert_m4a_in_place", lambda *a, **k: None)
    monkeypatch.setattr(imp, "_process_book", fake_process)
    monkeypatch.setattr(imp, "prompt", fake_prompt)
    monkeypatch.setattr(imp, "prompt_yes_no", lambda *a, **k: False)

    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(
            debug=False,
            yes=False,
            quiet=False,
            dry_run=True,
            config=None,
            publish=None,
            wipe_id3=None,
            source_prefix=None,
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=False,
            clean_inbox_mode="no",
            split_chapters=True,
            ff_loglevel="warning",
            cpu_cores=None,
            json=False,
        )
        imp.run_import(cfg={})

        # Expect: preflight Src.One, preflight Src.Two,
        # then process Src.One, process Src.Two (deterministic order)
        assert events[:2] == [("preflight", "Src.One"), ("preflight", "Src.Two")]
        assert events[2:] == [("process", "Src.One"), ("process", "Src.Two")]
    finally:
        state.OPTS = old_opts


def test_partial_book_import_ignores_only_processed_book(monkeypatch, tmp_path: Path):
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    src = drop_root / "Meyrink, Gustav (audio) [mp3]"
    book1 = src / "Obrazy vepsane do vzduchu"
    book2 = src / "Vizitka"
    book1.mkdir(parents=True)
    book2.mkdir(parents=True)
    (book1 / "01.mp3").write_bytes(b"x")
    (book2 / "01.mp3").write_bytes(b"y")

    import audiomason.import_flow as imp
    from audiomason.ignore import load_ignore
    from audiomason.util import slug

    monkeypatch.setattr(imp, "get_drop_root", lambda cfg: drop_root)
    monkeypatch.setattr(imp, "get_stage_root", lambda cfg: stage_root)
    monkeypatch.setattr(imp, "get_archive_root", lambda cfg: archive_root)
    monkeypatch.setattr(imp, "get_output_root", lambda cfg: output_root)
    monkeypatch.setattr(imp, "_choose_books", lambda cfg, books, default_ans="1": [books[0]])
    monkeypatch.setattr(imp, "_process_book", lambda *args, **kwargs: None)

    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(
            yes=True,
            dry_run=False,
            quiet=True,
            publish=False,
            wipe_id3=False,
            loudnorm=False,
            q_a="2",
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=True,
            clean_inbox_mode="no",
            split_chapters=True,
            ff_loglevel="warning",
            cpu_cores=None,
            json=False,
        )

        cfg = {"_openlibrary_enabled": False, "_ai_enabled": False}

        imp.run_import(cfg=cfg, src_path=Path(src.name))
        assert load_ignore(src) == {slug("Obrazy vepsane do vzduchu")}
        assert load_ignore(drop_root, source_list=True) == set()
        assert not (drop_root / ".abook_ignore").exists()
        assert (tmp_path / f"{src.name}.abook_ignore").exists()

        imp.run_import(cfg=cfg, src_path=Path(src.name))
        assert load_ignore(src) == {
            slug("Obrazy vepsane do vzduchu"),
            slug("Vizitka"),
        }
        assert slug(src.name) in load_ignore(drop_root, source_list=True)
        assert (tmp_path / ".abook_ignore").exists()
    finally:
        state.OPTS = old_opts


def test_import_passes_stage_run_to_batch_ai_artifacts(monkeypatch, tmp_path: Path):
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    src = drop_root / "sp.rar"
    src.mkdir()
    (src / "01.mp3").write_bytes(b"x")

    from mutagen.id3 import ID3
    from mutagen.id3._frames import TALB, TIT2, TPE1, TRCK

    id3 = ID3()
    id3.add(TIT2(encoding=3, text="Tagged Title"))
    id3.add(TPE1(encoding=3, text="Tagged Artist"))
    id3.add(TALB(encoding=3, text="Tagged Album"))
    id3.add(TRCK(encoding=3, text="7"))
    id3.save(src / "01.mp3")

    import audiomason.ai_lookup as ai_lookup
    import audiomason.import_flow as imp

    seen: dict[str, object] = {}

    def fake_batch_defaults(source_name, books, cfg=None, *, artifact_dir=None):
        seen["artifact_dir"] = artifact_dir
        seen["books"] = books
        return ai_lookup.BatchMetadataSuggestions(source_author=None, book_titles={})

    monkeypatch.setattr(imp, "get_drop_root", lambda cfg: drop_root)
    monkeypatch.setattr(imp, "get_stage_root", lambda cfg: stage_root)
    monkeypatch.setattr(imp, "get_archive_root", lambda cfg: archive_root)
    monkeypatch.setattr(imp, "get_output_root", lambda cfg: output_root)
    monkeypatch.setattr(
        imp.metadata_lookup, "suggest_batch_defaults", fake_batch_defaults, raising=True
    )
    monkeypatch.setattr(imp, "prompt", lambda msg, default="": default)
    monkeypatch.setattr(imp, "prompt_yes_no", lambda *a, **k: False)
    monkeypatch.setattr(imp, "_choose_books", lambda cfg, books, default_ans="1": books)
    monkeypatch.setattr(imp, "_process_book", lambda *args, **kwargs: None)

    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(
            yes=True,
            dry_run=False,
            quiet=True,
            publish=False,
            wipe_id3=False,
            loudnorm=False,
            q_a="2",
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=True,
            clean_inbox_mode="no",
            split_chapters=True,
            ff_loglevel="warning",
            cpu_cores=None,
            json=False,
        )

        imp.run_import(cfg={}, src_path=Path(src.name))

        assert seen["artifact_dir"] == stage_root / "sp.rar"
        assert isinstance(seen["books"], list)
        assert seen["books"][0]["id3"][0]["title"] == "Tagged Title"
        assert seen["books"][0]["id3"][0]["artist"] == "Tagged Artist"
    finally:
        state.OPTS = old_opts


def test_book_title_defaults_use_one_numbering_style_per_series(monkeypatch, tmp_path: Path):
    drop_root = tmp_path / "abooksinbox"
    stage_root = tmp_path / "_am_stage"
    archive_root = tmp_path / "abooks"
    output_root = tmp_path / "abooks_ready"
    for d in (drop_root, stage_root, archive_root, output_root):
        d.mkdir(parents=True, exist_ok=True)

    src = drop_root / "sp.rar"
    src.mkdir()
    for book in [
        "__ROOT_AUDIO__",
        "Adams D Stoparuv Pruvodce Galaxii 2 Restaurant Na Konci Vesmiru",
        "Douglas Adams - Stoparuv pruvodce galaxii 3 (2021)(CZ)",
        (
            "Douglas Adams - Stopařův průvodce galaxii IV - Sbohem a díky za ryby "
            "(Vojtěch Kotek)(5h40m20s)"
        ),
    ]:
        book_dir = src if book == "__ROOT_AUDIO__" else src / book
        book_dir.mkdir(parents=True, exist_ok=True)
        (book_dir / "01.mp3").write_bytes(b"x")

    import audiomason.ai_lookup as ai_lookup
    import audiomason.import_flow as imp

    monkeypatch.setattr(imp, "get_drop_root", lambda cfg: drop_root)
    monkeypatch.setattr(imp, "get_stage_root", lambda cfg: stage_root)
    monkeypatch.setattr(imp, "get_archive_root", lambda cfg: archive_root)
    monkeypatch.setattr(imp, "get_output_root", lambda cfg: output_root)
    monkeypatch.setattr(imp, "_choose_books", lambda cfg, books, default_ans="1": books)
    monkeypatch.setattr(imp, "_process_book", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        imp.metadata_lookup,
        "suggest_batch_defaults",
        lambda source_name, books, cfg=None, *, artifact_dir=None: (
            ai_lookup.BatchMetadataSuggestions(
                source_author="Douglas Adams",
                book_titles={
                    "__ROOT_AUDIO__": "Stoparuv pruvodce Galaxii V. - Prevazne neskodna",
                    ("Adams D Stoparuv Pruvodce Galaxii 2 Restaurant Na Konci Vesmiru"): (
                        "Stoparuv pruvodce Galaxii 2 - Restaurant na konci vesmiru"
                    ),
                    "Douglas Adams - Stoparuv pruvodce galaxii 3 (2021)(CZ)": (
                        "Stoparuv pruvodce galaxii 3 - Zivot, vesmir a vubec"
                    ),
                    (
                        "Douglas Adams - Stopařův průvodce galaxii IV - Sbohem a díky za "
                        "ryby (Vojtěch Kotek)(5h40m20s)"
                    ): ("Stoparuv pruvodce galaxii IV - Sbohem a diky za ryby"),
                },
            )
        ),
        raising=True,
    )

    defaults: list[str] = []

    def fake_prompt(msg: str, default: str = "") -> str:
        if str(msg).startswith("[book ") and "Book title" in str(msg):
            defaults.append(default)
        return default

    monkeypatch.setattr(imp, "prompt", fake_prompt)
    monkeypatch.setattr(imp, "prompt_yes_no", lambda *a, **k: False)

    old_opts = getattr(state, "OPTS", None)
    try:
        state.OPTS = Opts(
            yes=True,
            dry_run=False,
            quiet=True,
            publish=False,
            wipe_id3=False,
            loudnorm=False,
            q_a="2",
            verify=False,
            verify_root=output_root,
            lookup=False,
            cleanup_stage=True,
            clean_inbox_mode="no",
            split_chapters=True,
            ff_loglevel="warning",
            cpu_cores=None,
            json=False,
        )

        imp.run_import(
            cfg={"_openlibrary_enabled": False, "_ai_enabled": True}, src_path=Path(src.name)
        )

        assert any(" 2 " in d for d in defaults)
        assert any(" 3 " in d for d in defaults)
        assert all(" II " not in d and " III " not in d for d in defaults)
    finally:
        state.OPTS = old_opts
