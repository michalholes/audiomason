from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from audiomason.version import __version__
from audiomason.config import load_config
import audiomason.state as state
from audiomason.state import Opts
from audiomason.import_flow import run_import
from audiomason.verify import verify_library
from audiomason.paths import OUTPUT_ROOT


def _parent_parser(cfg: Dict[str, Any]) -> argparse.ArgumentParser:
    audio = cfg.get("audio", {}) if isinstance(cfg.get("audio", {}), dict) else {}
    paths = cfg.get("paths", {}) if isinstance(cfg.get("paths", {}), dict) else {}

    pp = argparse.ArgumentParser(add_help=False)
    pp.add_argument("--yes", action="store_true", help="non-interactive")
    pp.add_argument("--dry-run", action="store_true", help="do not modify anything")
    pp.add_argument("--quiet", action="store_true", help="less output")
    pp.add_argument("--verbose", action="store_true", help="more output (overrides --quiet)")
    pp.add_argument("--debug", action="store_true", help="prefix every out() line with [TRACE]")
    pp.add_argument("--verify", action="store_true", help="verify library after import")

    default_verify_root = Path(paths.get("verify_root", OUTPUT_ROOT))
    pp.add_argument("--verify-root", type=Path, default=default_verify_root, help="root for --verify")

    g2 = pp.add_mutually_exclusive_group()
    g2.add_argument("--lookup", dest="lookup", action="store_true", default=True, help="enable OpenLibrary validation")
    g2.add_argument("--no-lookup", dest="lookup", action="store_false", help="disable OpenLibrary validation")

    pp.add_argument("--publish", choices=["yes", "no", "ask"], default=str(paths.get("publish", "ask")))
    g = pp.add_mutually_exclusive_group()
    g.add_argument("--wipe-id3", dest="wipe_id3", action="store_true", default=None, help="full wipe ID3 tags before writing new tags")
    g.add_argument("--no-wipe-id3", dest="wipe_id3", action="store_false", help="do not wipe ID3 tags (default)")
    pp.add_argument("--loudnorm", action="store_true", default=bool(audio.get("loudnorm", False)))
    pp.add_argument("--q-a", default=str(audio.get("q_a", "2")), help="lame VBR quality (2=high)")
    pp.add_argument("--split-chapters", dest="split_chapters", action="store_true", default=bool(audio.get("split_chapters", True)))
    pp.add_argument("--no-split-chapters", dest="split_chapters", action="store_false")
    pp.add_argument("--cpu-cores", type=int, default=cfg.get("cpu_cores", None), help="override CPU core count for perf tuning")
    pp.add_argument("--ff-loglevel", choices=["info", "warning", "error"], default=str(audio.get("ff_loglevel", "warning")))
    return pp


def _parse_args() -> argparse.Namespace:
    cfg = load_config()
    parent = _parent_parser(cfg)

    ap = argparse.ArgumentParser(
        prog="audiomason",
        description="AudioMason – audiobook import & maintenance tool",
        parents=[parent],
    )
    ap.add_argument("--version", action="store_true", help="show version and exit")

    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("import", help="import audiobooks from inbox", parents=[parent])

    v = sub.add_parser("verify", help="verify audiobook library", parents=[parent])
    v.add_argument("root", nargs="?", type=Path, default=None)

    i = sub.add_parser("inspect", help="read-only source inspection", parents=[parent])
    i.add_argument("path", type=Path)

    ns = ap.parse_args()

    if ns.version:
        print(__version__)
        raise SystemExit(0)

    if not ns.cmd:
        ns.cmd = "import"

    if ns.verbose:
        ns.quiet = False

    return ns


def _ns_to_opts(ns: argparse.Namespace) -> Opts:
    publish = {"yes": True, "no": False, "ask": None}[ns.publish]
    return Opts(
yes=ns.yes,
        dry_run=ns.dry_run,
        quiet=ns.quiet,
        publish=publish,
        wipe_id3=ns.wipe_id3,
        loudnorm=ns.loudnorm,
        q_a=ns.q_a,
        verify=ns.verify,
        verify_root=ns.verify_root,
        lookup=getattr(ns, "lookup", True),
        cleanup_stage=True,
        split_chapters=ns.split_chapters,
        ff_loglevel=ns.ff_loglevel,
        cpu_cores=getattr(ns, 'cpu_cores', None),
    )


def main() -> int:
    cfg = load_config()
    ns = _parse_args()

    # DEBUG wiring must be active before any out()/trace output
    state.DEBUG = bool(getattr(ns, "debug", False))
    state.VERBOSE = bool(getattr(ns, "verbose", False))
    if state.DEBUG:
        from audiomason.util import enable_trace
        enable_trace()

    state.OPTS = _ns_to_opts(ns)

    if ns.cmd == "inspect":
        from audiomason.inspect import inspect_source
        inspect_source(ns.path)
        return 0

    if ns.cmd == "verify":
        root = ns.root or state.OPTS.verify_root
        verify_library(root)
        return 0

    try:
        run_import(cfg)
    except KeyboardInterrupt:
        from audiomason.util import out
        out("[abort] cancelled by user")
        return 130
    return 0
