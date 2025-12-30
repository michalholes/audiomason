from __future__ import annotations

from pathlib import Path
import shutil
import time

from .planner import build_candidates
from .normalize import path_component


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _clean_dir(p: Path):
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)


def _prompt(msg: str, default: str, yes: bool) -> str:
    if yes:
        return default
    s = input(f"{msg} [{default}]: ").strip()
    return s if s else default


def _stage_run(cfg: dict) -> Path:
    stage = Path(cfg["paths"]["stage"])
    ts = time.strftime("run-%Y%m%d-%H%M%S")
    return stage / ts


def _prepare_stage(cfg: dict, run: Path):
    stage_root = Path(cfg["paths"]["stage"])
    if cfg["behavior"].get("clean_stage_on_start", True):
        _clean_dir(stage_root)
    _ensure_dir(run / "src")


def _stage_input(input_path: Path, dst_src: Path):
    # v0.1: directory copy or single file copy.
    # (Unpack archives pridame v dalsom kroku.)
    if input_path.is_dir():
        shutil.copytree(input_path, dst_src, dirs_exist_ok=True)
    else:
        _ensure_dir(dst_src)
        shutil.copy2(input_path, dst_src / input_path.name)


def cmd_inspect(cfg: dict, path: Path) -> int:
    run = _stage_run(cfg)
    _prepare_stage(cfg, run)

    stage_src = run / "src"
    _stage_input(path, stage_src)

    allow_guess = bool(cfg.get("covers", {}).get("allow_guess_single_image_if_no_cover", True))
    cands = build_candidates(stage_src, allow_guess_single_image=allow_guess)

    print(f"FOUND {len(cands)} book candidate(s)\n")
    for i, c in enumerate(cands, 1):
        rel = c.root.relative_to(stage_src)
        print(f"[{i}] kind={c.kind} root={rel}")
        print(f"    audio={len(c.audio)} cover_candidates={len(c.cover_candidates)} sidecars={len(c.sidecars)}")
        print(f"    author_suggest={c.suggest_author!r}")
        print(f"    title_suggest={c.suggest_title!r}")
        if c.notes:
            print(f"    notes={','.join(c.notes)}")
        for cc in c.cover_candidates:
            print(f"    cover_candidate={cc.name}")
        print()
    return 0


def cmd_process(cfg: dict, path: Path, yes: bool) -> int:
    run = _stage_run(cfg)
    _prepare_stage(cfg, run)

    stage_src = run / "src"
    _stage_input(path, stage_src)

    ready = Path(cfg["paths"]["ready"])
    _ensure_dir(ready)

    allow_guess = bool(cfg.get("covers", {}).get("allow_guess_single_image_if_no_cover", True))
    cands = build_candidates(stage_src, allow_guess_single_image=allow_guess)

    use_spaces = bool(cfg.get("naming", {}).get("use_spaces_in_dirs", True))

    for c in cands:
        author_in = _prompt("Author (Surname.Name)", c.suggest_author, yes=yes)
        title_in = _prompt("Book", c.suggest_title, yes=yes)

        author_dir = path_component(author_in, use_spaces=False)  # Surname.Name stays ASCII
        book_dir = path_component(title_in, use_spaces=use_spaces)

        out_dir = ready / author_dir / book_dir
        print(f"[PLAN] {c.root.relative_to(stage_src)} -> {out_dir}")
        _ensure_dir(out_dir)

    if cfg["behavior"].get("clean_stage_on_success", True):
        _clean_dir(Path(cfg["paths"]["stage"]))
    return 0
