#!/usr/bin/env python3
"""Validate a supplied synthetic case manifest. No harness or model is launched."""
import argparse
import hashlib
import json
from pathlib import Path
import re

def validate(data, skill):
    findings = []
    expected = hashlib.sha256(skill.read_bytes()).hexdigest()
    if data.get("skill_sha256") != expected:
        findings.append("Skill hash differs from the supplied source")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        return findings + ["No cases supplied"]
    ids = [case.get("id") for case in cases]
    if any(not isinstance(identity, str) or not identity for identity in ids) or len(set(ids)) != len(ids):
        findings.append("Case IDs must be nonempty and unique")
    kinds = {case.get("kind") for case in cases}
    if not {"must-trigger", "neighbor"}.issubset(kinds):
        findings.append("Trigger and neighbor cases are required")
    for case in cases:
        if case.get("kind") not in {"must-trigger", "neighbor", "border"}:
            findings.append("Unknown case kind")
        if not case.get("request") or not case.get("criteria") or not case.get("expected"):
            findings.append("Each case needs request, criteria and expected result")
    return findings

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--skill", required=True, type=Path)
    args = parser.parse_args()
    try:
        findings = validate(json.loads(args.manifest.read_text()), args.skill)
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    print(json.dumps({"blocking": len(findings), "findings": findings,
                      "scope": "case preparation only; no sessions run"}, indent=2))
    return 1 if findings else 0

if __name__ == "__main__":
    raise SystemExit(main())
