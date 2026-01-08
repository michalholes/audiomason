from __future__ import annotations

import pytest

from audiomason.import_flow import _resolved_preflight_steps
from audiomason.util import AmConfigError


def test_preflight_steps_unknown_key_fails_fast():
    cfg = {"preflight_steps": ["reuse_stage", "NOPE", "use_manifest_answers", "choose_books", "skip_processed_books", "publish", "wipe_id3", "clean_stage", "source_author", "book_title", "cover", "overwrite_destination"]}
    with pytest.raises(AmConfigError):
        _resolved_preflight_steps(cfg)


def test_preflight_steps_duplicate_key_fails_fast():
    cfg = {"preflight_steps": ["reuse_stage", "reuse_stage", "use_manifest_answers", "choose_books", "skip_processed_books", "publish", "wipe_id3", "clean_stage", "source_author", "book_title", "cover", "overwrite_destination"]}
    with pytest.raises(AmConfigError):
        _resolved_preflight_steps(cfg)


def test_preflight_steps_missing_key_fails_fast():
    cfg = {"preflight_steps": ["reuse_stage", "use_manifest_answers", "choose_books", "skip_processed_books", "publish", "wipe_id3", "clean_stage", "source_author", "book_title", "cover"]}
    with pytest.raises(AmConfigError):
        _resolved_preflight_steps(cfg)


def test_preflight_steps_dependency_violation_fails_fast():
    cfg = {"preflight_steps": ["reuse_stage", "use_manifest_answers", "choose_books", "skip_processed_books", "publish", "wipe_id3", "clean_stage", "book_title", "source_author", "cover", "overwrite_destination"]}
    with pytest.raises(AmConfigError):
        _resolved_preflight_steps(cfg)


def test_preflight_steps_default_is_canonical_order():
    cfg = {}
    steps = _resolved_preflight_steps(cfg)
    assert steps == [
        "reuse_stage",
        "use_manifest_answers",
        "choose_books",
        "skip_processed_books",
        "publish",
        "wipe_id3",
        "clean_stage",
        "source_author",
        "book_title",
        "cover",
        "overwrite_destination",
    ]
