from __future__ import annotations

import argparse
import sys
from getpass import getpass
from pathlib import Path
from typing import cast

import yaml

import audiomason.state as state
from audiomason.config import DEFAULTS, load_config, user_config_path, validate_prompts_disable
from audiomason.import_flow import run_import
from audiomason.paths import get_output_root, validate_paths_contract
from audiomason.preflight_resolve import resolve_bool_config
from audiomason.state import Opts
from audiomason.util import AmAbortError, AmConfigError, AmExitError, ensure_dir, out
from audiomason.verify import verify_library
from audiomason.version import __version__

SUPPORT_URL = "https://buymeacoffee.com/audiomason"
SUPPORT_LINE = f"Support AudioMason: {SUPPORT_URL}"


def _as_dict(value: object) -> dict[str, object]:
    return (
        cast(dict[str, object], value) if isinstance(value, dict) else cast(dict[str, object], {})
    )


def _version_kv_line() -> str:
    # Stable, machine-readable version line (Feature #72)
    return f"audiomason_version={__version__}"


def _parent_parser() -> argparse.ArgumentParser:
    # IMPORTANT (Issue #105):
    # Argument parsing must be pure and MUST NOT require config.
    #
    # Config-derived defaults are applied later (post-parse) only for commands
    # that actually require config.
    pp = argparse.ArgumentParser(add_help=False)
    pp.add_argument("--yes", action="store_true", help="non-interactive")
    pp.add_argument("--dry-run", action="store_true", help="do not modify anything")
    pp.add_argument("--quiet", action="store_true", help="less output")
    pp.add_argument("--verbose", action="store_true", help="more output (overrides --quiet)")
    pp.add_argument("--debug", action="store_true", help="prefix every out() line with [TRACE]")
    pp.add_argument("--json", action="store_true", help="print machine-readable JSON report at end")
    pp.add_argument("--config", type=Path, help="explicit configuration.yaml path")
    pp.add_argument("--verify", action="store_true", help="verify library after import")

    pp.add_argument("--verify-root", type=Path, default=None, help="root for --verify")

    g2 = pp.add_mutually_exclusive_group()
    g2.add_argument(
        "--lookup",
        dest="lookup",
        action="store_true",
        default=True,
        help="enable OpenLibrary validation",
    )
    g2.add_argument(
        "--no-lookup", dest="lookup", action="store_false", help="disable OpenLibrary validation"
    )

    _publish_choices: list[str] = ["yes", "no", "ask"]
    pp.add_argument("--publish", choices=_publish_choices, default=None)

    # FEATURE #65: inbox cleanup control (delete processed source under DROP_ROOT)
    _clean_inbox_choices: list[str] = ["ask", "yes", "no"]
    pp.add_argument("--clean-inbox", choices=_clean_inbox_choices, default=None)

    g = pp.add_mutually_exclusive_group()
    g.add_argument(
        "--wipe-id3",
        dest="wipe_id3",
        action="store_true",
        default=None,
        help="full wipe ID3 tags before writing new tags",
    )
    g.add_argument(
        "--no-wipe-id3",
        dest="wipe_id3",
        action="store_false",
        help="do not wipe ID3 tags (default)",
    )

    pp.add_argument("--loudnorm", action="store_true", default=None)
    pp.add_argument("--q-a", default=None, help="lame VBR quality (2=high)")

    pp.add_argument("--split-chapters", dest="split_chapters", action="store_true", default=None)
    pp.add_argument("--no-split-chapters", dest="split_chapters", action="store_false")

    pp.add_argument(
        "--cpu-cores", type=int, default=None, help="override CPU core count for perf tuning"
    )
    _ff_loglevel_choices: list[str] = ["info", "warning", "error"]
    pp.add_argument("--ff-loglevel", choices=_ff_loglevel_choices, default=None)
    return pp


