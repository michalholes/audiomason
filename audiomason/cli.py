from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .pipeline import cmd_inspect, cmd_process, cmd_import, cmd_verify


def main() -> int:
    ap = argparse.ArgumentParser(prog="audiomason")
    ap.add_argument("--verbose", action="store_true", help="more output")
    ap.add_argument("--quiet", action="store_true", help="less output")
    sub = ap.add_subparsers(dest="cmd")

    p_ins = sub.add_parser("inspect", help="analyze input and print book candidates")
    p_ins.add_argument("path", type=Path)

    p_proc = sub.add_parser("process", help="process input (prompts), produce ready output")
    p_proc.add_argument("path", type=Path)
    p_proc.add_argument("--yes", action="store_true", help="non-interactive (use defaults)")
    p_proc.add_argument("--dry-run", action="store_true", help="plan only (avoid destructive actions)")

    sub.add_parser("verify", help="verify archive library (id3, tracks, cover)")

    p_imp = sub.add_parser("import", help="scan inbox and run interactive import (default)")
    p_imp.add_argument("--all", action="store_true", help="include ignored items")
    p_imp.add_argument("--yes", action="store_true", help="non-interactive (use defaults)")
    p_imp.add_argument("--dry-run", action="store_true", help="plan only (avoid destructive actions)")

    ns = ap.parse_args()
    if ns.cmd is None:
        ns.cmd = "import"
    cfg = load_config()
    cfg.setdefault("runtime", {})
    cfg["runtime"]["verbose"] = bool(getattr(ns, "verbose", False))
    cfg["runtime"]["quiet"] = bool(getattr(ns, "quiet", False))

    if ns.cmd == "inspect":
        return cmd_inspect(cfg, ns.path)
    if ns.cmd == "process":
        return cmd_process(cfg, ns.path, yes=ns.yes, dry_run=getattr(ns, 'dry_run', False))
    if ns.cmd == "import":
        return cmd_import(cfg, yes=getattr(ns, "yes", False), all_items=getattr(ns, "all", False))

    return 2
