# Issue #93: Preflight Registry Guard
from __future__ import annotations

from audiomason.preflight_registry import DEFAULT_PREFLIGHT_STEPS, REGISTRY


def test_registry_covers_default_steps():
    for k in DEFAULT_PREFLIGHT_STEPS:
        assert k in REGISTRY


def test_choose_source_is_registered_non_movable():
    # Design #92: choose_source exists in registry and is NON-MOVABLE.
    assert "choose_source" in REGISTRY
    assert REGISTRY["choose_source"].non_movable is True