def _parse_args() -> argparse.Namespace:
    parent = _parent_parser()

    ap = argparse.ArgumentParser(
        prog="audiomason",
        description="AudioMason – audiobook import & maintenance tool",
        parents=[parent],
    )
    ap.add_argument("--version", action="store_true", help="show version and exit")
    ap.add_argument("--support", action="store_true", help="show support link and exit")

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
        help=(
            "save per-source processing log (.log) to explicit file/dir (implies --processing-log)"
        ),
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

    # Issue #90 (amended): support banner after successful import (default on)
    imp.add_argument(
        "--no-support",
        dest="no_support",
        action="store_true",
        default=False,
        help="disable support banner after successful import",
    )

    v = sub.add_parser("verify", help="verify audiobook library", parents=[parent])
    v.add_argument("root", nargs="?", type=Path, default=None)

    i = sub.add_parser("inspect", help="read-only source inspection", parents=[parent])
    i.add_argument("path", type=Path)

    c = sub.add_parser("cache", help="cache maintenance", parents=[parent])
    csub = c.add_subparsers(dest="cache_cmd")
    gc = csub.add_parser("gc", help="prune cover disk cache", parents=[parent])
    gc.add_argument("--days", type=int, default=None, help="remove cache files older than N days")
    gc.add_argument(
        "--max-mb", type=int, default=None, help="keep cache size under M megabytes (prune oldest)"
    )

    sub.add_parser("init", help="interactive config wizard", parents=[parent])

    ns = ap.parse_args()

    # argv fallback for quiet/verbose (argparse quirk)
    argv = set(sys.argv[1:])
    if "--quiet" in argv:
        ns.quiet = True
    if "--verbose" in argv:
        ns.verbose = True
        ns.quiet = False

    if cast(bool, ns.support):
        print(SUPPORT_LINE)
        raise SystemExit(0)

    if cast(bool, ns.version):
        print(_version_kv_line())
        print(SUPPORT_LINE)
        raise SystemExit(0)

    if not cast(str, ns.cmd):
        ns.cmd = "import"

    if cast(bool, ns.verbose):
        ns.quiet = False

    return ns


def _cmd_requires_config(ns: argparse.Namespace) -> bool:
    # Commands that can run without config:
    # - --help / --version / --support handled during parsing (pre-main)
    # - inspect (pure filesystem)
    # - verify if explicit root is provided (positional root or --verify-root)
    if cast(str, ns.cmd) == "inspect":
        return False
    if cast(str, ns.cmd) == "init":
        return False
    if cast(str, ns.cmd) == "verify":
        root_val = cast(object, getattr(ns, "root", None))
        verify_root_val = cast(object, getattr(ns, "verify_root", None))
        return not bool(root_val or verify_root_val)
    # cache and import require config
    if cast(str, ns.cmd) in ("import", "cache"):
        return True
    # default safe stance: require config
    return True


def _apply_config_defaults(ns: argparse.Namespace, cfg: dict[str, object]) -> None:
    ffmpeg = _as_dict(cfg.get("ffmpeg"))
    paths = _as_dict(cfg.get("paths"))

    if cast(object, getattr(ns, "verify_root", None)) is None:
        vr_raw = paths.get("verify_root")
        vr_str: str = str(vr_raw) if isinstance(vr_raw, str) else "__AUDIOMASON_VERIFY_ROOT_UNSET__"
        default_verify_root = Path(vr_str)
        ns.verify_root = default_verify_root

    if cast(object, getattr(ns, "publish", None)) is None:
        publish_default: object = cfg.get("publish", "ask")
        if isinstance(publish_default, bool):
            publish_default = "yes" if publish_default else "no"
        ns.publish = str(publish_default)

    if cast(object, getattr(ns, "wipe_id3", None)) is None:
        ns.wipe_id3 = resolve_bool_config(cfg, "wipe_id3")

    if cast(object, getattr(ns, "clean_inbox", None)) is None:
        ns.clean_inbox = str(cfg.get("clean_inbox", "no"))

    if cast(object, getattr(ns, "loudnorm", None)) is None:
        ns.loudnorm = bool(ffmpeg.get("loudnorm", False))

    if cast(object, getattr(ns, "q_a", None)) is None:
        ns.q_a = str(ffmpeg.get("q_a", "2"))

    if cast(object, getattr(ns, "split_chapters", None)) is None:
        ns.split_chapters = bool(cfg.get("split_chapters", True))

    if cast(object, getattr(ns, "cpu_cores", None)) is None:
        ns.cpu_cores = cfg.get("cpu_cores")

    if cast(object, getattr(ns, "ff_loglevel", None)) is None:
        ns.ff_loglevel = str(ffmpeg.get("loglevel", "warning"))


