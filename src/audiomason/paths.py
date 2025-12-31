from pathlib import Path

ARCHIVE_EXTS = {".zip", ".rar", ".7z"}


def _get(cfg, key: str, default: str) -> Path:
    try:
        val = cfg.get("paths", {}).get(key)
        if val:
            return Path(val).expanduser()
    except Exception:
        pass
    return Path(default).resolve()


def get_drop_root(cfg) -> Path:
    return _get(cfg, "inbox", "./inbox")


def get_stage_root(cfg) -> Path:
    return _get(cfg, "stage", "./stage")


def get_output_root(cfg) -> Path:
    return _get(cfg, "output", "./output")


def get_archive_root(cfg) -> Path:
    return _get(cfg, "archive", "./archive")
