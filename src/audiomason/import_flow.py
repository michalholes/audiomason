
from __future__ import annotations

import io
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import audiomason.state as state
from audiomason.archives import unpack
from audiomason.audio import convert_m4a_in_place, convert_opus_in_place
from audiomason.covers import (
    choose_cover,
    cover_from_input,
    extract_embedded_cover_from_mp3,
    find_file_cover,
)
from audiomason.ignore import add_ignore, load_ignore
from audiomason.manifest import load_manifest, source_fingerprint, update_manifest
from audiomason.naming import normalize_name, normalize_sentence
from audiomason.openlibrary import validate_author, validate_book
from audiomason.paths import (
    ARCHIVE_EXTS,
    get_archive_root,
    get_drop_root,
    get_output_root,
    get_stage_root,
)
from audiomason.pipeline_steps import resolve_pipeline_steps
from audiomason.preflight_orchestrator import PreflightContext, PreflightOrchestrator
from audiomason.preflight_registry import DEFAULT_PREFLIGHT_STEPS, validate_steps_list
from audiomason.rename import natural_sort, rename_sequential
from audiomason.tags import wipe_id3, write_cover, write_tags
from audiomason.util import AmConfigError, die, ensure_dir, out, prompt, prompt_yes_no, slug

# FEATURE #67: disable selected preflight prompts (skip prompts deterministically)

# Issue #82: OpenLibrary master switch
def _ol_enabled(cfg: dict) -> bool:
    return bool(cfg.get('_openlibrary_enabled', True))

PREFLIGHT_DISABLE_KEYS = {
    'publish',
    'wipe_id3',
    'clean_stage',
    'clean_inbox',
    'reuse_stage',
    'use_manifest_answers',
    'normalize_author',
    'normalize_book_title',
    'cover',
}

# Issue #66: configurable preflight question order (deterministic, validated)
PREFLIGHT_STEP_KEYS = list(DEFAULT_PREFLIGHT_STEPS)


def _resolved_preflight_steps(cfg: dict) -> list[str]:
    cached = cfg.get('_preflight_steps_list')
    if isinstance(cached, list) and all(isinstance(x, str) for x in cached):
        return cached

    raw = cfg.get('preflight_steps', None)
    if raw is None:
        cfg['_preflight_steps_list'] = list(PREFLIGHT_STEP_KEYS)
        return cfg['_preflight_steps_list']
    if not isinstance(raw, list):
        raise AmConfigError('Invalid config: preflight_steps must be a list of step keys')

    try:
        out_list = validate_steps_list(raw)
    except Exception as e:
        msg = str(e).strip()
        if msg.startswith('duplicate preflight step key: '):
            raise AmConfigError('Invalid config: duplicate preflight_steps key: ' + msg.split(': ', 1)[1])
        if msg.startswith('unknown preflight step key: '):
            raise AmConfigError('Invalid config: unknown preflight_steps key: ' + msg.split(': ', 1)[1])
        if msg.startswith('missing required preflight step key(s): '):
            raise AmConfigError('Invalid config: missing required preflight_steps key(s): ' + msg.split(': ', 1)[1])
        if msg.startswith('order requires '):
            raise AmConfigError('Invalid config: preflight_steps order requires ' + msg[len('order requires '):])
        raise AmConfigError('Invalid config: ' + msg)

    cfg['_preflight_steps_list'] = out_list
    return out_list

def _resolved_preflight_disable(cfg: dict) -> set[str]:
    # Cache the resolved set on cfg to avoid repeated parsing.
    cached = cfg.get('_preflight_disable_set')
    if isinstance(cached, set):
        return cached
    raw = cfg.get('preflight_disable', [])
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise AmConfigError('Invalid config: preflight_disable must be a list of keys')
    out_set: set[str] = set()
    for x in raw:
        k = str(x).strip()
        if not k:
            continue
        if k not in PREFLIGHT_DISABLE_KEYS:
            raise AmConfigError(f'Invalid config: unknown preflight_disable key: {k}')
        out_set.add(k)
    cfg['_preflight_disable_set'] = out_set
    return out_set

def _resolved_prompts_disable(cfg: dict) -> set[str]:
    # Cache the resolved set on cfg to avoid repeated parsing.
    cached = cfg.get('_prompts_disable_set')
    if isinstance(cached, set):
        return cached
    prm = cfg.get('prompts', {})
    if prm is None:
        prm = {}
    if not isinstance(prm, dict):
        raise AmConfigError("Invalid config: prompts must be a mapping")
    raw = prm.get('disable', [])
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise AmConfigError("Invalid config: prompts.disable must be a list")
    seen: set[str] = set()
    for x in raw:
        if not isinstance(x, str):
            raise AmConfigError("Invalid config: prompts.disable items must be strings")
        if x in seen:
            raise AmConfigError(f"Invalid config: duplicate prompts.disable key: {x}")
        seen.add(x)
    if "*" in seen and len(seen) != 1:
        raise AmConfigError("Invalid config: prompts.disable cannot combine '*' with other keys")
    unknown = sorted(k for k in seen if k != "*" and k not in {
        "normalize_author","normalize_book_title","publish","wipe_id3","reuse_stage","cover",
        "choose_source","choose_books","skip_processed_books","overwrite_destination",
        "source_author","book_title","choose_cover","cover_input",
    })
    if unknown:
        raise AmConfigError(f"Invalid config: unknown prompts.disable key(s): {', '.join(unknown)}")
    cfg['_prompts_disable_set'] = seen
    return seen

def _prompt_disabled(cfg: dict, key: str) -> bool:
    ds = _resolved_prompts_disable(cfg)
    return "*" in ds or key in ds

def _pf_disabled(cfg: dict, key: str) -> bool:
    return _prompt_disabled(cfg, key) or (key in _resolved_preflight_disable(cfg))

def _pf_prompt_yes_no(cfg: dict, key: str, question: str, *, default_no: bool) -> bool:
    # Disabled => behave like pressing Enter (use existing defaults).
    if _pf_disabled(cfg, key):
        ret = (not default_no)
        if state.DEBUG:
            out(f"[TRACE] [preflight] disabled: {key} -> default: {'no' if default_no else 'yes'}")
        return ret
    return prompt_yes_no(question, default_no=default_no)

def _pf_prompt(cfg: dict, key: str, question: str, default: str) -> str:
    # Disabled => behave like pressing Enter (use default argument).
    if _pf_disabled(cfg, key):
        if state.DEBUG:
            out(f"[TRACE] [preflight] disabled: {key} -> default: {default}")
        return default
    return prompt(question, default)

_AUDIO_EXTS = {".mp3", ".m4a", ".opus"}

# Issue #75: prefix destination with source name when importing all sources ('a')
_SOURCE_PREFIX: Optional[str] = None


@dataclass(frozen=True)
class BookGroup:
    label: str
    group_root: Path        # directory containing audio (non-recursive)
    stage_root: Path        # stage src root
    rel_path: Path = field(default_factory=lambda: Path("."))
    m4a_hint: Optional[Path] = None

