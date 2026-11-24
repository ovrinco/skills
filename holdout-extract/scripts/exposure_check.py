#!/usr/bin/env python3
"""Read-only builder-input exposure lint; not a filesystem isolation mechanism."""
import argparse
import json
from pathlib import Path

def check(roots, withheld, marker):
    if not withheld.is_file():
        raise ValueError(f"Withheld input is not a file: {withheld}")
    findings = []
    files = 0
    text_files = 0
    needles = {str(withheld), str(withheld.resolve()), withheld.name, marker}
    for root in roots:
        if not root.exists():
            raise ValueError(f"Input does not exist: {root}")
        paths = sorted(root.rglob("*")) if root.is_dir() else [root]
        for path in paths:
            if path.is_symlink():
                findings.append({"file": str(path), "reason": "symlink needs explicit input review"})
                continue
            if not path.is_file():
                continue
            files += 1
            data = path.read_bytes()
            if b"\0" in data:
                findings.append({"file": str(path), "reason": "binary input needs manual review"})
                continue
            text = data.decode("utf-8", errors="strict")
            text_files += 1
            for number, line in enumerate(text.splitlines(), 1):
                if any(needle in line for needle in needles):
                    findings.append({"file": str(path), "line": number,
                                     "reason": "withheld path or marker reference"})
    if not text_files:
        findings.append({"reason": "no readable text files searched"})
    return {"files_searched": files, "text_files_searched": text_files,
            "blocking": len(findings), "findings": findings}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--withheld", required=True, type=Path)
    parser.add_argument("--marker", required=True)
    parser.add_argument("roots", nargs="+", type=Path)
    args = parser.parse_args()
    if not args.marker.strip():
        parser.error("marker must be nonempty")
    try:
        result = check(args.roots, args.withheld, args.marker)
    except (OSError, ValueError, UnicodeError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    print(json.dumps(result, indent=2))
    return 1 if result["blocking"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
