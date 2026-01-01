from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from audiomason.version import __version__
from audiomason.config import load_config
import audiomason.state as state
from audiomason.state import Opts
from audiomason.import_flow import run_import
from audiomason.verify import verify_library
from audiomason.paths import validate_paths_contract, get_output_root
def _parent_parser(cfg: Dict[str, Any]) -> argparse.ArgumentParser:
    ffmpeg = cfg.get("ffmpeg", {}) if isinstance(cfg.get("ffmpeg", {}), dict) else {}
    paths = cfg.get("paths", {}) if isinstance(cfg.get("paths", {}), dict) else {}

    pp = argparse.ArgumentParser(add_help=False)
    pp.add_argument("--yes", action="store_true", help="non-interactive")
    pp.add_argument("--dry-run", action="store_true", help="do not modify anything")
    pp.add_argument("--quiet", action="store_true", help="less output")
    pp.add_argument("--verbose", action="store_true", help="more output (overrides --quiet)")
    pp.add_argument("--debug", action="store_true", help="prefix every out() line with [TRACE]")
    pp.add_argument("--json", action="store_true", help="print machine-readable JSON report at end")
    pp.add_argument("--config", type=Path, help="explicit configuration.yaml path")
    pp.add_argument("--verify", action="store_true", help="verify library after import")

    default_verify_root = Path(paths.get("verify_root") or "__AUDIOMASON_VERIFY_ROOT_UNSET__")
    pp.add_argument("--verify-root", type=Path, default=default_verify_root, help="root for --verify")

    g2 = pp.add_mutually_exclusive_group()
    g2.add_argument("--lookup", dest="lookup", action="store_true", default=True, help="enable OpenLibrary validation")
    g2.add_argument("--no-lookup", dest="lookup", action="store_false", help="disable OpenLibrary validation")

    publish_default = cfg.get("publish", "ask")
    if isinstance(publish_default, bool):
        publish_default = "yes" if publish_default else "no"
    pp.add_argument("--publish", choices=["yes", "no", "ask"], default=str(publish_default))
    g = pp.add_mutually_exclusive_group()
    g.add_argument("--wipe-id3", dest="wipe_id3", action="store_true", default=None, help="full wipe ID3 tags before writing new tags")
    g.add_argument("--no-wipe-id3", dest="wipe_id3", action="store_false", help="do not wipe ID3 tags (default)")
    pp.add_argument("--loudnorm", action="store_true", default=bool(ffmpeg.get("loudnorm", False)))
    pp.add_argument("--q-a", default=str(ffmpeg.get("q_a", "2")), help="lame VBR quality (2=high)")
    pp.add_argument("--split-chapters", dest="split_chapters", action="store_true", default=bool(cfg.get("split_chapters", True)))
    pp.add_argument("--no-split-chapters", dest="split_chapters", action="store_false")
    pp.add_argument("--cpu-cores", type=int, default=cfg.get("cpu_cores", None), help="override CPU core count for perf tuning")
    pp.add_argument("--ff-loglevel", choices=["info", "warning", "error"], default=str(ffmpeg.get("loglevel", "warning")))
    return pp


def _parse_args(cfg: Dict[str, Any] | None = None) -> argparse.Namespace:
    if cfg is None:
        cfg = load_config()
    parent = _parent_parser(cfg)

    ap = argparse.ArgumentParser(
        prog="audiomason",
        description="AudioMason – audiobook import & maintenance tool",
        parents=[parent],
    )
    ap.add_argument("--version", action="store_true", help="show version and exit")

    sub = ap.add_subparsers(dest="cmd")
    imp = sub.add_parser("import", help="import audiobooks from inbox", parents=[parent])
    imp.add_argument("path", nargs="?", type=Path, default=None, help="source path under DROP_ROOT")

    v = sub.add_parser("verify", help="verify audiobook library", parents=[parent])
    v.add_argument("root", nargs="?", type=Path, default=None)

    i = sub.add_parser("inspect", help="read-only source inspection", parents=[parent])
    i.add_argument("path", type=Path)

    ns = ap.parse_args()

    # argv fallback for quiet/verbose (argparse quirk)
    argv = set(sys.argv[1:])
    if "--quiet" in argv:
        ns.quiet = True
    if "--verbose" in argv:
        ns.verbose = True
        ns.quiet = False

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
        json=getattr(ns, "json", False),
    )


def main() -> int:
    pre = _parse_args({})
    cfg = load_config(pre.config) if pre.config else load_config()
    validate_paths_contract(cfg)
    ns = _parse_args(cfg)
    if state.DEBUG:
        from audiomason.util import out
        out(f"[config] loaded_from={cfg.get('loaded_from','unknown')}")

    # DEBUG wiring must be active before any out()/trace output
    state.DEBUG = bool(getattr(ns, "debug", False))
    state.VERBOSE = bool(getattr(ns, "verbose", False))
    if state.DEBUG:
        from audiomason.util import enable_trace
        enable_trace()

    if state.DEBUG:
        from audiomason.util import out
        out(f"[config] loaded_from={cfg.get('loaded_from','unknown')}")

    state.OPTS = _ns_to_opts(ns)
    if str(state.OPTS.verify_root) == "__AUDIOMASON_VERIFY_ROOT_UNSET__":
        state.OPTS.verify_root = get_output_root(cfg)

    if ns.cmd == "inspect":
        from audiomason.inspect import inspect_source
        inspect_source(ns.path)
        return 0

    if ns.cmd == "verify":
        root = ns.root or state.OPTS.verify_root
        verify_library(root)
        return 0

    try:
        run_import(cfg, getattr(ns, "path", None))
    except KeyboardInterrupt:
        from audiomason.util import out
        out("[abort] cancelled by user")
        return 130
    return 0
