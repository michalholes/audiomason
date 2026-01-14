#!/usr/bin/env python3
import json, subprocess
from datetime import datetime
from pathlib import Path

ISSUE_DIR = Path("docs/issues")
AUDIT_DIR = Path("docs/audit")
SUMMARY_FILE = AUDIT_DIR / "issues_summary.json"

def _count_issues(file):
    return sum(1 for line in open(file) if line.startswith("## #"))

def main():
    open_md = ISSUE_DIR / "open_issues.md"
    closed_md = ISSUE_DIR / "closed_issues.md"
    open_count, closed_count = _count_issues(open_md), _count_issues(closed_md)
    total = open_count + closed_count
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "open": open_count,
        "closed": closed_count,
        "total": total,
        "close_rate": f"{(closed_count/total)*100:.1f}%" if total else "N/A"
    }
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_FILE, "w") as f: json.dump(summary, f, indent=2)
    print(f"✅ Stats written to {SUMMARY_FILE}")
if __name__ == "__main__": main()