def _build_json_report(stage_runs: list[Path]) -> dict:
    # Deterministic: derived from manifest.json only
    sources: list[dict] = []
    books: list[dict] = []
    decisions: list[dict] = []
    total_books = 0
    processed_books = 0
    for sr in stage_runs:
        mf = load_manifest(sr)
        src = mf.get('source', {}) if isinstance(mf, dict) else {}
        binfo = mf.get('books', {}) if isinstance(mf, dict) else {}
        dec = mf.get('decisions', {}) if isinstance(mf, dict) else {}
        bm = mf.get('book_meta', {}) if isinstance(mf, dict) else {}
        picked = binfo.get('picked') if isinstance(binfo, dict) else None
        detected = binfo.get('detected') if isinstance(binfo, dict) else None
        processed = binfo.get('processed') if isinstance(binfo, dict) else None
        picked_l = [str(x) for x in picked] if isinstance(picked, list) else []
        detected_l = [str(x) for x in detected] if isinstance(detected, list) else []
        processed_l = [str(x) for x in processed] if isinstance(processed, list) else []
        total_books += len(picked_l)
        processed_books += len(processed_l)

        sources.append({
            'name': str(src.get('name') or ''),
            'stem': str(src.get('stem') or ''),
            'path': str(src.get('path') or ''),
            'fingerprint': str(src.get('fingerprint') or ''),
            'detected_books': detected_l,
            'picked_books': picked_l,
            'processed_books': processed_l,
        })

        decisions.append({
            'source_stem': str(src.get('stem') or ''),
            'publish': (bool(dec.get('publish')) if isinstance(dec, dict) and ('publish' in dec) else None),
            'wipe_id3': (bool(dec.get('wipe_id3')) if isinstance(dec, dict) and ('wipe_id3' in dec) else None),
            'author': (str(dec.get('author') or '') if isinstance(dec, dict) else ''),
            'clean_stage': (bool(dec.get('clean_stage')) if isinstance(dec, dict) and ('clean_stage' in dec) else None),
        })

        author = str(dec.get('author') or '') if isinstance(dec, dict) else ''
        if isinstance(bm, dict):
            for label, meta in sorted(bm.items(), key=lambda kv: str(kv[0])):
                m2 = meta if isinstance(meta, dict) else {}
                title = str(m2.get('title') or '')
                out_title = str(m2.get('out_title') or '') or title
                books.append({
                    'source_stem': str(src.get('stem') or ''),
                    'label': str(label),
                    'author': author,
                    'title': title,
                    'out_title': out_title,
                    'dest_kind': str(m2.get('dest_kind') or ''),
                    'cover_mode': str(m2.get('cover_mode') or ''),
                    'overwrite': bool(m2.get('overwrite') is True),
                    'result': ('processed' if str(label) in processed_l else 'pending'),
                })

    return {
        'sources': sources,
        'books': books,
        'decisions': decisions,
        'results': {
            'sources_total': len(sources),
            'books_total': total_books,
            'books_processed': processed_books,
        },
    }


def _ol_offer_top(kind: str, entered: str, res, *, cfg: dict, key: str) -> str:
    if not _ol_enabled(cfg):
        return entered
    top = getattr(res, "top", None)
    if isinstance(top, str):
        top = top.strip()
    if not top:
        return entered
    e = (entered or "").strip()
    if top.casefold() == e.casefold():
        return entered
    from audiomason.util import out
    out(f"[ol] {kind} suggestion: '{e}' -> '{top}'")
    if _pf_prompt_yes_no(cfg, key, f"Use suggested {kind} '{top}'?", default_no=True):
        return top
    return entered

def _list_sources(drop_root: Path) -> list[Path]:
    # Filter ignored sources here so they never appear in the prompt list.
    import unicodedata

    from audiomason.ignore import load_ignore
    from audiomason.util import slug

    def _norm(s: str) -> str:
        return unicodedata.normalize("NFKC", s).strip().casefold()

    ignore_raw = load_ignore(drop_root)
    ignore_norm = {_norm(k) for k in ignore_raw}
    ignore_norm |= {_norm(slug(k)) for k in ignore_raw}

    if not drop_root.exists():
        ensure_dir(drop_root)
        return []

    items: list[Path] = []
    for src in sorted(drop_root.iterdir(), key=lambda x: x.name.lower()):
        name = src.name
        if name.startswith("."):
            continue
        # never treat internal/work artifacts as sources
        if name in {"_am_stage", "import.log.jsonl", ".DS_Store"}:
            continue
        if name.startswith("_"):
            continue

        # allow only dirs + supported archives
        if src.is_file() and src.suffix.lower() not in ARCHIVE_EXTS:
            continue
        if not (src.is_dir() or (src.is_file() and src.suffix.lower() in ARCHIVE_EXTS)):
            continue

        candidates = {
            _norm(src.name),
            _norm(src.stem),
            _norm(slug(src.name)),
            _norm(slug(src.stem)),
        }
        if candidates & ignore_norm:
            continue

        items.append(src)

    return items


def _choose_source(cfg: dict, sources: list[Path]) -> list[Path]:
    if not sources:
        out("[inbox] empty")
        return []
    out("[inbox] sources:")
    for i, p in enumerate(sources, 1):
        out(f"  {i}) {p.name}")
    else:
        ans = _pf_prompt(cfg, 'choose_source', "Choose source number, or 'a' for all", "1").strip().lower()
    if ans == "a":
        return sources
    try:
        n = int(ans)
        if 1 <= n <= len(sources):
            return [sources[n - 1]]
    except Exception:
        pass
    die("Invalid source selection")
    return []


def _reset_dir(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)
    ensure_dir(p)


def _stage_source(src: Path, stage_src: Path) -> None:
    _reset_dir(stage_src)
    if src.is_dir():
        # copy tree into stage (deterministic)
        for item in src.rglob("*"):
            rel = item.relative_to(src)
            dst = stage_src / rel
            if item.is_dir():
                ensure_dir(dst)
            else:
                ensure_dir(dst.parent)
                shutil.copy2(item, dst)
        return

    if src.is_file() and src.suffix.lower() in ARCHIVE_EXTS:
        unpack(src, stage_src)
        return

    die(f"Unsupported source: {src}")


def _has_audio_files_here(p: Path) -> bool:
    for f in p.iterdir():
        if f.is_file() and f.suffix.lower() in _AUDIO_EXTS:
            return True
    return False


def _find_first_m4a(p: Path) -> Optional[Path]:
    for f in sorted(p.rglob("*.m4a"), key=lambda x: x.as_posix().lower()):
        if f.is_file():
            return f
    return None


