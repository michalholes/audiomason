from __future__ import annotations

from importlib import metadata


def _pkg_version() -> str:
    try:
        return metadata.version("audiomason")
    except metadata.PackageNotFoundError:
        return "0+unknown"


__version__ = _pkg_version()
