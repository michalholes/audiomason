from __future__ import annotations

from pathlib import Path

import pytest

from audiomason.config import load_config
from audiomason.util import AmConfigError


def test_ai_max_completion_tokens_is_accepted(tmp_path: Path):
    cfgp = tmp_path / "config.yaml"
    cfgp.write_text(
        "ai:\n  enabled: true\n  max_completion_tokens: 128\n",
        encoding="utf-8",
    )

    cfg: dict[str, object] = load_config(cfgp)
    ai_cfg = cfg["ai"]
    assert isinstance(ai_cfg, dict)
    assert ai_cfg["max_completion_tokens"] == 128


def test_ai_max_completion_tokens_must_be_positive_integer(tmp_path: Path):
    cfgp = tmp_path / "config.yaml"
    cfgp.write_text(
        "ai:\n  enabled: true\n  max_completion_tokens: 0\n",
        encoding="utf-8",
    )

    with pytest.raises(AmConfigError, match="ai.max_completion_tokens"):
        load_config(cfgp)