def _argv_config_path() -> Path | None:
    _argv = list(sys.argv[1:])
    for _i, _a in enumerate(_argv):
        if _a == "--config" and _i + 1 < len(_argv):
            return Path(_argv[_i + 1])
        if _a.startswith("--config="):
            return Path(_a.split("=", 1)[1])
    return None


def _apply_builtin_defaults(ns: argparse.Namespace) -> None:
    # Fallback defaults used when config is intentionally not loaded.
    if cast(object, getattr(ns, "publish", None)) is None:
        ns.publish = "ask"
    if cast(object, getattr(ns, "clean_inbox", None)) is None:
        ns.clean_inbox = "no"
    if cast(object, getattr(ns, "loudnorm", None)) is None:
        ns.loudnorm = False
    if cast(object, getattr(ns, "q_a", None)) is None:
        ns.q_a = "2"
    if cast(object, getattr(ns, "split_chapters", None)) is None:
        ns.split_chapters = True
    if cast(object, getattr(ns, "ff_loglevel", None)) is None:
        ns.ff_loglevel = "warning"


def _wizard_prompt(msg: str, default: str | None = None, *, secret: bool = False) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    try:
        raw = getpass(f"{msg}:{suffix} ") if secret else input(f"{msg}:{suffix} ")
    except (KeyboardInterrupt, EOFError) as e:
        raise AmAbortError("cancelled by user") from e
    val = raw.strip()
    if val:
        return val
    return default or ""


def _wizard_prompt_yes_no(msg: str, default_no: bool = True) -> bool:
    suffix = "[y/N]" if default_no else "[Y/n]"
    try:
        ans = input(f"{msg} {suffix} ").strip().lower()
    except (KeyboardInterrupt, EOFError) as e:
        raise AmAbortError("cancelled by user") from e
    if not ans:
        return not default_no
    return ans in {"y", "yes"}


def _wizard_default_data_base() -> Path:
    return Path.home() / ".local" / "share" / "audiomason"


def _render_init_config(
    *,
    inbox: str,
    stage: str,
    output: str,
    archive: str,
    cache: str,
    enabled: bool,
    endpoint: str | None,
    model: str | None,
    api_key: str | None,
) -> str:
    payload: dict[str, object] = {
        "paths": {
            "inbox": inbox,
            "stage": stage,
            "output": output,
            "archive": archive,
            "cache": cache,
        }
    }

    ai_cfg: dict[str, object] = {"enabled": enabled}
    if enabled:
        ai_defaults = _as_dict(DEFAULTS.get("ai"))
        timeout_s = ai_defaults.get("timeout_s")
        max_completion_tokens = ai_defaults.get("max_completion_tokens")
        ai_cfg["provider"] = "openai_compatible"
        ai_cfg["endpoint"] = endpoint or str(ai_defaults.get("endpoint", ""))
        ai_cfg["model"] = model or str(ai_defaults.get("model", ""))
        ai_cfg["api_key"] = api_key or ""
        ai_cfg["timeout_s"] = int(timeout_s) if isinstance(timeout_s, (int, float)) else 20
        ai_cfg["max_completion_tokens"] = (
            int(max_completion_tokens) if isinstance(max_completion_tokens, int) else 80
        )

    payload["ai"] = ai_cfg
    body = yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=False)
    return (
        "# AudioMason user configuration\n"
        "# Set your filesystem roots first. The defaults below are safe per-user paths.\n\n"
        f"{body}"
    )


