#!/usr/bin/env python3
"""Checks an essence against its export. Standard library only; reads two files, writes nothing.

usage: check_essence.py EXPORT.md ESSENCE.md        exit 0 = all pass, 1 = a check failed, 2 = bad input

1. turn ids    every U<n> / A<n> cited in the essence exists in the export, and every item line cites one
2. size        essence lines <= max(12, a third of the export's lines), and never over 300
3. no copying  no run of eight or more consecutive words of an operator turn appears in the essence
4. no tone     the essence has no tone section
"""
import re
import sys

RUN = 8


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:['’][a-z]+)?", text.lower())


def read_export(path: str) -> tuple[set[str], dict[str, str], int]:
    """Turn ids, the text of each operator turn, and the number of lines."""
    ids, operator, current, fence, lines = set(), {}, None, None, 0
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            lines += 1
            line = raw.rstrip("\n")
            if fence:
                if line == fence:
                    fence = None
                elif current and current.startswith("U"):
                    operator[current] = operator.get(current, "") + line + "\n"
                continue
            opened = re.match(r"^(`{3,})text$", line)
            if opened:
                fence = opened.group(1)
                continue
            heading = re.match(r"^## ([UA]\d+) · ", line)
            if heading:
                current = heading.group(1)
                ids.add(current)
    return ids, operator, lines


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    ids, operator, export_lines = read_export(sys.argv[1])
    essence = open(sys.argv[2], encoding="utf-8").read()
    essence_lines = essence.rstrip("\n").split("\n")
    failed = False

    cited = set(re.findall(r"\b([UA]\d+)\b", essence))
    unknown = sorted(cited - ids)
    items = [l for l in essence_lines if re.match(r"^\s*(?:[-*]|\d+\.)\s+\S", l)]
    uncited = [l for l in items if not re.search(r"\b[UA]\d+\b", l)]
    ok = not unknown and not uncited and bool(cited)
    failed |= not ok
    print(f"1 turn ids    {'pass' if ok else 'FAIL'}: {len(cited)} ids cited, {len(unknown)} not in the export"
          f"{' ' + str(unknown) if unknown else ''}; {len(items)} items, {len(uncited)} without a turn id")
    for line in uncited:
        print(f"    no turn id: {line.strip()[:90]}")

    limit = min(300, max(12, export_lines // 3))
    ok = len(essence_lines) <= limit
    failed |= not ok
    print(f"2 size        {'pass' if ok else 'FAIL'}: essence {len(essence_lines)} lines, export {export_lines}, "
          f"limit {limit}")

    grams = {}
    for turn, text in operator.items():
        w = words(text)
        for i in range(len(w) - RUN + 1):
            grams.setdefault(tuple(w[i:i + RUN]), turn)
    w = words(essence)
    hits = [(grams[tuple(w[i:i + RUN])], " ".join(w[i:i + RUN])) for i in range(len(w) - RUN + 1)
            if tuple(w[i:i + RUN]) in grams]
    failed |= bool(hits)
    print(f"3 no copying  {'FAIL' if hits else 'pass'}: {len(operator)} operator turns, {len(grams)} runs of {RUN} "
          f"words compared, {len(hits)} found in the essence")
    for turn, run in hits[:5]:
        print(f"    copied from {turn}: {run}")

    tone = [l for l in essence_lines if re.match(r"^#+ .*\b(tone|tonal|mood|posture)\b", l, re.I)]
    failed |= bool(tone)
    print(f"4 no tone     {'FAIL' if tone else 'pass'}: {len(tone)} tone headings")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
