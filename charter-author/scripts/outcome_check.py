#!/usr/bin/env python3
"""Check the portable outcome contract and result references. Read-only structural lint."""
import argparse
import json
from pathlib import Path
import re

FIELD = re.compile(r"^##\s+.+?\(F(10|[1-9])\)\s*$", re.M)
RESULT = re.compile(r"^\|\s*([0-9]+[a-z]?|Z[0-9]+)\s*\|(.+)$", re.M)
REFERENCE = re.compile(r"result lines?\s+([^:\n(]+)", re.I)

def references(text):
    result = set()
    for match in REFERENCE.finditer(text):
        for low, high in re.findall(r"(\d+)\s*-\s*(\d+)", match.group(1)):
            result.update(str(number) for number in range(int(low), int(high) + 1))
        result.update(re.findall(r"\b(?:\d+[a-z]?|Z\d+)\b", match.group(1)))
    return result

def check(root):
    path = root / "OUTCOME.md"
    text = path.read_text()
    findings = []
    sections = {}
    matches = list(FIELD.finditer(text))
    for index, match in enumerate(matches):
        field = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        if field in sections:
            findings.append(f"F{field} appears more than once")
        sections[field] = body
        if not body:
            findings.append(f"F{field} has no content")
    for field in range(1, 11):
        if field not in sections:
            findings.append(f"F{field} missing")
    rows = list(RESULT.finditer(sections.get(3, "")))
    numbers = {row.group(1) for row in rows}
    if not numbers:
        findings.append("F3 has no numbered result rows")
    if len(numbers) != len(rows):
        findings.append("F3 has duplicate result identifiers")
    required = {row.group(1) for row in rows if re.search(r"\bstated\b", row.group(2))}
    covered = references(sections.get(2, ""))
    for number in sorted(required - covered):
        findings.append(f"Stated result {number} has no F2 proof reference")
    for number in sorted(covered - numbers):
        findings.append(f"F2 refers to unknown result {number}")
    directives = []
    for wave in sorted(root.glob("wave*")):
        if not wave.is_dir():
            continue
        for directive in sorted(wave.glob("*.md")):
            if not re.match(r"[A-Z]\d+", directive.name):
                continue
            directives.append(str(directive.relative_to(root)))
            used = references(directive.read_text())
            if not used:
                findings.append(f"{directive.name} names no result line")
            for number in sorted(used - numbers):
                findings.append(f"{directive.name} refers to unknown result {number}")
    return {"blocking": len(findings), "findings": findings,
            "results": sorted(numbers), "directives_checked": directives,
            "scope": "structure and result references; no behavioral or source-authority proof"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        result = check(args.root)
    except (OSError, UnicodeError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    print(json.dumps(result, indent=2))
    return 1 if result["blocking"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