def _run_init_wizard(config_path: Path | None) -> int:
    target = config_path or user_config_path()
    if target.exists() and target.is_dir():
        raise AmConfigError(f"Config path is a directory: {target}")

    if target.exists() and not _wizard_prompt_yes_no(
        f"Config already exists at {target}. Overwrite?", default_no=True
    ):
        print(f"[info] Keeping existing config at {target}")
        return 0

    print(f"AudioMason init wizard -> {target}")
    base = _wizard_default_data_base()
    inbox = _wizard_prompt("Inbox path", str((base / "abooksinbox").resolve()))
    stage = _wizard_prompt("Stage path", str((base / "_am_stage").resolve()))
    output = _wizard_prompt("Output path", str((base / "abooks_ready").resolve()))
    archive = _wizard_prompt("Archive path", str((base / "abooks").resolve()))
    cache = _wizard_prompt("Cache path", str((base / ".cover_cache").resolve()))
    enable_ai = _wizard_prompt_yes_no("Enable AI metadata fallback now?", default_no=True)
    endpoint: str | None = None
    model: str | None = None
    api_key: str | None = None
    if enable_ai:
        ai_defaults = _as_dict(DEFAULTS.get("ai"))
        endpoint = _wizard_prompt("AI endpoint", str(ai_defaults.get("endpoint", "")))
        model = _wizard_prompt("AI model", str(ai_defaults.get("model", "")))
        while True:
            api_key = _wizard_prompt("AI secret / API key", secret=True)
            if api_key:
                break
            print("[error] AI secret cannot be empty")

    ensure_dir(target.parent)
    target.write_text(
        _render_init_config(
            inbox=inbox,
            stage=stage,
            output=output,
            archive=archive,
            cache=cache,
            enabled=enable_ai,
            endpoint=endpoint,
            model=model,
            api_key=api_key,
        ),
        encoding="utf-8",
    )
    target.chmod(0o600)
    print(f"[ok] Wrote {target}")
    if enable_ai:
        print(f"[ok] AI endpoint: {endpoint}")
    else:
        print("[ok] AI metadata fallback disabled")
    return 0


def _ns_to_opts(ns: argparse.Namespace) -> Opts:
    publish_key_raw: object = getattr(ns, "publish", None)
    publish_key: str = str(publish_key_raw) if publish_key_raw is not None else "ask"
    publish = {"yes": True, "no": False, "ask": None}[publish_key]
    return Opts(
        yes=cast(bool, ns.yes),
        dry_run=cast(bool, ns.dry_run),
        quiet=cast(bool, ns.quiet),
        publish=publish,
        wipe_id3=cast(bool | None, ns.wipe_id3),
        loudnorm=cast(bool, ns.loudnorm),
        q_a=cast(str, ns.q_a),
        verify=cast(bool, ns.verify),
        verify_root=cast(Path, ns.verify_root),
        lookup=cast(bool, getattr(ns, "lookup", True)),
        cleanup_stage=True,
        clean_inbox_mode=cast(str, getattr(ns, "clean_inbox", "no")),
        split_chapters=cast(bool, ns.split_chapters),
        ff_loglevel=cast(str, ns.ff_loglevel),
        cpu_cores=cast(int | None, getattr(ns, "cpu_cores", None)),
        json=cast(bool, getattr(ns, "json", False)),
    )


