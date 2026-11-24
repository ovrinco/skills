#!/usr/bin/env python3
"""Citation check: cited decision ids exist; a line marked stated rests on his turn or note, never a reading.
Read-only, no model. Lists offenders; corrects nothing. Exit 1 if any offender."""
import argparse, glob, json, os, re, sys

OD = re.compile(r"OD-\d{4}-\d\d-\d\d-\d\d")
VOX = re.compile(r"voxtype:[\w:@.-]+")
REG = re.compile(r"R-[A-Z]+-[A-Z]?\d+")
SESSION = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|session [0-9a-f]{8}")
READING = re.compile(r"orchestrator_reading|\breading\b|\bbrief\b|\brelay", re.I)
ROW = re.compile(r"^\|\s*\d+[a-z]?\s*\|")

def his_word(source):
    return source.startswith("voxtype:") or ("chat:" in source and bool(SESSION.search(source)))

def check(path, ledger, reg_ids):
    out = []
    for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        for i in OD.findall(line):
            if i not in ledger:
                out.append((f"{path}:{n}", "A", i, "unknown decision id"))
        if not ROW.match(line):
            continue
        cell = line.strip().strip("|").split("|")[-1].strip()
        if not re.search(r"\bstated\b", cell):
            continue
        ids = OD.findall(cell)
        if ids and READING.search(cell):
            out.append((f"{path}:{n}", "C", cell[:100], "stated on a reading"))
            continue
        good = [i for i in ids if his_word(ledger.get(i, ""))] + VOX.findall(cell) + \
               [r for r in REG.findall(cell) if r in reg_ids]
        if good:
            continue
        if any(i in ledger for i in ids) or READING.search(cell):
            out.append((f"{path}:{n}", "B", cell[:100], "stated on a reading"))
        else:
            out.append((f"{path}:{n}", "B", cell[:100], "stated without a source id"))
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--register")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    data = json.load(open(a.ledger))
    entries = data["entries"] if isinstance(data, dict) else data
    ledger = {e["id"]: e.get("source") or "" for e in entries}
    reg_ids = set()
    for f in (glob.glob(os.path.join(a.register, "*.md")) if a.register else []):
        reg_ids.update(REG.findall(open(f, encoding="utf-8", errors="replace").read()))
    files = a.files
    rows, counts = [], {}
    for f in files:
        found = check(f, ledger, reg_ids)
        rows += found
        counts[f] = len(found)
    if a.json:
        print(json.dumps({"offenders": [dict(zip(("where", "check", "cited", "reason"), r)) for r in rows],
                          "counts": counts, "total": len(rows), "files_checked": len(files)}, indent=1))
    else:
        for r in rows:
            print(" | ".join(r))
        print()
        for f, c in counts.items():
            print(f"{c:4d}  {f}")
        print(f"total offenders: {len(rows)} in {len(files)} files")
    return 1 if rows else 0

if __name__ == "__main__":
    sys.exit(main())
