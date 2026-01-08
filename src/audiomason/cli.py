from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from audiomason.version import __version__
from audiomason.config import load_config, _validate_prompts_disable
import audiomason.state as state
from audiomason.state import Opts
from audiomason.import_flow import run_import
from audiomason.verify import verify_library
from audiomason.paths import validate_paths_contract, get_output_root
from audiomason.util import out, AmExit, AmAbort, AmConfigError


def _version_kv_line() -> str:
    # Stable, machine-readable version line (Feature #72)
    return f"audiomason_version={__version__}"
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

    # FEATURE #65: inbox cleanup control (delete processed source under DROP_ROOT)
    clean_inbox_default = cfg.get("clean_inbox", "no")
    pp.add_argument("--clean-inbox", choices=["ask", "yes", "no"], default=str(clean_inbox_default))
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
    # FEATURE #67: disable selected preflight prompts (repeatable, comma-separated)
    # Issue #74: optional per-source processing log (default off)
    gpl = imp.add_mutually_exclusive_group()
    gpl.add_argument(
        "--processing-log",
        dest="processing_log",
        action="store_true",
        default=False,
        help="save per-source processing log (.log) to stage (default off)",
    )
    gpl.add_argument(
        "--processing-log-path",
        dest="processing_log_path",
        type=Path,
        default=None,
        help="save per-source processing log (.log) to explicit file/dir (implies --processing-log)",
    )

    imp.add_argument(
        "--preflight-disable",
        dest="preflight_disable",
        action="append",
        default=None,
        help="disable selected preflight prompts (repeatable, comma-separated keys)",
    )

    # Issue #89: disable selected prompts at runtime (CLI overrides config)
    imp.add_argument(
        "--disable-prompt",
        dest="disable_prompt",
        action="append",
        default=None,
        help="disable prompts (repeatable, comma-separated keys; supports '*')",
    )

    v = sub.add_parser("verify", help="verify audiobook library", parents=[parent])
    v.add_argument("root", nargs="?", type=Path, default=None)

    i = sub.add_parser("inspect", help="read-only source inspection", parents=[parent])
    i.add_argument("path", type=Path)

    c = sub.add_parser("cache", help="cache maintenance", parents=[parent])
    csub = c.add_subparsers(dest="cache_cmd")
    gc = csub.add_parser("gc", help="prune cover disk cache", parents=[parent])
    gc.add_argument("--days", type=int, default=None, help="remove cache files older than N days")
    gc.add_argument("--max-mb", type=int, default=None, help="keep cache size under M megabytes (prune oldest)")


    ns = ap.parse_args()

    # argv fallback for quiet/verbose (argparse quirk)
    argv = set(sys.argv[1:])
    if "--quiet" in argv:
        ns.quiet = True
    if "--verbose" in argv:
        ns.verbose = True
        ns.quiet = False

    if ns.version:
        print(_version_kv_line())
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
        clean_inbox_mode=str(getattr(ns, 'clean_inbox', 'no')),
        split_chapters=ns.split_chapters,
        ff_loglevel=ns.ff_loglevel,
        cpu_cores=getattr(ns, 'cpu_cores', None),
        json=getattr(ns, "json", False),
    )


