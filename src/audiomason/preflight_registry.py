# Issue #93: Preflight Step Registry
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


MIN_CONTEXT_NONE = "none"
MIN_CONTEXT_SOURCE = "source_selected"
MIN_CONTEXT_BOOKS = "books_selected"


@dataclass(frozen=True)
class PreflightStepMeta:
    key: str
    non_movable: bool
    min_context: str
    default_apply_scope: str  # run/source/book/author (min run/source/book)
    condition: Optional[Callable[[dict], bool]] = None


# Canonical default ordering baseline (NO-CONFIG = NO-CHANGE in RUN1).
# (Design #92 adds choose_source as NON-MOVABLE, but wiring is introduced in later runs.)
DEFAULT_PREFLIGHT_STEPS: list[str] = [
    # stage reuse / answers
    "reuse_stage",
    "use_manifest_answers",
    # selection / resume
    "choose_books",
    "skip_processed_books",
    # global decisions
    "publish",
    "wipe_id3",
    "clean_stage",
    # source + per-book
    "source_author",
    "book_title",
    "cover",
    "overwrite_destination",
]


# Registry includes all known step keys for subsequent dispatcher refactor.
# NON-MOVABLE steps are present even if not executed via dispatcher yet (RUN1 scaffolding).
REGISTRY: dict[str, PreflightStepMeta] = {
    "reuse_stage": PreflightStepMeta(
        key="reuse_stage",
        non_movable=False,
        min_context=MIN_CONTEXT_SOURCE,
        default_apply_scope="source",
    ),
    "use_manifest_answers": PreflightStepMeta(
        key="use_manifest_answers",
        non_movable=False,
        min_context=MIN_CONTEXT_SOURCE,
        default_apply_scope="source",
    ),
    "choose_source": PreflightStepMeta(
        key="choose_source",
        non_movable=True,
        min_context=MIN_CONTEXT_NONE,
        default_apply_scope="run",
    ),
    "choose_books": PreflightStepMeta(
        key="choose_books",
        non_movable=True,
        min_context=MIN_CONTEXT_SOURCE,
        default_apply_scope="source",
    ),
    "skip_processed_books": PreflightStepMeta(
        key="skip_processed_books",
        non_movable=False,
        min_context=MIN_CONTEXT_BOOKS,
        default_apply_scope="source",
    ),
    "publish": PreflightStepMeta(
        key="publish",
        non_movable=False,
        min_context=MIN_CONTEXT_SOURCE,
        default_apply_scope="source",
    ),
    "wipe_id3": PreflightStepMeta(
        key="wipe_id3",
        non_movable=False,
        min_context=MIN_CONTEXT_SOURCE,
        default_apply_scope="source",
    ),
    "clean_stage": PreflightStepMeta(
        key="clean_stage",
        non_movable=False,
        min_context=MIN_CONTEXT_SOURCE,
        default_apply_scope="source",
    ),
    "source_author": PreflightStepMeta(
        key="source_author",
        non_movable=False,
        min_context=MIN_CONTEXT_SOURCE,
        default_apply_scope="source",
    ),
    "book_title": PreflightStepMeta(
        key="book_title",
        non_movable=False,
        min_context=MIN_CONTEXT_BOOKS,
        default_apply_scope="book",
    ),
    "cover": PreflightStepMeta(
        key="cover",
        non_movable=False,
        min_context=MIN_CONTEXT_BOOKS,
        default_apply_scope="book",
    ),
    "overwrite_destination": PreflightStepMeta(
        key="overwrite_destination",
        non_movable=False,
        min_context=MIN_CONTEXT_BOOKS,
        default_apply_scope="book",
    ),
}


def default_steps() -> list[str]:
    return list(DEFAULT_PREFLIGHT_STEPS)