def main() -> int:
    try:
        try:
            ns = _parse_args()

            # argparse quirk: --config can be lost when subparsers are involved
            _cfgp = _argv_config_path()
            if _cfgp is not None:
                ns.config = _cfgp

            argv_set = set(sys.argv[1:])

            # DEBUG wiring must be active before any out()/trace output
            state.DEBUG = "--debug" in argv_set
            state.VERBOSE = cast(bool, getattr(ns, "verbose", False))
            if state.DEBUG:
                from audiomason.trace_ops import enable_trace

                enable_trace()

            # argparse quirk: --json can be lost when subparsers are involved
            if "--json" in argv_set:
                ns.json = True

            if cast(str, ns.cmd) == "init":
                _apply_builtin_defaults(ns)
                state.OPTS = _ns_to_opts(ns)
                return _run_init_wizard(cast(Path | None, getattr(ns, "config", None)))

            cfg: dict[str, object] | None = None
            if _cmd_requires_config(ns):
                # Issue #105: config is loaded lazily ONLY after args are parsed and
                # only for commands that actually require it.
                cfg = load_config(cast(Path | None, getattr(ns, "config", None)))
                validate_paths_contract(cfg)
                _apply_config_defaults(ns, cfg)
            else:
                _apply_builtin_defaults(ns)

            # Issue #82: resolve metadata lookup enablement (CLI > config)
            if "--lookup" in argv_set:
                _ol_cli = True
            elif "--no-lookup" in argv_set:
                _ol_cli = False
            else:
                _ol_cli = None

            if "--ai-lookup" in argv_set:
                _ai_cli = True
            elif "--no-ai-lookup" in argv_set:
                _ai_cli = False
            else:
                _ai_cli = None

            if cfg is not None:
                _ol_cfg = _as_dict(cfg.get("openlibrary"))
                _ol_effective = (
                    _ol_cli if _ol_cli is not None else bool(_ol_cfg.get("enabled", True))
                )
                cfg["_openlibrary_enabled"] = bool(_ol_effective)

                _ai_cfg = _as_dict(cfg.get("ai"))
                _ai_effective = (
                    _ai_cli if _ai_cli is not None else bool(_ai_cfg.get("enabled", False))
                )
                cfg["_ai_enabled"] = bool(_ai_effective)
            else:
                _ol_effective = _ol_cli if _ol_cli is not None else cast(bool, ns.lookup)
                _ai_effective = _ai_cli if _ai_cli is not None else cast(bool, ns.ai_lookup)

            ns.lookup = bool(_ol_effective)
            ns.ai_lookup = bool(_ai_effective)

            state.OPTS = _ns_to_opts(ns)

            if state.DEBUG:
                if cfg is not None:
                    print(
                        f"[TRACE] [config] loaded_from={cfg.get('loaded_from', 'unknown')}",
                        flush=True,
                    )
                else:
                    print("[TRACE] [config] not loaded", flush=True)

            # Non-config commands must work without config (Issue #105).
            if cast(str, ns.cmd) == "inspect":
                from audiomason.inspect import inspect_source

                inspect_source(cast(Path, ns.path))
                return 0

            if cast(str, ns.cmd) == "verify" and cfg is None:
                root = cast(Path | None, getattr(ns, "root", None)) or state.OPTS.verify_root
                verify_library(root, None)
                return 0

            # From here on, commands are config-dependent.
            assert cfg is not None

            # FEATURE #65: config default for clean_inbox when flag not provided
            argv_list = list(sys.argv[1:])
            argv_has_clean_inbox = "--clean-inbox" in argv_list
            if not argv_has_clean_inbox:
                cfg_mode: object = cfg.get("clean_inbox", "no")
                state.OPTS.clean_inbox_mode = str(cfg_mode)

            if state.DEBUG:
                print(f"[TRACE] [config] argv_has_clean_inbox={argv_has_clean_inbox}", flush=True)
                print(
                    f"[TRACE] [config] clean_inbox_mode={state.OPTS.clean_inbox_mode}", flush=True
                )

            if str(state.OPTS.verify_root) == "__AUDIOMASON_VERIFY_ROOT_UNSET__":
                state.OPTS.verify_root = get_output_root(cfg)

            # Issue #89: resolve prompts.disable (CLI overrides config)
            _dp = cast(object, getattr(ns, "disable_prompt", None))
            if _dp is not None:
                items: list[str] = []
                for raw in cast(list[object], _dp):
                    for part in str(raw).split(","):
                        k = part.strip()
                        if k:
                            items.append(k)
                if not items:
                    raise AmConfigError("Invalid --disable-prompt: no keys specified")

                prm = _as_dict(cfg.get("prompts"))
                prm2 = dict(prm)
                prm2["disable"] = items
                cfg["prompts"] = prm2
                if "_prompts_disable_set" in cfg:
                    del cfg["_prompts_disable_set"]
                validate_prompts_disable(cfg)

            # Feature #72: version banner (configurable via config.yaml: version-banner)
            _vb = bool(cfg.get("version-banner", True))
            if _vb and ((not state.OPTS.quiet) or cast(bool, getattr(state.OPTS, "json", False))):
                print(_version_kv_line(), flush=True)

            if cast(str, ns.cmd) == "verify":
                root = cast(Path | None, getattr(ns, "root", None)) or state.OPTS.verify_root
                verify_library(root, cfg)
                return 0

            if cast(str, ns.cmd) == "cache":
                if cast(object, getattr(ns, "cache_cmd", None)) == "gc":
                    from audiomason.cache_gc import cache_gc

                    return int(
                        cache_gc(
                            cfg,
                            days=cast(int | None, getattr(ns, "days", None)),
                            max_mb=cast(int | None, getattr(ns, "max_mb", None)),
                            dry_run=cast(bool, getattr(ns, "dry_run", False)),
                        )
                    )
                out("[error] unknown cache subcommand")
                return 2

            # Issue #74: resolve processing_log (CLI overrides config)
            _pl_cfg = _as_dict(cfg.get("processing_log"))
            _pl_enabled = bool(_pl_cfg.get("enabled", False))
            _pl_path: str | None = cast(str | None, _pl_cfg.get("path"))
            if cast(object, getattr(ns, "processing_log_path", None)) is not None:
                _pl_enabled = True
                _pl_path = str(cast(object, ns.processing_log_path))
            elif cast(bool, getattr(ns, "processing_log", False)):
                _pl_enabled = True
                _pl_path = None
            cfg["processing_log"] = {"enabled": bool(_pl_enabled), "path": _pl_path}

            # FEATURE #67: resolve preflight_disable (CLI overrides config)
            _pd = cast(object, getattr(ns, "preflight_disable", None))
            if _pd:
                _items: list[str] = []
                for _raw in cast(list[object], _pd):
                    for _part in str(_raw).split(","):
                        _k = _part.strip()
                        if _k:
                            _items.append(_k)
                cfg["preflight_disable"] = _items
            else:
                raw_fd: object = cfg.get("preflight_disable", [])
                if isinstance(raw_fd, list):
                    cfg["preflight_disable"] = cast(list[object], raw_fd)
                else:
                    cfg["preflight_disable"] = []

            run_import(cfg, cast(Path | None, getattr(ns, "path", None)))

            # Issue #90 (amended): banner shows by default after import.
            # Disabled in machine/silent modes (--quiet / --json)
            # and when user disables via CLI or config.
            support_enabled = True
            if cast(bool, getattr(state.OPTS, "quiet", False)) or cast(
                bool, getattr(state.OPTS, "json", False)
            ):
                support_enabled = False
            if cast(bool, getattr(ns, "no_support", False)):
                support_enabled = False
            sup_cfg = _as_dict(cfg.get("support"))
            if sup_cfg.get("enabled", True) is False:
                support_enabled = False
            if support_enabled:
                print(SUPPORT_LINE)

            return 0
        except KeyboardInterrupt as e:
            raise AmAbortError("cancelled by user") from e
    except AmAbortError as e:
        out(f"[abort] {e}")
        return e.exit_code
    except AmExitError as e:
        out(f"[error] {e}")
        return e.exit_code
