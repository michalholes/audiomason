from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .pipeline import cmd_inspect, cmd_process


def main() -> int:
    ap = argparse.ArgumentParser(prog="audiomason")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ins = sub.add_parser("inspect", help="analyze input and print book candidates")
    p_ins.add_argument("path", type=Path)

    p_proc = sub.add_parser("process", help="process input (prompts), produce ready output")
    p_proc.add_argument("path", type=Path)
    p_proc.add_argument("--yes", action="store_true", help="non-interactive (use defaults)")

    ns = ap.parse_args()
    cfg = load_config()

    if ns.cmd == "inspect":
        return cmd_inspect(cfg, ns.path)
    if ns.cmd == "process":
        return cmd_process(cfg, ns.path, yes=ns.yes)

    return 2
