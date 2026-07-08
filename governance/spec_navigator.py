from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, cast

JsonDict: TypeAlias = dict[str, object]
JsonList: TypeAlias = list[JsonDict]


def as_json_dict(value: object) -> JsonDict:
    if not isinstance(value, dict):
        raise ValueError("expected_json_object")
    return cast(JsonDict, value)


SEPARATOR = "-" * 72


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in cast(list[object], value)]


def _load_jsonl(path: Path) -> JsonList:
    objects: JsonList = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                objects.append(as_json_dict(cast(object, json.loads(line))))
    return objects


def _parse_applies_to(raw: str) -> set[str]:
    return {t.strip().upper() for t in raw.split("|") if t.strip()}


def _index(
    objects: JsonList,
) -> tuple[
    JsonDict | None,
    list[JsonDict],
    dict[str, JsonDict],
]:
    meta: JsonDict | None = None
    caps: list[JsonDict] = []
    rules: dict[str, JsonDict] = {}
    for obj in objects:
        t = obj.get("type")
        if t == "meta":
            meta = obj
        elif t == "capability":
            caps.append(obj)
        elif t == "rule":
            rules[str(obj.get("id", ""))] = obj
    return meta, caps, rules


def _all_tags(caps: list[JsonDict]) -> dict[str, list[str]]:
    """Return {tag: [cap_id, ...]} sorted."""
    tag_map: dict[str, list[str]] = {}
    for cap in caps:
        for tag in _parse_applies_to(str(cap.get("applies_to", ""))):
            tag_map.setdefault(tag, []).append(str(cap.get("id", "")))
    return dict(sorted(tag_map.items()))


def _has_tag_model(caps: list[JsonDict]) -> bool:
    return any(str(cap.get("applies_to", "")).strip() for cap in caps)


def _spec_header(meta: JsonDict | None) -> list[str]:
    if not meta:
        return []
    return [f"spec: {meta.get('id', '')}  version: {meta.get('version', '')}", ""]


def _emit_cap_rules(
    cap: JsonDict,
    rules: dict[str, JsonDict],
    out: list[str],
    seen: set[str],
) -> int:
    rule_ids = _str_list(cap.get("triggers_rules", []))
    added = 0
    for rid in rule_ids:
        rule = rules.get(rid)
        if rule is None:
            continue
        stmt = str(rule.get("statement", "")).strip()
        hp = str(rule.get("heading_path", ""))
        section = hp.split(" > ")[-1] if " > " in hp else hp
        normativity = str(rule.get("normativity", ""))
        prefix = f"[{normativity}] " if normativity else ""
        out.append(f"  {rid}")
        if section:
            out.append(f"    section: {section}")
        out.append(f"    {prefix}{stmt}")
        out.append("")
        if rid not in seen:
            seen.add(rid)
            added += 1
    return added


def cmd_list_tags(
    meta: JsonDict | None,
    caps: list[JsonDict],
    rules: dict[str, JsonDict],
) -> str:
    out: list[str] = _spec_header(meta)
    if _has_tag_model(caps):
        out.append(f"{'TAG':<20}  {'CAPS':>4}  {'RULES':>5}  CAPABILITY IDS")
        out.append(SEPARATOR)
        tag_map = _all_tags(caps)
        cap_by_id = {str(c.get("id", "")): c for c in caps}
        for tag, cap_ids in tag_map.items():
            rule_count = sum(
                len(_str_list(cap_by_id[cid].get("triggers_rules", [])))
                for cid in cap_ids
                if cid in cap_by_id
            )
            out.append(f"{tag:<20}  {len(cap_ids):>4}  {rule_count:>5}  {', '.join(cap_ids)}")
        out.append("")
        out.append(f"total capabilities: {len(caps)}  total rules: {len(rules)}")
        out.append("use: --tags TAG [TAG...]")
    else:
        # Section-contract model — list capability names for --section queries
        out.append(f"{'RULES':>5}  SECTION")
        out.append(SEPARATOR)
        for cap in caps:
            name = str(cap.get("name", cap.get("id", "")))
            rule_count = len(_str_list(cap.get("triggers_rules", [])))
            out.append(f"{rule_count:>5}  {name}")
        out.append("")
        out.append(f"total capabilities: {len(caps)}  total rules: {len(rules)}")
        out.append("use: --section KEYWORD")
    return "\n".join(out)