# [issue_75] _detect_books
def _detect_books(stage_src: Path) -> list[BookGroup]:
    books: list[BookGroup] = []

    if not (stage_src.exists() and stage_src.is_dir()):
        die(f"Source is not a directory: {stage_src}")

    pairs: list[tuple[str, Path]] = []

    # Root audio => '__ROOT_AUDIO__' (and still include nested books)
    if _has_audio_files_here(stage_src):
        pairs.append(("__ROOT_AUDIO__", stage_src))

    def visit(d: Path, rel: Path) -> None:
        if d != stage_src and _has_audio_files_here(d):
            pairs.append((rel.as_posix(), d))
        subdirs = sorted([x for x in d.iterdir() if x.is_dir()], key=lambda p: p.name.casefold())
        for sd in subdirs:
            visit(sd, rel / sd.name)

    for top in sorted([x for x in stage_src.iterdir() if x.is_dir()], key=lambda p: p.name.casefold()):
        visit(top, Path(top.name))

    for rel_s, root in sorted(pairs, key=lambda t: t[0].casefold()):
        label = rel_s
        rp = Path('.') if rel_s == '__ROOT_AUDIO__' else Path(rel_s)
        books.append(BookGroup(label=label, group_root=root, stage_root=stage_src, m4a_hint=_find_first_m4a(root), rel_path=rp))

    if not books:
        die("No books found in source (no mp3/m4a in any directory)")
    return books

def _choose_books(cfg: dict, books: list[BookGroup], default_ans: str = "1") -> list[BookGroup]:
    # Issue #76: allow disabling choose_books prompt deterministically.
    if len(books) == 1:
        return books
    out(f"[books] found {len(books)}:")
    for i, b in enumerate(books, 1):
        out(f"  {i}) {b.label}")
    ans = _pf_prompt(cfg, "choose_books", "Choose book number, or 'a' for all", default_ans).strip().lower()
    if ans == "a":
        return books
    try:
        n = int(ans)
        if 1 <= n <= len(books):
            return [books[n - 1]]
    except Exception:
        pass
    die("Invalid book selection")
    return []

    if len(books) == 1:
        return books
    out(f"[books] found {len(books)}:")
    for i, b in enumerate(books, 1):
        out(f"  {i}) {b.label}")
    ans = _pf_prompt(cfg, "choose_books", "Choose book number, or 'a' for all", default_ans).strip().lower()
    if ans == "a":
        return books
    try:
        n = int(ans)
        if 1 <= n <= len(books):
            return [books[n - 1]]
    except Exception:
        pass
    die("Invalid book selection")
    return []


# [issue_75] _collect_audio_files
def _collect_audio_files(group_root: Path) -> list[Path]:
    mp3s = sorted([p for p in group_root.iterdir() if p.is_file() and p.suffix.lower() == ".mp3"], key=lambda p: p.name.casefold())
    m4as = sorted([p for p in group_root.iterdir() if p.is_file() and p.suffix.lower() == ".m4a"], key=lambda p: p.name.casefold())
    opuses = sorted([p for p in group_root.iterdir() if p.is_file() and p.suffix.lower() == ".opus"], key=lambda p: p.name.casefold())
    return mp3s + m4as + opuses
def _preflight_global(cfg: dict) -> tuple[bool, bool]:
    # publish (placeholder, but must be decided before processing)
    if state.OPTS.publish is None:
        pub = _pf_prompt_yes_no(cfg, 'publish', "Publish after import?", default_no=True)
    else:
        pub = bool(state.OPTS.publish)

    # wipe ID3 decision
    if state.OPTS.wipe_id3 is None:
        wipe = _pf_prompt_yes_no(cfg, 'wipe_id3', "Full wipe ID3 tags before tagging?", default_no=True)

    else:
        wipe = bool(state.OPTS.wipe_id3)

    return (pub, wipe)


def _preflight_book(cfg: dict, i: int, n: int, b: BookGroup, default_title: str = "") -> str:
    out(f"[book-meta] {i}/{n}: {b.label}")
    default_title = (default_title or (b.label if b.label != "__ROOT_AUDIO__" else "Untitled"))
    if _prompt_disabled(cfg, 'book_title'):
        title = default_title.strip()
    else:
        title = prompt(f"[book {i}/{n}] Book title", default_title).strip()
    nt = normalize_sentence(title)
    if nt != title:
        out(f"[name] book suggestion: '{title}' -> '{nt}'")
        if _pf_prompt_yes_no(cfg, 'normalize_book_title', "Apply suggested book title?", default_no=True):
            title = nt

    if not title:
        die("Book title is required")
    return title

def _is_dir_nonempty(p: Path) -> bool:
    return p.exists() and p.is_dir() and any(p.iterdir())

def _next_available_title(author_dir: Path, title: str) -> str:
    # Deterministic: Title, Title (2), Title (3), ...
    if not author_dir.exists():
        return title
    if not _is_dir_nonempty(author_dir / title) and not (author_dir / title).exists():
        return title
    n = 2
    while True:
        cand = f"{title} ({n})"
        if not (author_dir / cand).exists() and not _is_dir_nonempty(author_dir / cand):
            return cand
        n += 1

# [issue_75] _output_dir
# [issue_75_v4] _output_dir
def _output_dir(archive_root: Path, author: str, title: str) -> Path:
    # Strict mapping: archive_root / author / title
    if author is None or title is None:
        die("Empty author/title (refusing to construct output path)")

    author_s = str(author)
    title_s = str(title)

    if not author_s.strip() or not title_s.strip():
        die("Empty author/title (refusing to construct output path)")

    # Guard against separators / traversal.
    if "/" in author_s or "\\" in author_s or author_s in {".", ".."}:
        die(f"Invalid author for output path: {author_s!r}")
    if "/" in title_s or "\\" in title_s or title_s in {".", ".."}:
        die(f"Invalid title for output path: {title_s!r}")

    return archive_root / author_s / title_s

def _copy_audio_to_out_no_rename(group_root: Path, outdir: Path) -> list[Path]:
    ensure_dir(outdir)
    src_mp3s = _collect_audio_files(group_root)
    if not src_mp3s:
        die("No audio files to import (no mp3/m4a/opus found)")
    copied: list[Path] = []
    for p in src_mp3s:
        dst = outdir / p.name
        shutil.copy2(p, dst)
        copied.append(dst)
    return natural_sort(copied)


def _copy_audio_to_out_raw(group_root: Path, outdir: Path) -> list[Path]:
    ensure_dir(outdir)
    src_mp3s = _collect_audio_files(group_root)
    if not src_mp3s:
        die("No audio files to import (no mp3/m4a/opus found)")
    copied: list[Path] = []
    for p in src_mp3s:
        dst = outdir / p.name
        shutil.copy2(p, dst)
        copied.append(dst)
    return natural_sort(copied)


def _copy_audio_to_out(group_root: Path, outdir: Path) -> list[Path]:
    copied = _copy_audio_to_out_raw(group_root, outdir)
    return rename_sequential(outdir, copied)
