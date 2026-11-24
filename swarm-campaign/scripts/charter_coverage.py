#!/usr/bin/env python3
"""List, for every stated result line of the charters, the campaigns whose directives cite it (rule O2 form).

Read-only. Lists the stated lines no campaign builds and those built by more than one. Exit 1 if any stated
line has no campaign, else 0. Edits nothing.
"""
import argparse, glob, json, os, re, sys

OUTCOMES = os.path.abspath("charters")
REGISTRY = os.path.abspath("campaign-registry")
ROW = re.compile(r"^\|\s*\d+[a-z]?\s*\|")  # the row test of citation_check
OUTCOME_LINE = re.compile(r"^Outcome: (OC-\d\d), result lines? ([0-9a-zA-Z, and–-]+?)\s*[:(]", re.M)  # outcome_check O2
NUMBERS = re.compile(r"([0-9]+)\s*[-–]\s*([0-9]+)|([0-9]+[a-z]?|Z[0-9])")

def stated_lines(path):
    m = re.match(r"(OC-\d\d)", os.path.basename(path))
    oc = m.group(1) if m else None
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        if oc is None:
            h = re.match(r"#\s+(OC-\d\d)\b", line)
            oc = h.group(1) if h else None
        if not ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not re.search(r"\bstated\b", cells[-1]):
            continue
        words = " ".join(cells[1].split()[:8]) if len(cells) > 1 else ""
        out.append((oc, cells[0], words))
    return out

def cited(root):
    pairs = set()
    for d in sorted(glob.glob(os.path.join(root, "wave*", "*.md"))):
        m = OUTCOME_LINE.search(open(d, encoding="utf-8", errors="replace").read())
        if not m:
            continue
        for a, b, single in NUMBERS.findall(m.group(2)):
            if single:
                pairs.add((m.group(1), single))
            elif int(a) <= int(b):
                pairs.update((m.group(1), str(i)) for i in range(int(a), int(b) + 1))
    return pairs

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--charters", default=os.path.join(OUTCOMES, "OC-[0-9][0-9]_*.md"))
    ap.add_argument("--registry", default=REGISTRY)
    ap.add_argument("--root", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not glob.glob(a.charters):
        ap.error("no charter files match the explicit/default input")
    names, missing = {}, []
    for f in sorted(glob.glob(os.path.join(a.registry, "*.json"))):
        try:
            d = json.load(open(f))
        except (OSError, ValueError):
            continue
        r = d.get("root")
        if not r:
            continue
        r = os.path.realpath(r)
        names[r] = d.get("name") or os.path.basename(r)
        if not os.path.isdir(r):
            missing.append(names[r])
    roots = [os.path.realpath(r) for r in a.root] or sorted(r for r in names if os.path.isdir(r))
    built = {}
    for r in roots:
        for pair in cited(r):
            built.setdefault(pair, []).append(names.get(r, os.path.basename(r)))
    rows = []
    for c in sorted(glob.glob(a.charters)):
        for oc, n, words in stated_lines(c):
            camps = sorted(built.get((oc, n), []))
            rows.append({"outcome": oc, "line": n, "result": words, "campaigns": camps, "count": len(camps)})
    none = [r for r in rows if r["count"] == 0]
    many = [r for r in rows if r["count"] > 1]
    totals = {"charters": len(glob.glob(a.charters)), "stated_lines": len(rows), "roots": len(roots),
              "missing_roots": missing, "built_by_none": len(none), "built_by_more_than_one": len(many)}
    if a.json:
        print(json.dumps({"rows": rows, "none": none, "more_than_one": many, "totals": totals}, indent=1))
    else:
        fmt = lambda r: f"{r['outcome']} | line {r['line']} | {r['result']} | {', '.join(r['campaigns']) or '-'} | {r['count']}"
        for r in rows:
            print(fmt(r))
        print("\nBuilt by none:")
        for r in none:
            print("  " + fmt(r))
        print("\nBuilt by more than one campaign:")
        for r in many:
            print("  " + fmt(r))
        print(f"\nTotals: {totals['charters']} charters, {totals['stated_lines']} stated lines, {totals['roots']} roots read; "
              f"{totals['built_by_none']} built by none, {totals['built_by_more_than_one']} by more than one")
        print(f"Missing roots: {len(missing)}" + (f" ({', '.join(missing)})" if missing else ""))
    return 1 if none else 0

if __name__ == "__main__":
    sys.exit(main())