def cmd_query_tags(
    tags: list[str],
    caps: list[JsonDict],
    rules: dict[str, JsonDict],
) -> str:
    if not _has_tag_model(caps):
        return (
            "This spec uses section-contract capabilities, not domain tags.\n"
            "Use --section KEYWORD instead.\n"
        )
    query = {t.upper() for t in tags}
    matched = [c for c in caps if _parse_applies_to(str(c.get("applies_to", ""))) & query]
    if not matched:
        return f"No capabilities found for tags: {sorted(query)}\n"

    out: list[str] = [f"query tags: {sorted(query)}", ""]
    seen: set[str] = set()
    total = 0
    for cap in matched:
        cap_id = str(cap.get("id", ""))
        applies = str(cap.get("applies_to", ""))
        rule_ids = _str_list(cap.get("triggers_rules", []))
        out.append(f"[{cap_id}]  applies_to: {applies}  rules: {len(rule_ids)}")
        out.append(SEPARATOR)
        total += _emit_cap_rules(cap, rules, out, seen)
        out.append("")
    out.append(SEPARATOR)
    out.append(f"matched {len(matched)} capability/capabilities  unique rules: {total}")
    return "\n".join(out)


def cmd_query_section(
    keyword: str,
    caps: list[JsonDict],
    rules: dict[str, JsonDict],
) -> str:
    kw = keyword.lower()
    matched = [
        c
        for c in caps
        if kw in str(c.get("name", "")).lower() or kw in str(c.get("heading_path", "")).lower()
    ]
    if not matched:
        return f"No capabilities found matching section keyword: {keyword!r}\n"

    out: list[str] = [f"section query: {keyword!r}  matched: {len(matched)}", ""]
    seen: set[str] = set()
    total = 0
    for cap in matched:
        cap_id = str(cap.get("id", ""))
        name = str(cap.get("name", cap_id))
        rule_ids = _str_list(cap.get("triggers_rules", []))
        out.append(f"[{cap_id}]")
        out.append(f"  section: {name}  rules: {len(rule_ids)}")
        out.append(SEPARATOR)
        total += _emit_cap_rules(cap, rules, out, seen)
        out.append("")
    out.append(SEPARATOR)
    out.append(f"matched {len(matched)} section(s)  unique rules: {total}")
    return "\n".join(out)


@dataclass(frozen=True)
class NavigatorArgs:
    spec: str
    list_tags: bool
    tags: list[str] | None
    section: str | None


def parse_args(argv: list[str]) -> NavigatorArgs:
    parser = argparse.ArgumentParser(
        description=(
            "Query a specification.jsonl by capability tags or section keyword.\n"
            "Supports two spec models:\n"
            "  tag-model:     capabilities have applies_to domain tags  → use --tags\n"
            "  section-model: capabilities are section contracts         → use --section"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  spec_navigator.py governance/specification.jsonl --list-tags\n"
            "  spec_navigator.py governance/specification.jsonl --tags PLUGIN REGISTRY\n"
            "  spec_navigator.py governance/specification.jsonl --tags FILE_IO\n"
            "  spec_navigator.py governance/specification.jsonl --section 'timeout'\n"
            "  spec_navigator.py governance/specification.jsonl --section 'gate'\n"
        ),
    )
    parser.add_argument("spec", help="Path to specification.jsonl")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--list-tags",
        action="store_true",
        help="List available tags (tag-model) or sections (section-model) with rule counts",
    )
    group.add_argument(
        "--tags",
        nargs="+",
        metavar="TAG",
        help="Return rules from capabilities matching any tag (tag-model specs)",
    )
    group.add_argument(
        "--section",
        metavar="KEYWORD",
        help="Return rules from capabilities whose section name/path contains keyword",
    )
    ns = parser.parse_args(argv)
    values = cast(dict[str, object], vars(ns))
    tags_raw = values.get("tags")
    tags = None if tags_raw is None else _str_list(tags_raw)
    section_raw = values.get("section")
    section = None if section_raw is None else str(section_raw)
    return NavigatorArgs(
        spec=str(values["spec"]),
        list_tags=bool(values.get("list_tags", False)),
        tags=tags,
        section=section,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args((argv or sys.argv)[1:])
    path = Path(args.spec)
    if not path.is_file():
        sys.stderr.write(f"error: file not found: {path}\n")
        return 1
    objects = _load_jsonl(path)
    meta, caps, rules = _index(objects)
    if not caps:
        sys.stderr.write("error: no capability objects found in spec\n")
        return 1
    if args.list_tags:
        sys.stdout.write(cmd_list_tags(meta, caps, rules) + "\n")
    elif args.tags:
        sys.stdout.write(cmd_query_tags(args.tags, caps, rules) + "\n")
    else:
        assert args.section is not None
        sys.stdout.write(cmd_query_section(args.section, caps, rules) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