def _apply_book_steps(
    *,
    steps: list[str],
    mp3s: list[Path],
    outdir: Path,
    author: str,
    title: str,
    out_title: str,
    i: int,
    n: int,
    b: BookGroup,
    cfg: dict,
    cover_mode: str,
) -> list[Path]:
    # Only PROCESS-phase steps are applied here.
    # Unknown steps are validated earlier by resolve_pipeline_steps().
    for st in steps:
        if st == "rename":
            mp3s = rename_sequential(outdir, mp3s)
        elif st == "tags":
            write_tags(mp3s, artist=author, album=title, track_start=1, cover=None, cover_mime=None)
        elif st == "cover":
            mp3_first = mp3s[0] if mp3s else None
            cover = choose_cover(
                cfg=cfg,
                mp3_first=mp3_first,
                m4a_source=b.m4a_hint,
                bookdir=outdir,
                stage_root=b.stage_root,
                group_root=b.group_root,
                mode=cover_mode,
            )
            cover_bytes = cover[0] if cover else None
            cover_mime = cover[1] if cover else None
            write_cover(mp3s, cover=cover_bytes, cover_mime=cover_mime)
        elif st == "publish":
            # publish is resolved earlier via dest_root choice; keep step for ordering/visibility
            pass
        else:
            # unpack/convert/chapters/split are stage-level in this codebase
            pass
    return mp3s

def _write_dry_run_summary(stage_run: Path, author: str, title: str, lines: list[str]) -> None:
    name = f"{author} - {title}.dryrun.txt"
    path = stage_run / name
    header = [
        "AudioMason dry-run summary",
        "",
    ]
    path.write_text("\n".join(header + lines) + "\n", encoding="utf-8")

def _process_book(i: int, n: int, b: BookGroup, stage_run: Path, dest_root: Path, author: str, title: str, out_title: str, wipe: bool, cover_mode: str, overwrite: bool, cfg: dict, final_root: Path, steps: list[str]) -> None:
    out(f"[book] {i}/{n}: {b.label}")

    outdir = _output_dir(dest_root, author, out_title)
    if _is_dir_nonempty(outdir):
        if overwrite:
            if state.OPTS and state.OPTS.dry_run:
                out(f"[dest] would overwrite: {outdir}")
            else:
                out(f"[dest] overwrite: {outdir}")
            if not (state.OPTS and state.OPTS.dry_run):
                shutil.rmtree(outdir, ignore_errors=True)
        else:
            die(f"Conflict: output already exists and is not empty: {outdir}")

    if state.OPTS.dry_run:
        out(f"[dry-run] would create: {outdir}")
        # ISSUE #2: write human-readable dry-run summary file (per book)
        lines = [
            "AudioMason dry-run summary",
            f"Author: {author}",
            f"Title: {out_title}",
            f"Destination root: {dest_root}",
            f"Destination dir: {outdir}",
            f"Overwrite: {bool(overwrite)}",
            f"Cover mode: {cover_mode}",
            f"Wipe ID3: {bool(wipe)}",
            f"Pipeline steps: {' -> '.join(steps)}",
        ]
        _write_dry_run_summary(stage_run, author, out_title, lines)
        out(f"[dry-run] wrote: {stage_run / (author + ' - ' + out_title + '.dryrun.txt')}")
        return
    mp3s = _copy_audio_to_out_no_rename(b.group_root, outdir)

    # [issue_86] PROCESS-only conversion (m4a/opus -> mp3)
    convert_m4a_in_place(outdir, recursive=False)
    convert_opus_in_place(outdir, recursive=False)
    mp3s = natural_sort([p for p in outdir.iterdir() if p.is_file() and p.suffix.lower() == '.mp3'])
    if not mp3s:
        die('No mp3 files to import after conversion')

    # Preserve embedded cover across ID3 wipe (Issue #55)
    _embedded_cover = None
    if wipe and mp3s:
        try:
            _embedded_cover = extract_embedded_cover_from_mp3(mp3s[0])
        except Exception:
            _embedded_cover = None

    if wipe:
        wipe_id3(mp3s)
        if _embedded_cover:
            try:
                data, mime = _embedded_cover
                write_cover(mp3s, cover=data, cover_mime=mime)
                out("[cover] preserved embedded cover after wipe")
            except Exception:
                pass

    mp3s = _apply_book_steps(
        steps=steps,
        mp3s=mp3s,
        outdir=outdir,
        author=author,
        title=title,
        out_title=out_title,
        i=i,
        n=n,
        b=b,
        cfg=cfg,
        cover_mode=cover_mode,
    )

    # [issue_86] publish-at-end: copy finalized book dir to final_root (archive) only after all PROCESS steps
    if final_root != dest_root:
        final_outdir = _output_dir(final_root, author, out_title)
        if state.OPTS and state.OPTS.dry_run:
            out(f"[dry-run] would publish: {outdir} -> {final_outdir}")
        else:
            ensure_dir(final_outdir.parent)
            if final_outdir.exists() and any(final_outdir.iterdir()):
                shutil.rmtree(final_outdir, ignore_errors=True)
            shutil.copytree(outdir, final_outdir, dirs_exist_ok=True)
            shutil.rmtree(outdir, ignore_errors=True)


def _resolve_source_arg(drop_root: Path, src_path: Path) -> Path:
    p = src_path
    if not p.is_absolute():
        p = drop_root / p
    p = p.expanduser().resolve()
    dr = drop_root.expanduser().resolve()

    if p == dr:
        return p

    if not p.exists():
        die(f"Source path not found: {p}")

    # must be under DROP_ROOT
    if not p.is_relative_to(dr):
        die(f"Source path must be under DROP_ROOT: {dr}")

    name = p.name
    if name.startswith(".") or name.startswith("_") or name in {"_am_stage", "import.log.jsonl", ".DS_Store"}:
        die(f"Invalid source path: {p}")

    # allow only dirs + supported archives
    if p.is_file() and p.suffix.lower() not in ARCHIVE_EXTS:
        die(f"Unsupported source: {p}")
    if not (p.is_dir() or (p.is_file() and p.suffix.lower() in ARCHIVE_EXTS)):
        die(f"Unsupported source: {p}")

    return p


def _resolved_pipeline_steps(cfg: dict) -> list[str]:
    # single source of truth for pipeline order
    return resolve_pipeline_steps(cfg)


def _is_interactive() -> bool:
    # Interactive = prompts are allowed (not --yes)
    return not (state.OPTS and state.OPTS.yes)


