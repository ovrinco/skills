#!/usr/bin/env python3
"""Validate frozen requirements, ownership and explicit acceptance without executing a task."""
import argparse
import hashlib
import json
from pathlib import Path

def confined(root, relative):
    value = Path(relative)
    if value.is_absolute():
        raise ValueError("expected a relative path")
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("path escapes its root")
    return path

def overlaps(first, second):
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)

def check(path):
    data = json.loads(path.read_text())
    base = path.parent.resolve()
    findings = []
    source = confined(base, data["source"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != data["source_sha256"]:
        findings.append("requirements source changed")
    requirements = json.loads(source.read_text())
    known = {}
    for requirement in requirements:
        ident = requirement["id"]
        if ident in known:
            findings.append("duplicate requirement: " + ident)
        known[ident] = requirement
    project = confined(base, data["project_root"])
    protected = [confined(project, value) for value in data.get("protected", [])]
    served = set()
    deferred = set()
    for item in data.get("deferred", []):
        ident = item["id"]
        if ident not in known or not item.get("reason", "").strip():
            findings.append("invalid deferral: " + str(ident))
        if ident in deferred:
            findings.append("duplicate deferral: " + ident)
        deferred.add(ident)
    tasks = data["tasks"]
    if not tasks:
        findings.append("no tasks")
    ids = set()
    owners = []
    for task in tasks:
        ident = task["id"]
        if ident in ids:
            findings.append("duplicate task: " + ident)
        ids.add(ident)
        if not task.get("requires"):
            findings.append("task has no requirements: " + ident)
        if not task.get("acceptance") or any(not str(x).strip() for x in task["acceptance"]):
            findings.append("task has no concrete acceptance: " + ident)
        if not task.get("writes"):
            findings.append("task has no declared writes: " + ident)
        for requirement in task.get("requires", []):
            rid = requirement["id"]
            if rid not in known or requirement != known[rid]:
                findings.append("requirement differs from source: " + rid)
            served.add(rid)
        for value in task.get("writes", []):
            target = confined(project, value)
            if any(overlaps(target, item) for item in protected):
                findings.append("protected write: " + ident + " / " + value)
            for other, previous in owners:
                if other != ident and overlaps(target, previous):
                    findings.append("overlapping writes: " + other + " / " + ident)
            owners.append((ident, target))
    for rid in sorted(set(known) - served - deferred):
        findings.append("unserved requirement: " + rid)
    for rid in sorted(served & deferred):
        findings.append("served and deferred: " + rid)
    return findings

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    args = parser.parse_args()
    try:
        findings = check(args.pack.resolve())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"valid": False, "error": str(error)}))
        return 2
    print(json.dumps({"valid": not findings, "findings": findings}, indent=2))
    return 1 if findings else 0

if __name__ == "__main__":
    raise SystemExit(main())