def main() -> int:
    try:
        try:
            pre = _parse_args({})
            # FIX: resolve --config path from argv before load_config (do not fall back to /etc)
            _argv_cfg = None
            _argv = list(sys.argv[1:])
            for _i, _a in enumerate(_argv):
                if _a == '--config' and _i + 1 < len(_argv):
                    _argv_cfg = Path(_argv[_i + 1])
                    break
                if _a.startswith('--config='):
                    _argv_cfg = Path(_a.split('=', 1)[1])
                    break
            cfg = load_config(_argv_cfg) if _argv_cfg else load_config()
            validate_paths_contract(cfg)
            ns = _parse_args(cfg)

            # Guard: argparse subparser parsing can reset store_true flags to defaults.
            # Recompute --json from argv so Feature #72 banner logic remains correct.
            if "--json" in sys.argv[1:]:
                setattr(ns, "json", True)
            # FIX: preserve --config from pre-parse into main parse (do not fall back to /etc)
            if getattr(pre, 'config', None):
                ns.config = pre.config

            # DEBUG wiring must be active before any out()/trace output
            # FEATURE: debug flag should be argv-driven (parse_args can drop ns.debug)
            argv = set(sys.argv[1:])
            state.DEBUG = ('--debug' in argv)
            state.VERBOSE = bool(getattr(ns, "verbose", False))
            if state.DEBUG:
                from audiomason.util import enable_trace
                enable_trace()
                out(f"[config] loaded_from={cfg.get('loaded_from','unknown')}")
                print(f"[TRACE] [config] loaded_from={cfg.get('loaded_from','unknown')}", flush=True)

            state.OPTS = _ns_to_opts(ns)

            # Issue #82: resolve OpenLibrary enablement (CLI > config)
            _ol_cfg = cfg.get('openlibrary', {})
            if not isinstance(_ol_cfg, dict):
                raise AmConfigError('Invalid config: openlibrary must be a mapping')
            _ol_cfg_enabled = bool(_ol_cfg.get('enabled', True))

            _argv = set(sys.argv[1:])
            if '--lookup' in _argv:
                _ol_cli = True
            elif '--no-lookup' in _argv:
                _ol_cli = False
            else:
                _ol_cli = None

            _ol_effective = (_ol_cli if _ol_cli is not None else _ol_cfg_enabled)
            state.OPTS.lookup = bool(_ol_effective)
            cfg['_openlibrary_enabled'] = bool(_ol_effective)

            # FEATURE #65: config default + debug print for clean_inbox
            argv = list(sys.argv[1:])
            argv_has_clean_inbox = ('--clean-inbox' in argv)
            if not argv_has_clean_inbox:
                cfg_mode = cfg.get('clean_inbox', 'no')
                state.OPTS.clean_inbox_mode = str(cfg_mode)

            if state.DEBUG:
                # Guaranteed visibility (don’t rely on out()/trace prefixing)
                print(f"[TRACE] [config] loaded_from={cfg.get('loaded_from','unknown')}", flush=True)
                print(f"[TRACE] [config] argv_has_clean_inbox={argv_has_clean_inbox}", flush=True)
                print(f"[TRACE] [config] clean_inbox_mode={state.OPTS.clean_inbox_mode}", flush=True)

            # FEATURE #65: enforce config default for --clean-inbox when flag not provided
            # (CLI always overrides config if user explicitly passes --clean-inbox)
            argv = set(sys.argv[1:])
            if '--clean-inbox' not in argv:
                cfg_mode = cfg.get('clean_inbox', 'no')
                state.OPTS.clean_inbox_mode = str(cfg_mode)

            if state.DEBUG:
                out(f"[config] clean_inbox_mode={state.OPTS.clean_inbox_mode}")
            if str(state.OPTS.verify_root) == "__AUDIOMASON_VERIFY_ROOT_UNSET__":
                state.OPTS.verify_root = get_output_root(cfg)

            # Issue #89: resolve prompts.disable (CLI overrides config)
            _dp = getattr(ns, "disable_prompt", None)
            if _dp is not None:
                items: list[str] = []
                for raw in _dp:
                    for part in str(raw).split(","):
                        k = part.strip()
                        if k:
                            items.append(k)
                if not items:
                    raise AmConfigError("Invalid --disable-prompt: no keys specified")

                prm = cfg.get("prompts", {})
                if prm is None:
                    prm = {}
                if not isinstance(prm, dict):
                    raise AmConfigError("Invalid config: prompts must be a mapping")

                prm2 = dict(prm)
                prm2["disable"] = items
                cfg["prompts"] = prm2
                if "_prompts_disable_set" in cfg:
                    del cfg["_prompts_disable_set"]
                _validate_prompts_disable(cfg)

            # Feature #72: version banner (configurable via config.yaml: version-banner)
            # Print only after config + CLI validation so fail-fast errors start with [error].
            _vb = bool(cfg.get('version-banner', True))
            if _vb and ((not state.OPTS.quiet) or bool(getattr(state.OPTS, 'json', False))):
                print(_version_kv_line(), flush=True)

            if ns.cmd == "inspect":
                from audiomason.inspect import inspect_source
                inspect_source(ns.path)
                return 0

            if ns.cmd == "verify":
                root = ns.root or state.OPTS.verify_root
                verify_library(root)
                return 0

            if ns.cmd == "cache":
                if getattr(ns, "cache_cmd", None) == "gc":
                    from audiomason.cache_gc import cache_gc
                    # command-local --dry-run can force report-only
                    # argparse quirk: both parent and subparser define --dry-run; keep ns.dry_run
                    return int(cache_gc(cfg, days=getattr(ns, "days", None), max_mb=getattr(ns, "max_mb", None), dry_run=bool(getattr(ns, "dry_run", False))))
                out("[error] unknown cache subcommand")
                return 2

            # Issue #74: resolve processing_log (CLI overrides config)
            _pl_cfg = cfg.get("processing_log", {})
            if not isinstance(_pl_cfg, dict):
                _pl_cfg = {}
            _pl_enabled = bool(_pl_cfg.get("enabled", False))
            _pl_path = _pl_cfg.get("path", None)
            if getattr(ns, "processing_log_path", None) is not None:
                _pl_enabled = True
                _pl_path = str(getattr(ns, "processing_log_path"))
            elif bool(getattr(ns, "processing_log", False)):
                _pl_enabled = True
                _pl_path = None
            cfg["processing_log"] = {"enabled": bool(_pl_enabled), "path": _pl_path}

            # FEATURE #67: resolve preflight_disable (CLI overrides config)
            _pd = getattr(ns, 'preflight_disable', None)
            if _pd:
                _items: list[str] = []
                for _raw in _pd:
                    for _part in str(_raw).split(','):
                        _k = _part.strip()
                        if _k:
                            _items.append(_k)
                cfg['preflight_disable'] = _items
            else:
                _d = cfg.get('preflight_disable', [])
                cfg['preflight_disable'] = list(_d) if isinstance(_d, list) else []

            run_import(cfg, getattr(ns, "path", None))
            return 0
        except KeyboardInterrupt as e:
            raise AmAbort("cancelled by user") from e
    except AmAbort as e:
        out(f"[abort] {e}")
        return e.exit_code
    except AmExit as e:
        out(f"[error] {e}")
        return e.exit_code

    except AmConfigError as e:
        out(f"[error] {e}")
        return 2
