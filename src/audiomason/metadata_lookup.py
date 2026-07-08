from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

import audiomason.ai_lookup as ai_lookup
import audiomason.openlibrary as openlibrary


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _lookup_enabled(cfg: Mapping[str, object] | None) -> bool:
    if cfg is None:
        try:
            import audiomason.state as state

            return bool(state.OPTS is not None and state.OPTS.lookup)
        except Exception:
            return False
    if "_openlibrary_enabled" in cfg:
        return bool(cfg.get("_openlibrary_enabled"))
    raw = _as_dict(cfg.get("openlibrary"))
    return bool(raw.get("enabled", True))


def _ai_enabled(cfg: Mapping[str, object] | None) -> bool:
    if cfg is None:
        try:
            import audiomason.state as state

            return bool(state.OPTS is not None and state.OPTS.ai_lookup)
        except Exception:
            return False
    if "_ai_enabled" in cfg:
        return bool(cfg.get("_ai_enabled"))
    raw = _as_dict(cfg.get("ai"))
    return bool(raw.get("enabled", False))


def is_enabled(cfg: Mapping[str, object] | None = None) -> bool:
    return _lookup_enabled(cfg) or _ai_enabled(cfg)


def _ai_cfg(cfg: Mapping[str, object] | None) -> Mapping[str, object] | None:
    return cfg


def suggest_batch_defaults(
    source_name: str,
    books: list[dict[str, object]],
    cfg: Mapping[str, object] | None = None,
    *,
    artifact_dir: Path | None = None,
) -> ai_lookup.BatchMetadataSuggestions | None:
    return ai_lookup.suggest_batch_defaults(
        source_name, books, cfg=_ai_cfg(cfg), artifact_dir=artifact_dir
    )


def validate_author(
    name: str,
    cfg: Mapping[str, object] | None = None,
    *,
    context: str | None = None,
    artifact_dir: Path | None = None,
) -> openlibrary.OLResult:
    q = (name or "").strip()
    if not q:
        return openlibrary.OLResult(False, "author:empty", 0, None)

    public_res: openlibrary.OLResult | None = None
    if _lookup_enabled(cfg):
        public_res = openlibrary.validate_author(q)
        if public_res.ok or public_res.top or not _ai_enabled(cfg):
            return public_res

    if _ai_enabled(cfg):
        suggestion = ai_lookup.suggest_author(
            q, cfg=_ai_cfg(cfg), context=context, artifact_dir=artifact_dir
        )
        if suggestion:
            return openlibrary.OLResult(True, "author:ai", 1, suggestion, "ai")

    if public_res is not None:
        return public_res
    return openlibrary.OLResult(False, "author:not_found", 0, None)


def validate_book(
    author: str,
    title: str,
    cfg: Mapping[str, object] | None = None,
    *,
    context: str | None = None,
    artifact_dir: Path | None = None,
) -> openlibrary.OLResult:
    a = (author or "").strip()
    t = (title or "").strip()
    if not a or not t:
        return openlibrary.OLResult(False, "book:empty", 0, None)

    public_res: openlibrary.OLResult | None = None
    if _lookup_enabled(cfg):
        public_res = openlibrary.validate_book(a, t)
        if public_res.ok or public_res.top or not _ai_enabled(cfg):
            return public_res

    if _ai_enabled(cfg):
        suggestion = ai_lookup.suggest_title(
            a, t, cfg=_ai_cfg(cfg), context=context, artifact_dir=artifact_dir
        )
        if suggestion:
            return openlibrary.OLResult(True, "book:ai", 1, suggestion, "ai")

    if public_res is not None:
        return public_res
    return openlibrary.OLResult(False, "book:not_found", 0, None)
