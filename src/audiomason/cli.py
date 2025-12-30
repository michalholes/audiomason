from __future__ import annotations

import runpy
from typing import List, Optional

def main(argv: Optional[List[str]] = None) -> int:
    # For now we run the legacy monolith as-is.
    # This keeps behavior identical while we split into modules.
    # argv is accepted for future use; the legacy script reads sys.argv directly.
    runpy.run_module("audiomason._legacy.abook_import", run_name="__main__")
    return 0