def _stage_cover_from_raw(cfg: dict, raw: str, group_root: Path) -> Path | None:
    """Resolve a cover input (URL/path) and stage it as cover.<ext> inside the book folder.
    Returns the staged cover path, or None if invalid/empty.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    img = cover_from_input(cfg, raw)
    if img is None:
        return None
    ext = img.suffix.lower() or ".jpg"
    dst = group_root / f"cover{ext}"
    if state.OPTS and state.OPTS.dry_run:
        out(f"[dry-run] would stage cover: {img} -> {dst}")
        return dst
    ensure_dir(dst.parent)
    shutil.copy2(img, dst)
    return dst

def run_import(cfg: dict, src_path: Optional[Path] = None) -> None:
    # validate preflight_steps early (fail fast, before FS touch)
    _resolved_preflight_steps(cfg)
    # validate pipeline_steps early (fail fast, before FS touch)
    # validate preflight_disable early (fail fast, before FS touch)
    _resolved_preflight_disable(cfg)

    steps = _resolved_pipeline_steps(cfg)
    if getattr(state, 'DEBUG', False):
        out(f"[debug] pipeline order: {' -> '.join(steps)}")

    # FEATURE #65: inbox cleanup control (delete processed source under DROP_ROOT)
    clean_inbox_mode = str(getattr(getattr(state, 'OPTS', None), 'clean_inbox_mode', cfg.get('clean_inbox', 'no')))
    if clean_inbox_mode not in {'ask', 'yes', 'no'}:
        die(f"Invalid configuration: clean_inbox must be one of ask|yes|no, got: {clean_inbox_mode!r}")
    if (state.OPTS and state.OPTS.yes) and clean_inbox_mode == 'ask':
        die("Non-interactive run requires an explicit inbox cleanup decision: set --clean-inbox yes|no (or config clean_inbox: yes|no)")

    drop_root = get_drop_root(cfg)
    stage_root = get_stage_root(cfg)
    archive_root = get_archive_root(cfg)
    output_root = get_output_root(cfg)

    ensure_dir(drop_root)
    ensure_dir(stage_root)
    ensure_dir(archive_root)
    ensure_dir(output_root)
    stage_runs_for_json: list[Path] = []
    picked_sources: list[Path]
    forced = False


    # Issue #74: per-source processing log
    def _pl_resolve_target(cfg: dict, stage_run: Path, src: Path) -> Path | None:
        spec = cfg.get('processing_log', {})
        if not isinstance(spec, dict):
            spec = {}
        if not bool(spec.get('enabled', False)):
            return None
        raw = spec.get('path', None)
        # Default: stage_run/processing.log
        if raw is None or str(raw).strip() == '':
            return (stage_run / 'processing.log')

        p = Path(str(raw)).expanduser()
        # If directory (or endswith slash), create per-source file inside
        if str(raw).endswith('/') or p.exists() and p.is_dir():
            fname = f"{slug(src.name)}.log"
            return (p / fname)

        # Treat as file path; enforce .log extension
        if p.suffix.lower() != '.log':
            p = p.with_suffix('.log')
        return p

    class _PLTee(io.TextIOBase):
        def __init__(self, a, b):
            self._a = a
            self._b = b
        def write(self, s):
            if s is None:
                return 0
            na = self._a.write(s)
            self._b.write(s)
            return na
        def flush(self):
            try:
                self._a.flush()
            except Exception:
                pass
            try:
                self._b.flush()
            except Exception:
                pass
        def isatty(self):
            return False
    picked_all = False


    def _process_one_source(src: Path, si: int, total: int, *, phase: str, do_process: bool, run_clean_inbox: bool) -> None:
        global prompt, prompt_yes_no
        # Issue #74: streaming per-source log (during run)
        stage_run = stage_root / slug(src.name)
        _pl_target = None
        _pl_fh = None
        _pl_stdout0 = sys.stdout
        _pl_stderr0 = sys.stderr
        _pl_prompt0 = prompt
        _pl_prompt_yes_no0 = prompt_yes_no
        _pl_util = None
        _pl_util_prompt0 = None
        _pl_util_prompt_yes_no0 = None
        try:
            _pl_target = _pl_resolve_target(cfg, stage_run, src)
            if _pl_target is not None and not (state.OPTS and state.OPTS.dry_run):
                # Ensure stage_run exists so we can log immediately.
                ensure_dir(stage_run)
                ensure_dir(_pl_target.parent)
                # Line-buffered file => every message is written right away.
                _pl_fh = _pl_target.open('w', encoding='utf-8', buffering=1)
        except Exception:
            _pl_target = None
            _pl_fh = None

        if _pl_fh is not None:
            _pl_tee = _PLTee(sys.stdout, _pl_fh)
            _pl_tee_err = _PLTee(sys.stderr, _pl_fh)
            sys.stdout = _pl_tee
            sys.stderr = _pl_tee_err

            # Wrap prompts to explicitly log questions + user answers.
            try:
                import audiomason.util as _pl_util
                _pl_util_prompt0 = getattr(_pl_util, 'prompt', None)
                _pl_util_prompt_yes_no0 = getattr(_pl_util, 'prompt_yes_no', None)
            except Exception:
                _pl_util = None

            def _pl_prompt(q: str, default: str) -> str:
                try:
                    _pl_fh.write(f"[prompt] {q} [default={default}]\n")
                except Exception:
                    pass
                ans = _pl_prompt0(q, default)
                try:
                    _pl_fh.write(f"[answer] {ans}\n")
                except Exception:
                    pass
                return ans

            def _pl_prompt_yes_no(q: str, *, default_no: bool = True) -> bool:
                try:
                    _pl_fh.write(f"[prompt_yes_no] {q} [default={'no' if default_no else 'yes'}]\n")
                except Exception:
                    pass
                ansb = _pl_prompt_yes_no0(q, default_no=default_no)
                try:
                    _pl_fh.write(f"[answer] {'yes' if ansb else 'no'}\n")
                except Exception:
                    pass
                return ansb

            # IMPORTANT: override module globals so all callers use wrappers.
            prompt = _pl_prompt
            prompt_yes_no = _pl_prompt_yes_no
            try:
                if _pl_util is not None and _pl_util_prompt0 is not None:
                    _pl_util.prompt = _pl_prompt
                if _pl_util is not None and _pl_util_prompt_yes_no0 is not None:
                    _pl_util.prompt_yes_no = _pl_prompt_yes_no
            except Exception:
                pass

        try:
                out(f"[source] {si}/{len(picked_sources)}: {src.name}")

                global _SOURCE_PREFIX
                _SOURCE_PREFIX = src.name

                import unicodedata

                def _norm(s: str) -> str:
                    return unicodedata.normalize("NFKC", s).strip().casefold()

                ignore_raw = load_ignore(drop_root)
                ignore_norm = {_norm(k) for k in ignore_raw}
                ignore_norm |= {_norm(slug(k)) for k in ignore_raw}

                candidates = {
                    _norm(src.name),
                    _norm(src.stem),
                    _norm(slug(src.name)),
                    _norm(slug(src.stem)),
                }

                if (not forced) and (candidates & ignore_norm):
                    out("[source] skipped (ignored)")
                    return

                stage_run = stage_root / slug(src.name)
                stage_runs_for_json.append(stage_run)
                stage_src = stage_run / "src"

                fp = source_fingerprint(src)
                update_manifest(stage_run, {"source": {"fingerprint": fp}})
                mf = load_manifest(stage_run)
                dec = mf.get("decisions", {})
                bm = mf.get("book_meta", {})

                reuse_possible = bool(stage_src.exists() and mf.get("source", {}).get("fingerprint") == fp)
                reuse_stage = False
                use_manifest_answers = False
                if phase == "process":
                    if not reuse_possible:
                        die("Internal error: process phase requires staged source from preflight phase")
                    reuse_stage = True
                    use_manifest_answers = True
                else:
                    if reuse_possible:
                        reuse_stage = _pf_prompt_yes_no(cfg, 'reuse_stage', "[stage] Reuse existing staged source?", default_no=False)

                    if reuse_stage:
                        out("[stage] reuse")
                        use_manifest_answers = _pf_prompt_yes_no(cfg, "use_manifest_answers", "[manifest] Use saved answers (skip prompts)?", default_no=False)
                    else:
                        if reuse_possible:
                            out("[stage] delete")
                            shutil.rmtree(stage_run, ignore_errors=True)
                            # reset locals; we'll recreate stage + manifest below
                            mf = {}
                            dec = {}
                            bm = {}

                    ensure_dir(stage_run)
                    update_manifest(stage_run, {
                        "source": {
                            "name": src.name,
                            "stem": src.stem,
                            "is_dir": bool(src.is_dir()),
                            "is_file": bool(src.is_file()),
                            "path": str(src),
                            "fingerprint": fp,
                        },
                    })
                    out(f"[stage] copying source into stage: {src} -> {stage_src}")
                    _stage_source(src, stage_src)

                # [issue_86] Conversion is PROCESS-only (m4a/opus -> mp3). No heavy work in PREPARE.

                books = _detect_books(stage_src)

                # book selection (skip when allowed, otherwise prompt with defaults)
                picked_books: list[BookGroup] = []
                picked = mf.get("books", {}).get("picked") if isinstance(mf, dict) else None
                if reuse_stage and use_manifest_answers and isinstance(picked, list) and picked:
                    by_label = {b.label: b for b in books}
                    picked_books = [by_label[label] for label in picked if label in by_label]

                default_ans = "1"
                if (not picked_books) and isinstance(picked, list) and picked:
                    if len(picked) == len(books):
                        default_ans = "a"
                    else:
                        try:
                            first = picked[0]
                            idx = [b.label for b in books].index(first) + 1
                            default_ans = str(idx)
                        except Exception:
                            default_ans = "1"

                if not picked_books:
                    picked_books = _choose_books(cfg, books, default_ans=default_ans)

                update_manifest(stage_run, {
                    "books": {
                        "detected": [b.label for b in books],
                        "picked": [b.label for b in picked_books],
                    },
                })

                # ISSUE #15: resume ask-to-skip processed books (never auto-skip)
                processed = mf.get("books", {}).get("processed") if isinstance(mf, dict) else None
                if reuse_stage and use_manifest_answers and isinstance(processed, list) and processed:
                    done = {str(x) for x in processed}
                    before = [b.label for b in picked_books]
                    already = [x for x in before if x in done]
                    if already:
                        out(f"[books] resume: already processed: {', '.join(already)}")
                        if _pf_prompt_yes_no(cfg, 'skip_processed_books', "Skip already processed books?", default_no=True):
                            picked_books = [b for b in picked_books if b.label not in done]
                            if not picked_books:
                                out("[books] resume: nothing left to process")
                                return

                # publish/wipe/clean_stage via dispatcher (Issue #93)
                
                publish: bool | None = None
                wipe: bool | None = None
                clean_stage: bool | None = None

                def _step_publish_wipe() -> None:
                    nonlocal publish, wipe
                    default_publish = bool(dec.get("publish")) if isinstance(dec, dict) and "publish" in dec else False
                    default_wipe = bool(dec.get("wipe_id3")) if isinstance(dec, dict) and "wipe_id3" in dec else False
                    if reuse_stage and use_manifest_answers and isinstance(dec, dict) and ("publish" in dec) and ("wipe_id3" in dec):
                        publish = bool(dec.get("publish"))
                        wipe = bool(dec.get("wipe_id3"))
                        return
                    if state.OPTS.publish is None:
                        publish = _pf_prompt_yes_no(cfg, "publish", "Publish after import?", default_no=(not default_publish))
                    else:
                        publish = bool(state.OPTS.publish)
                    if state.OPTS.wipe_id3 is None:
                        wipe = _pf_prompt_yes_no(cfg, "wipe_id3", "Full wipe ID3 tags before tagging?", default_no=(not default_wipe))
                    else:
                        wipe = bool(state.OPTS.wipe_id3)
                    update_manifest(stage_run, {"decisions": {"publish": bool(publish), "wipe_id3": bool(wipe)}})

                def _step_clean_stage() -> None:
                    nonlocal clean_stage
                    default_clean = bool(dec.get("clean_stage")) if isinstance(dec, dict) and ("clean_stage" in dec) else False
                    if reuse_stage and use_manifest_answers and isinstance(dec, dict) and ("clean_stage" in dec):
                        clean_stage = bool(dec.get("clean_stage"))
                        return
                    clean_stage = _pf_prompt_yes_no(cfg, "clean_stage", "Clean stage after successful import?", default_no=(not default_clean))
                    update_manifest(stage_run, {"decisions": {"clean_stage": bool(clean_stage)}})

                # Orchestrator is used for deterministic pending decisions.
                orchestrator = PreflightOrchestrator(cfg)
                ctx = PreflightContext(cfg=cfg)

                # In this flow, we already have source + books context here.
                ctx.context_level = "books_selected"

                plan = orchestrator.plan(ctx)

                def _exec_step(step_key: str) -> None:
                    if step_key in {"publish", "wipe_id3"}:
                        if publish is None or wipe is None:
                            _step_publish_wipe()
                    elif step_key == "clean_stage":
                        if clean_stage is None:
                            _step_clean_stage()
                    else:
                        # Other keys are handled elsewhere in existing flow.
                        return

                orchestrator.materialize_pending(ctx, plan, executor=_exec_step)

                if publish is None or wipe is None:
                    die("Internal error: missing required preflight decisions (publish/wipe_id3)")
                if clean_stage is None:
                    # Keep original behavior: clean_stage is required decision
                    _step_clean_stage()

# Issue #66: resolve source author (required for OpenLibrary validate_book)
                default_author = str(dec.get('author') or '').strip() if isinstance(dec, dict) else ''
                if reuse_stage and use_manifest_answers and default_author:
                    author = default_author
                else:
                    dflt_author = default_author or str(getattr(src, 'name', '') or '').strip() or src.name
                    author = _pf_prompt(cfg, 'source_author', '[source] Author', dflt_author).strip()
                    na = normalize_name(author)
                    if na != author:
                        out(f"[name] author suggestion: '{author}' -> '{na}'")
                        if _pf_prompt_yes_no(cfg, 'normalize_author', 'Apply suggested author?', default_no=True):
                            author = na
                    if _ol_enabled(cfg):
                        if getattr(state, 'DEBUG', False):
                            out(f"[ol] validate author: author='{author}'")
                        ar = validate_author(author)
                        if getattr(state, 'DEBUG', False):
                            out(f"[ol] author result: ok={getattr(ar,'ok',None)} status={getattr(ar,'status',None)!r} hits={getattr(ar,'hits',None)} top={getattr(ar,'top',None)!r}")
                        author = _ol_offer_top('author', author, ar, cfg=cfg, key='normalize_author')
                if not author:
                    die('Author is required')
                update_manifest(stage_run, {'decisions': {'author': author}})

                out("[phase] PREPARE")

                # Issue #66: resolve destination roots (work vs final)
                # publish=True => process into output_root, then (optionally) publish to archive_root at end
                # publish=False => process directly into chosen final root
                _publish = bool(publish)
                _work_root_default = output_root if _publish else None

                # preflight per-book metadata (must happen before touching output)
                # ISSUE #12: unify decisions upfront (title + cover choice). Processing must not prompt.
                meta: list[tuple[BookGroup, str, str, Path, str, bool]] = []
                for bi, b in enumerate(picked_books, 1):
                    # title
                    bm_entry2 = (bm.get(b.label, {}) if isinstance(bm, dict) else {})
                    default_title = str((bm_entry2.get("out_title") or bm_entry2.get("title") or "")).strip()

                    if reuse_stage and use_manifest_answers and default_title:
                        title = default_title
                    else:
                        # NOTE: during --dry-run, keep deterministic and do not prompt for title.
                        if state.OPTS and state.OPTS.dry_run:
                            title = default_title or b.label
                        else:
                            title = _preflight_book(cfg, bi, len(picked_books), b, default_title=default_title)

                        # OpenLibrary suggestion (book title)
                        if _ol_enabled(cfg):
                            if getattr(state, "DEBUG", False):
                                out(f"[ol] validate book: author='{author}' title='{title}'")
                            br = validate_book(author, title)
                            if (not getattr(br, 'ok', False)) and (not getattr(br, 'top', None)):
                                out(f"[ol] book not found: author='{author}' title='{title}'")
                            if getattr(state, "DEBUG", False):
                                out(f"[ol] book result: ok={getattr(br,'ok',None)} status={getattr(br,'status',None)!r} hits={getattr(br,'hits',None)} top={getattr(br,'top',None)!r}")
                            title = _ol_offer_top('book title', title, br, cfg=cfg, key='normalize_book_title')

                    # cover decision (Issue #43: choose/add cover during preflight; processing must not prompt)
                    default_cover_mode = (str(bm.get(b.label, {}).get("cover_mode") or "").strip() if (reuse_stage and use_manifest_answers and isinstance(bm, dict)) else "")
                    default_cover_src = (str(bm.get(b.label, {}).get("cover_src") or "").strip() if (reuse_stage and use_manifest_answers and isinstance(bm, dict)) else "")
                    mp3s = _collect_audio_files(b.group_root)
                    mp3_first = mp3s[0] if mp3s else None
                    file_cover = find_file_cover(b.stage_root, b.group_root)
                    embedded = extract_embedded_cover_from_mp3(mp3_first) if mp3_first else None

                    cover_mode = ""
                    cover_src = ""
                    if reuse_stage and use_manifest_answers and default_cover_mode:
                        cover_mode = default_cover_mode
                        cover_src = default_cover_src
                    else:
                        out(f"[cover-meta] {bi}/{len(picked_books)}: {author} / {title}")
                        # Non-interactive: deterministic, no prompts
                        if not _is_interactive():
                            if file_cover:
                                cover_mode = "file"
                                cover_src = str(file_cover.name)
                            elif embedded:
                                cover_mode = "embedded"
                                cover_src = "embedded"
                            else:
                                cover_mode = "skip"
                                cover_src = "skip"
                        else:
                            # Interactive preflight: allow keep/override/skip, or provide URL/path
                            if file_cover or embedded:
                                # If both exist, offer explicit choice first
                                if file_cover and embedded:
                                    out("Cover detected:")
                                    out("  1) embedded cover from audio")
                                    out(f"  2) {file_cover.name} (preferred)")
                                    out("  s) skip")
                                    out("  u) URL/path override")
                                    d = "2"
                                    if default_cover_mode == "embedded":
                                        d = "1"
                                    elif default_cover_mode == "skip":
                                        d = "s"
                                    ans = _pf_prompt(cfg, 'cover', "Choose cover [1/2/s/u]", d).strip().lower()
                                    if ans == "1":
                                        cover_mode = "embedded"
                                        cover_src = "embedded"
                                    elif ans == "s":
                                        cover_mode = "skip"
                                        cover_src = "skip"
                                    elif ans == "u":
                                        raw = _pf_prompt(cfg, "cover", "Cover URL or file path (Enter=skip)", "").strip()
                                        if not raw:
                                            cover_mode = "skip"
                                            cover_src = "skip"
                                        else:
                                            staged = _stage_cover_from_raw(cfg, raw, b.group_root)
                                            if staged is None:
                                                cover_mode = "skip"
                                                cover_src = "skip"
                                            else:
                                                cover_mode = "file"
                                                cover_src = raw
                                    else:
                                        cover_mode = "file"
                                        cover_src = str(file_cover.name)
                                else:
                                    # Only one detected => keep by default, allow override
                                    if file_cover:
                                        out(f"Cover detected: {file_cover.name}")
                                        keep = _pf_prompt_yes_no(cfg, 'cover', "Use detected cover?", default_no=False)
                                        if keep:
                                            cover_mode = "file"
                                            cover_src = str(file_cover.name)
                                        else:
                                            raw = _pf_prompt(cfg, "cover", "Cover URL or file path (Enter=skip)", "").strip()
                                            if not raw:
                                                cover_mode = "skip"
                                                cover_src = "skip"
                                            else:
                                                staged = _stage_cover_from_raw(cfg, raw, b.group_root)
                                                if staged is None:
                                                    cover_mode = "skip"
                                                    cover_src = "skip"
                                                else:
                                                    cover_mode = "file"
                                                    cover_src = raw
                                    else:
                                        out("Cover detected: embedded")
                                        keep = _pf_prompt_yes_no(cfg, 'cover', "Use embedded cover?", default_no=False)
                                        if keep:
                                            cover_mode = "embedded"
                                            cover_src = "embedded"
                                        else:
                                            raw = _pf_prompt(cfg, "cover", "Cover URL or file path (Enter=skip)", "").strip()
                                            if not raw:
                                                cover_mode = "skip"
                                                cover_src = "skip"
                                            else:
                                                staged = _stage_cover_from_raw(cfg, raw, b.group_root)
                                                if staged is None:
                                                    cover_mode = "skip"
                                                    cover_src = "skip"
                                                else:
                                                    cover_mode = "file"
                                                    cover_src = raw
                            else:
                                # No detected cover => ask once
                                # NOTE: during --dry-run, keep deterministic and do not prompt for cover.
                                if state.OPTS and state.OPTS.dry_run:
                                    cover_mode = "skip"
                                    cover_src = "skip"
                                else:
                                    raw = _pf_prompt(cfg, 'cover', "No cover found. URL or file path (Enter=skip)", "").strip()
                                    if not raw:
                                        cover_mode = "skip"
                                        cover_src = "skip"
                                    else:
                                        staged = _stage_cover_from_raw(cfg, raw, b.group_root)
                                        if staged is None:
                                            cover_mode = "skip"
                                            cover_src = "skip"
                                        else:
                                            cover_mode = "file"
                                            cover_src = raw

                    # ISSUE #1: destination conflict handling (fixed mapping for Issue #75)
                    bm_entry = (bm.get(b.label, {}) if isinstance(bm, dict) else {})
                    if reuse_stage and use_manifest_answers:
                        m_overwrite = bool(bm_entry.get("overwrite") is True)
                        m_dest_kind = str(bm_entry.get("dest_kind") or "")
                        m_out_title = str(bm_entry.get("out_title") or "").strip()
                    else:
                        m_overwrite = False
                        m_dest_kind = ""
                        m_out_title = ""

                    # Determine FINAL root (where the book should end up).
                    final_root2 = archive_root
                    if m_dest_kind == "output":
                        final_root2 = output_root
                    elif m_dest_kind == "archive":
                        final_root2 = archive_root

                    # Determine WORK root (where PROCESS writes). If publishing, we always work in output_root.
                    dest_root2 = (_work_root_default if _publish else final_root2)

                    out_title = m_out_title or title
                    overwrite = m_overwrite

                    outdir = _output_dir(dest_root2, author, out_title)
                    if _is_dir_nonempty(outdir) and not (reuse_stage and use_manifest_answers):
                        # 1) offer overwrite (interactive only)
                        if not (state.OPTS and state.OPTS.yes):
                            out(f"[dest] exists: {outdir}")
                            overwrite = _pf_prompt_yes_no(cfg, 'overwrite_destination', "Destination exists. Overwrite?", default_no=True)
                        else:
                            overwrite = False

                        if not overwrite:
                            # 2) fallback to abooks_ready if we are not already there
                            if dest_root2 != output_root:
                                dest_root2 = output_root
                                outdir = _output_dir(dest_root2, author, out_title)

                            # 3) if still conflict => fail (structure is fixed; no auto-new folder)
                            if _is_dir_nonempty(outdir):
                                die(f"Conflict: output already exists and is not empty: {outdir}")

                    # persist
                    dest_kind = "archive" if dest_root2 == archive_root else "output"
                    meta.append((b, title, cover_mode, dest_root2, out_title, overwrite, final_root2))  # [issue_86] include final_root
                    update_manifest(stage_run, {"book_meta": {b.label: {"title": title, "cover_mode": cover_mode, "cover_src": cover_src, "dest_kind": dest_kind, "out_title": out_title, "overwrite": bool(overwrite)}}})

                if not do_process:
                    return

                out("[phase] PROCESS")
                # ISSUE #15: manifest progress for resume
                processed_labels = mf.get("books", {}).get("processed") if isinstance(mf, dict) else None
                if not isinstance(processed_labels, list):
                    processed_labels = []

                # processing phase (no prompts)
                for bi, (b, title, cover_mode, dest_root2, out_title, overwrite, final_root2) in enumerate(meta, 1):
                    _process_book(bi, len(meta), b, stage_run, dest_root2, author, title, out_title, wipe, cover_mode, overwrite, cfg, final_root2, steps)
                    processed_labels.append(b.label)
                    update_manifest(stage_run, {"books": {"processed": processed_labels}})

                out("[phase] FINALIZE")

                # FEATURE #26: clean stage at end (successful run only)
                # FEATURE #51: mark processed source as ignored
                if not (state.OPTS and state.OPTS.dry_run):
                    add_ignore(drop_root, src.name)
                    out(f"[ignore] added: {src.name}")
                # FEATURE #65: inbox cleanup control (run-level decision)
                do_clean_inbox = bool(run_clean_inbox)

                if do_clean_inbox:
                    if state.OPTS and state.OPTS.dry_run:
                        out(f"[inbox] would clean: {src}")
                    else:
                        if src.is_dir():
                            shutil.rmtree(src, ignore_errors=True)
                        else:
                            src.unlink(missing_ok=True)
                        out(f"[inbox] cleaned: {src}")

                # perform stage cleanup if requested and not dry-run
                dec2 = load_manifest(stage_run).get('decisions', {})
                do_clean = bool(dec2.get('clean_stage'))
                if do_clean:
                    if state.OPTS and state.OPTS.dry_run:
                        out(f"[stage] would clean: {stage_run}")
                    else:
                        shutil.rmtree(stage_run, ignore_errors=True)
                        out(f"[stage] cleaned: {stage_run}")


        finally:
            # Issue #74: finalize streaming per-source log
            sys.stdout = _pl_stdout0
            sys.stderr = _pl_stderr0
            # restore prompt functions
            try:
                prompt = _pl_prompt0
                prompt_yes_no = _pl_prompt_yes_no0
            except Exception:
                pass
            try:
                if _pl_util is not None and _pl_util_prompt0 is not None:
                    _pl_util.prompt = _pl_util_prompt0
                if _pl_util is not None and _pl_util_prompt_yes_no0 is not None:
                    _pl_util.prompt_yes_no = _pl_util_prompt_yes_no0
            except Exception:
                pass
            try:
                if _pl_fh is not None:
                    _pl_fh.flush()
                    _pl_fh.close()
            except Exception:
                pass

    def _run_one_source(src: Path, si: int, total: int, *, phase: str, do_process: bool, run_clean_inbox: bool) -> None:
        # Explicit per-source boundary: delegate the full lifecycle to _process_one_source().
        return _process_one_source(src, si, total, phase=phase, do_process=do_process, run_clean_inbox=run_clean_inbox)




    if src_path is not None:
        sp = _resolve_source_arg(drop_root, src_path)
        if sp.expanduser().resolve() == drop_root.expanduser().resolve():
            sources = _list_sources(drop_root)
            picked_sources = _choose_source(cfg, sources)
            forced = False
            picked_all = (picked_sources is sources)
        else:
            picked_sources = [sp]
            forced = True
    else:
        sources = _list_sources(drop_root)
        picked_sources = _choose_source(cfg, sources)
        forced = False
        picked_all = (picked_sources is sources)

    # ISSUE #88: resolve inbox cleanup decision ONCE per run (never prompt mid-PROCESS)
    run_clean_inbox: bool
    if clean_inbox_mode == 'yes':
        run_clean_inbox = True
    elif clean_inbox_mode == 'no':
        run_clean_inbox = False
    else:
        # clean_inbox_mode == 'ask' (validated above)
        run_clean_inbox = _pf_prompt_yes_no(cfg, "clean_inbox", "Clean inbox after successful import?", default_no=True)

    phases = ["combined"]
    if picked_all and len(picked_sources) > 1:
        phases = ["preflight", "process"]
    for phase in phases:
        do_process = phase != "preflight"
        for si, src in enumerate(picked_sources, 1):
            _run_one_source(src, si, len(picked_sources), phase=phase, do_process=do_process, run_clean_inbox=run_clean_inbox)
# ISSUE #18: machine-readable report (printed at end; human output unchanged)
    if state.OPTS and getattr(state.OPTS, "json", False):
        report = _build_json_report(stage_runs_for_json)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)

