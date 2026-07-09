# Preflight prompt resolution — config defaults & disable logic.
from __future__ import annotations

from typing import cast

import audiomason.state as state
from audiomason.util import AmConfigError, out, prompt, prompt_yes_no

PREFLIGHT_DISABLE_KEYS = {
    "publish",
    "wipe_id3",
    "clean_stage",
    "clean_inbox",
    "reuse_stage",
    "use_manifest_answers",
    "normalize_author",
    "normalize_book_title",
    "cover",
}

_PROMPTS_DISABLE_ALLOWED = {
    "normalize_author",
    "normalize_book_title",
    "publish",
    "wipe_id3",
    "clean_stage",
    "reuse_stage",
    "cover",
    "choose_source",
    "choose_books",
    "skip_processed_books",
    "overwrite_destination",
    "source_author",
    "book_title",
    "choose_cover",
    "cover_input",
}


def resolve_preflight_disable(cfg: dict[str, object]) -> set[str]:
    cached = cfg.get("_preflight_disable_set")
    if isinstance(cached, set):
        return cast(set[str], cached)
    raw: object = cfg.get("preflight_disable", [])
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise AmConfigError("Invalid config: preflight_disable must be a list of keys")
    out_set: set[str] = set()
    for x in cast(list[object], raw):
        k = str(x).strip()
        if not k:
            continue
        if k not in PREFLIGHT_DISABLE_KEYS:
            raise AmConfigError(f"Invalid config: unknown preflight_disable key: {k}")
        out_set.add(k)
    cfg["_preflight_disable_set"] = out_set
    return out_set


def resolve_prompts_disable(cfg: dict[str, object]) -> set[str]:
    cached = cfg.get("_prompts_disable_set")
    if isinstance(cached, set):
        return cast(set[str], cached)
    prm_obj = cfg.get("prompts", {})
    if prm_obj is None:
        prm_obj = {}
    if not isinstance(prm_obj, dict):
        raise AmConfigError("Invalid config: prompts must be a mapping")
    prm = cast(dict[str, object], prm_obj)
    raw: object = prm.get("disable", [])
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise AmConfigError("Invalid config: prompts.disable must be a list")
    seen: set[str] = set()
    for x in cast(list[object], raw):
        if not isinstance(x, str):
            raise AmConfigError("Invalid config: prompts.disable items must be strings")
        if x in seen:
            raise AmConfigError(f"Invalid config: duplicate prompts.disable key: {x}")
        seen.add(x)
    if "*" in seen and len(seen) != 1:
        raise AmConfigError("Invalid config: prompts.disable cannot combine '*' with other keys")
    unknown = sorted(k for k in seen if k != "*" and k not in _PROMPTS_DISABLE_ALLOWED)
    if unknown:
        raise AmConfigError(f"Invalid config: unknown prompts.disable key(s): {', '.join(unknown)}")
    cfg["_prompts_disable_set"] = seen
    return seen


def prompt_disabled(cfg: dict[str, object], key: str) -> bool:
    ds = resolve_prompts_disable(cfg)
    return "*" in ds or key in ds


def pf_disabled(cfg: dict[str, object], key: str) -> bool:
    return prompt_disabled(cfg, key) or (key in resolve_preflight_disable(cfg))


def pf_prompt_yes_no(cfg: dict[str, object], key: str, question: str, *, default_no: bool) -> bool:
    if pf_disabled(cfg, key):
        ret = not default_no
        if state.DEBUG:
            out(f"[TRACE] [preflight] disabled: {key} -> default: {'no' if default_no else 'yes'}")
        return ret
    return prompt_yes_no(question, default_no=default_no)


def pf_prompt(cfg: dict[str, object], key: str, question: str, default: str) -> str:
    if pf_disabled(cfg, key):
        if state.DEBUG:
            out(f"[TRACE] [preflight] disabled: {key} -> default: {default}")
        return default
    return prompt(question, default)


def resolve_bool_config(cfg: dict[str, object], key: str) -> bool | None:
    raw = cfg.get(key)
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return {"yes": True, "no": False, "true": True, "false": False}.get(raw.lower())
    return None
