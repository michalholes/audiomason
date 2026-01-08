# Issue #93: Preflight Step Registry
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


# One-list ordering model (Design #92):
# - preflight_steps is a single linear list
# - choose_source + choose_books are NON-MOVABLE
# - everything else is MOVABLE
#
# Registry owns:
# - canonical step keys
# - default ordering baseline (NO-CONFIG = NO-CHANGE)
# - deterministic validation (unknown/dup/missing + required hard deps)


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


# Canonical default ordering baseline (NO-CONFIG = NO-CHANGE).
# NOTE: choose_source is included but NON-MOVABLE (it is never offered as movable).
DEFAULT_PREFLIGHT_STEPS: list[str] = [
    # stage reuse / answers
    "reuse_stage",
    "use_manifest_answers",
    # selection (NON-MOVABLE)
    "choose_source",
    "choose_books",
    # selection / resume
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


def validate_steps_list(order: list[str]) -> list[str]:
    # Deterministic fail-fast validation (unknown/dup/missing + required hard deps).
    seen: set[str] = set()
    out: list[str] = []
    for x in order:
        k = str(x).strip()
        if not k:
            continue
        if k in seen:
            raise ValueError(f"duplicate preflight step key: {k}")
        if k not in REGISTRY:
            raise ValueError(f"unknown preflight step key: {k}")
        seen.add(k)
        out.append(k)

    missing = [k for k in DEFAULT_PREFLIGHT_STEPS if k not in seen]
    if missing:
        raise ValueError("missing required preflight step key(s): " + ", ".join(missing))

    pos = {k: i for i, k in enumerate(out)}

    def _req(a: str, b: str) -> None:
        if pos[a] > pos[b]:
            raise ValueError(f"order requires {a} before {b}")

    # ordering constraints (deterministic)
    _req("reuse_stage", "use_manifest_answers")
    _req("reuse_stage", "choose_books")
    _req("use_manifest_answers", "choose_books")
    _req("choose_source", "choose_books")
    _req("choose_books", "skip_processed_books")
    _req("source_author", "book_title")
    _req("book_title", "cover")
    _req("cover", "overwrite_destination")
    _req("choose_books", "book_title")
    _req("choose_books", "cover")
    _req("choose_books", "overwrite_destination")

    return out
