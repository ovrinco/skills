#!/usr/bin/env python3
"""White-label check for a deep-research prompts file.

Scans the fenced prompt blocks (``` ... ```) only, so the head and the mapping section may name things.
Prints file:line: name for every proprietary name found; exits 1 on any hit, 0 when clean.
Also fails any prompt block that does not demand one downloadable file and a one-sentence chat reply
The delivery contract is checked independently from the report content.
Names come from the voice-note name list (canonical names) plus the built-in list below.
"""
import json, re, sys, os
BUILTIN = []
PUBLIC = set()
NAMES_JSON = os.environ.get("RESEARCH_PRIVATE_NAMES", str(__import__("pathlib").Path(__file__).resolve().parent.parent / "private-names.json"))

def load_names():
    names = set(BUILTIN)
    try:
        for e in json.load(open(NAMES_JSON, encoding="utf-8")):
            c = e if isinstance(e, str) else e.get("canonical")
            if c and c not in PUBLIC: names.add(c)
    except Exception as ex:
        raise ValueError(f"private-name dictionary cannot be read: {ex}") from ex
    return sorted(names, key=len, reverse=True)

def main():
    if len(sys.argv) < 2:
        print("usage: check_prompt.py PROMPTS.md [more.md]", file=sys.stderr); return 2
    try:
        names = load_names()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    pats = [(n, re.compile(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_])", re.I)) for n in names]
    hits = 0
    one_file = [re.compile(r"one downloadable (markdown )?file", re.I), re.compile(r"one sentence", re.I)]
    for path in sys.argv[1:]:
        infence = False; block = []; start = 0
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            if line.startswith("```"):
                if infence:
                    text = "".join(block)
                    if not all(p.search(text) for p in one_file):
                        hits += 1; print(f"{path}:{start}: prompt lacks the one-file, one-sentence delivery line")
                else:
                    block = []; start = i
                infence = not infence; continue
            if not infence: continue
            block.append(line)
            for n, p in pats:
                if p.search(line):
                    hits += 1; print(f"{path}:{i}: {n}")
        if infence:
            hits += 1; print(f"{path}:{start}: unclosed prompt block")
    print(f"{hits} hit(s)" if hits else "clean: no proprietary name inside any prompt block")
    return 1 if hits else 0

if __name__ == "__main__":
    sys.exit(main())
