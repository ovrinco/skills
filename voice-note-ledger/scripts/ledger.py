#!/usr/bin/env python3
"""Validate a model-written ledger.json and render ledger.md with its date-and-trigger index
(voice-note-ledger, component B, mechanical half).

  ledger.py LEDGER_JSON_OR_OUT_DIR [--out ledger.md] [--title T] [--source S] [--corrections corrections.json]
                        [--units N] [--check]
  ledger.py --from-md TABLE.md [--out ledger.json]     convert a markdown ledger table to ledger.json

The extraction itself (what is actionable, what is an open question, and so on) is model work done
from the corrected transcript. This script only checks that the result is well formed and renders it.

ledger.json is a JSON array of entries (an object with an "entries" array is also accepted):
  id        VN-NNN, unique, in ascending order (gaps allowed; never reuse a dropped id)
  category  Action | Open question | Reminder | Research | Proposal | Direction / constraint |
            Hypothesis | Observation | Reference | Decision | Risk / dependency
  area      subject or project the entry belongs to
  capture   the item, succinct, one line
  stance    how firmly it was said (explicit, tentative, recalled, self-reported, ...)
  timing    when or what triggers it, as stated (use YYYY-MM-DD or "Month YYYY" for calendar anchors)
  sources   list of ids: voxtype:<folder>:<segment>, voxtype:<folder>:<first>-<last>,
            voxtype:<folder>:<segment>@<char offset>, or L<line>, L<first>-L<last> for pasted text

Exit codes: 0 valid (and rendered), 1 schema errors, 2 unreadable input or bad usage.
Standard library only. Never writes inside VoxType storage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CATEGORIES = ("Action", "Open question", "Reminder", "Research", "Proposal", "Direction / constraint",
              "Hypothesis", "Observation", "Reference", "Decision", "Risk / dependency")
FIELDS = ("id", "category", "area", "capture", "stance", "timing", "sources")
HEADER = ("ID", "Category", "Area", "Capture", "Stance / qualification", "Timing / trigger", "Source lines")
ID_RE = re.compile(r"^VN-\d{3}$")
LINE_RE = re.compile(r"^L(\d+)(?:[-\u2013]L?(\d+))?$")
VOX_RE = re.compile(r"^voxtype:([^:\s]+):(\d+)(?:[-\u2013](\d+))?(?:@(\d+)(?:[-\u2013](\d+))?)?$")
VOXTYPE_ROOT = Path.home() / ".local" / "share" / "voxtype"
RULES = ("Tentative ideas stay proposals. Nothing in this ledger is scheduled, executed or committed; "
         "it records what was said and how firmly.")

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], 1)}
ISO_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
MONTH_RE = re.compile(r"\b(" + "|".join(MONTHS) + r")\.?\s+(20\d{2})\b", re.I)
TRIGGERS = (
    ("No date stated", re.compile(r"\bno (?:deadline|date)\b|\bnot stated\b|\bnone stated\b", re.I)),
    ("Before", re.compile(r"\bbefore\b", re.I)),
    ("After / once", re.compile(r"\bafter\b|\bonce\b", re.I)),
    ("When / if", re.compile(r"\bwhen(?:ever)?\b|\bif\b", re.I)),
    ("During / ongoing", re.compile(r"\bduring\b|\bthroughout\b|\bongoing\b|\buntil\b|\balongside\b|\bwhile\b",
                                    re.I)),
)
OTHER_TRIGGER = "Topic / situation"
TENTATIVE = re.compile(r"\b(tentative|tentatively|proposed|proposal|maybe|might|leaning|not decided|undecided|"
                       r"not a mandate|explicitly tentative)\b", re.I)


class UsageError(Exception):
    """Unreadable input or bad usage. The CLI exits 2."""


class LedgerFormatError(Exception):
    """The file is not a ledger at all. The CLI exits 1."""


# --------------------------------------------------------------------------------------------
# loading and conversion
# --------------------------------------------------------------------------------------------

def load_ledger(path):
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise UsageError(f"{p}: {exc}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LedgerFormatError(f"{p}: not valid JSON ({exc})")
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        data = data["entries"]
    if not isinstance(data, list):
        raise LedgerFormatError(f"{p}: expected a JSON array of entries")
    return data


def split_row(line: str):
    cells = re.split(r"(?<!\\)\|", line.strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return [c.strip().replace("\\|", "|") for c in cells]


def parse_md_table(text: str):
    """Convert a seven-column markdown ledger table into a list of entries."""
    entries = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = split_row(line)
        if tuple(cells) == HEADER or (cells and cells[0] == "ID"):
            continue
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue
        if len(cells) != len(FIELDS):
            raise LedgerFormatError(f"table row has {len(cells)} cells, expected {len(FIELDS)}: {line[:70]}")
        sources = [s.strip().replace("\u2013", "-") for s in cells[6].split(",") if s.strip()]
        entries.append({"id": cells[0], "category": cells[1], "area": cells[2], "capture": cells[3],
                        "stance": cells[4], "timing": cells[5], "sources": sources})
    if not entries:
        raise LedgerFormatError("no ledger table rows found")
    return entries


def dump_entries(entries) -> str:
    """JSON with one field per line and the sources list inline, for readable diffs."""
    out = ["["]
    for i, e in enumerate(entries):
        out.append("  {")
        keys = list(e)
        for j, k in enumerate(keys):
            comma = "," if j < len(keys) - 1 else ""
            out.append(f"    {json.dumps(k)}: {json.dumps(e[k], ensure_ascii=False)}{comma}")
        out.append("  }" + ("," if i < len(entries) - 1 else ""))
    out.append("]")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------------------------
# source ids and validation
# --------------------------------------------------------------------------------------------

def parse_source_id(sid):
    if not isinstance(sid, str):
        return None
    m = LINE_RE.match(sid)
    if m:
        first = int(m.group(1))
        last = int(m.group(2)) if m.group(2) else first
        return {"kind": "text", "first": first, "last": last}
    m = VOX_RE.match(sid)
    if m:
        first = int(m.group(2))
        last = int(m.group(3)) if m.group(3) else first
        off_a = int(m.group(4)) if m.group(4) else None
        off_b = int(m.group(5)) if m.group(5) else off_a
        return {"kind": "voxtype", "folder": m.group(1), "first": first, "last": last,
                "off_first": off_a, "off_last": off_b}
    return None


def display_source(sid: str) -> str:
    return sid.replace("-", "\u2013") if LINE_RE.match(sid) else sid


def source_count(src):
    """Source units that citations address: a text note's source lines ("lines", written since 29 Oct 2026, when
    "units" became its count of non-empty lines), else "units"."""
    return src.get("lines", src.get("units", 0)) if src.get("kind") == "text" else src.get("units", 0)


def check_source_id(sid, corr=None, units=None):
    """Return a list of problems with one source id."""
    p = parse_source_id(sid)
    if p is None:
        return [f"source {sid!r} is not voxtype:<folder>:<segment>[-<last>][@<offset>] or L<line>[-L<last>]"]
    problems = []
    if p["last"] < p["first"]:
        problems.append(f"source {sid!r}: range runs backwards")
    if p["kind"] == "text" and p["first"] < 1:
        problems.append(f"source {sid!r}: line numbers start at 1")
    if p["kind"] == "voxtype" and p["off_first"] is not None:
        if p["last"] != p["first"]:
            problems.append(f"source {sid!r}: an @offset needs a single segment, not a range")
        if p["off_last"] < p["off_first"]:
            problems.append(f"source {sid!r}: offset range runs backwards")
    src = (corr or {}).get("source", {})
    if src:
        if src.get("kind") != p["kind"]:
            problems.append(f"source {sid!r}: this note's units are {src.get('unit')}s ({src.get('ref')})")
        elif p["kind"] == "voxtype" and src.get("ref") != f"voxtype:{p['folder']}":
            problems.append(f"source {sid!r}: not the folder of this note ({src.get('ref')})")
        else:
            first_index, n = src.get("first_index", 0), source_count(src)
            if p["first"] < first_index or p["last"] >= first_index + n:
                problems.append(f"source {sid!r}: {src.get('unit')} out of range "
                                f"({first_index} to {first_index + n - 1})")
            lengths = corr.get("unit_lengths") or []
            if p["kind"] == "voxtype" and p["off_last"] is not None and not problems:
                pos = p["first"] - first_index
                if 0 <= pos < len(lengths) and p["off_last"] > lengths[pos]:
                    problems.append(f"source {sid!r}: offset past the end of the segment ({lengths[pos]} characters)")
    elif units is not None:
        limit_ok = p["last"] < units if p["kind"] == "voxtype" else p["last"] <= units
        if not limit_ok:
            problems.append(f"source {sid!r}: beyond the {units} units of this note")
    return problems


def validate(entries, corr=None, units=None):
    """Return (errors, warnings). Errors make the CLI exit 1; warnings never do."""
    errors, warnings = [], []
    if not isinstance(entries, list) or not entries:
        return ["a ledger needs at least one entry"], warnings
    seen = set()
    last_id = None
    for n, e in enumerate(entries):
        where = f"entry {n}"
        if not isinstance(e, dict):
            errors.append(f"{where}: not an object")
            continue
        eid = e.get("id")
        if isinstance(eid, str) and eid:
            where = eid
        missing = [k for k in FIELDS if k not in e]
        extra = [k for k in e if k not in FIELDS]
        if missing:
            errors.append(f"{where}: missing field(s) {', '.join(missing)}")
        if extra:
            errors.append(f"{where}: unknown field(s) {', '.join(extra)}")
        if "id" in e:
            if not isinstance(eid, str) or not ID_RE.match(eid):
                errors.append(f"{where}: id must look like VN-001")
            else:
                if eid in seen:
                    errors.append(f"{where}: duplicate id")
                elif last_id is not None and eid < last_id:
                    errors.append(f"{where}: ids must be in ascending order (after {last_id})")
                seen.add(eid)
                last_id = eid if last_id is None or eid > last_id else last_id
        if "category" in e and e["category"] not in CATEGORIES:
            errors.append(f"{where}: category {e['category']!r} is not one of: {'; '.join(CATEGORIES)}")
        for k in ("area", "capture", "stance", "timing"):
            if k in e:
                v = e[k]
                if not isinstance(v, str) or not v.strip():
                    errors.append(f"{where}: {k} must be a non-empty string")
                elif "\n" in v or "\r" in v:
                    errors.append(f"{where}: {k} must be one line")
        if "sources" in e:
            s = e["sources"]
            if not isinstance(s, list) or not s:
                errors.append(f"{where}: sources must be a non-empty list of ids")
            else:
                for sid in s:
                    errors.extend(f"{where}: {m}" for m in check_source_id(sid, corr, units))
        cap, stance = e.get("capture"), e.get("stance")
        if isinstance(cap, str) and len(cap) > 420:
            warnings.append(f"{where}: capture is {len(cap)} characters; keep entries succinct")
        if e.get("category") == "Open question" and isinstance(cap, str) and "?" not in cap:
            warnings.append(f"{where}: an Open question capture usually contains the question mark")
        if e.get("category") in ("Action", "Reminder") and isinstance(stance, str) and TENTATIVE.search(stance):
            warnings.append(f"{where}: stance reads tentative; consider Proposal instead of {e['category']}")
    return errors, warnings


# --------------------------------------------------------------------------------------------
# index and rendering
# --------------------------------------------------------------------------------------------

def date_keys(timing: str):
    keys = set()
    for m in ISO_RE.finditer(timing):
        y, mo, d = (int(x) for x in m.groups())
        if 1 <= mo <= 12 and 1 <= d <= 31:
            keys.add(f"{y:04d}-{mo:02d}-{d:02d}")
    for m in MONTH_RE.finditer(timing):
        keys.add(f"{int(m.group(2)):04d}-{MONTHS[m.group(1).lower()]:02d}")
    return sorted(keys)


def trigger_class(timing: str) -> str:
    for name, rx in TRIGGERS:
        if rx.search(timing):
            return name
    return OTHER_TRIGGER


def build_index(entries):
    dated, triggered = [], []
    for e in entries:
        keys = date_keys(e["timing"])
        if keys:
            for k in keys:
                dated.append((k, e["id"], e))
        else:
            triggered.append((trigger_class(e["timing"]), e["id"], e))
    order = [n for n, _ in TRIGGERS] + [OTHER_TRIGGER]
    dated.sort(key=lambda t: (t[0], t[1]))
    triggered.sort(key=lambda t: (order.index(t[0]), t[1]))
    return dated, triggered


def cell(s: str) -> str:
    return s.replace("|", "\\|")


def row(cells) -> str:
    return "| " + " | ".join(cells) + " |"


def category_counts(entries):
    counts = {c: 0 for c in CATEGORIES}
    for e in entries:
        counts[e["category"]] += 1
    return counts


def render_md(entries, title=None, source=None) -> str:
    counts = category_counts(entries)
    dated, triggered = build_index(entries)
    lines = [f"# Ledger: {title}" if title else "# Ledger", ""]
    if source:
        lines += [f"Source: {source}", ""]
    lines.append(f"Entries: {len(entries)}. " + ", ".join(f"{c} {n}" for c, n in counts.items() if n))
    lines += ["", RULES, ""]
    lines.append(row(HEADER))
    lines.append("|" + "---|" * len(HEADER))
    for e in entries:
        lines.append(row([e["id"], e["category"], cell(e["area"]), cell(e["capture"]), cell(e["stance"]),
                          cell(e["timing"]), cell(", ".join(display_source(s) for s in e["sources"]))]))
    lines += ["", "## Date-and-trigger index", "",
              f"{len({i for _, i, _ in dated})} entries carry a calendar anchor; "
              f"{len(triggered)} depend on a trigger or state no date.", "", "### Dated", ""]
    if dated:
        lines.append(row(("Date", "ID", "Category", "Area", "Timing / trigger")))
        lines.append("|---|---|---|---|---|")
        for k, i, e in dated:
            lines.append(row([k, i, e["category"], cell(e["area"]), cell(e["timing"])]))
    else:
        lines.append("None.")
    lines += ["", "### Triggers", ""]
    if triggered:
        lines.append(row(("Trigger", "ID", "Category", "Area", "Timing / trigger")))
        lines.append("|---|---|---|---|---|")
        for k, i, e in triggered:
            lines.append(row([k, i, e["category"], cell(e["area"]), cell(e["timing"])]))
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------------
# coverage and CLI
# --------------------------------------------------------------------------------------------

def coverage(entries, corr):
    """Return (content units, uncited content units). Empty units carry nothing to cite."""
    src = corr.get("source", {})
    first_index, n = src.get("first_index", 0), source_count(src)
    lengths = corr.get("unit_lengths") or []
    cited = set()
    for e in entries:
        for sid in e["sources"]:
            p = parse_source_id(sid)
            if p and p["kind"] == src.get("kind"):
                cited.update(range(p["first"], p["last"] + 1))
    content = [first_index + i for i in range(n) if i >= len(lengths) or lengths[i] > 0]
    return content, [u for u in content if u not in cited]


def compress(nums):
    out, start, prev = [], None, None
    for x in nums:
        if start is None:
            start = prev = x
        elif x == prev + 1:
            prev = x
        else:
            out.append(str(start) if start == prev else f"{start}-{prev}")
            start = prev = x
    if start is not None:
        out.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(out)


def load_corrections(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UsageError(f"{path}: cannot read corrections.json ({exc})")
    if not isinstance(data, dict) or "source" not in data:
        raise UsageError(f"{path}: not a corrections.json written by normalize.py")
    return data


def guard_out(out: Path) -> None:
    target = out.expanduser().resolve()
    root = VOXTYPE_ROOT.resolve()
    if target == root or root in target.parents:
        raise UsageError(f"refusing to write into {root} (VoxType storage is read-only evidence)")


def build_parser():
    ap = argparse.ArgumentParser(
        prog="ledger.py", description="Validate ledger.json and render ledger.md with its date-and-trigger index.",
        epilog="Exit codes: 0 valid, 1 schema errors, 2 unreadable input or bad usage.")
    ap.add_argument("ledger", nargs="?",
                    help="ledger.json written by the model, or an output directory holding ledger.json "
                         "(its corrections.json is then used automatically)")
    ap.add_argument("--out", help="output file (default: ledger.md beside ledger.json; with --from-md, ledger.json)")
    ap.add_argument("--title", help="title for the ledger.md heading")
    ap.add_argument("--source", help="source line for the ledger.md header (default: from --corrections)")
    ap.add_argument("--corrections", help="corrections.json from normalize.py, to check ids against the real units")
    ap.add_argument("--units", type=int, help="number of units in the note, when there is no corrections.json")
    ap.add_argument("--check", action="store_true", help="validate only; write nothing")
    ap.add_argument("--from-md", metavar="TABLE.md", help="convert a markdown ledger table to ledger.json")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        if args.from_md:
            try:
                text = Path(args.from_md).read_text(encoding="utf-8")
            except OSError as exc:
                raise UsageError(f"{args.from_md}: {exc}")
            entries = parse_md_table(text)
            errors, warnings = validate(entries)
            if errors:
                print("\n".join(f"error: {m}" for m in errors), file=sys.stderr)
                return 1
            out = Path(args.out) if args.out else Path(args.from_md).with_name("ledger.json")
            guard_out(out)
            out.write_text(dump_entries(entries), encoding="utf-8")
            print(f"ledger: converted {len(entries)} entries from {args.from_md} to {out}")
            return 0
        if not args.ledger:
            ap.error("a ledger.json is required (or use --from-md)")
        ledger_path = Path(args.ledger)
        corrections_path = args.corrections
        if ledger_path.is_dir():  # an output directory: use its ledger.json and, if present, corrections.json
            if not corrections_path and (ledger_path / "corrections.json").is_file():
                corrections_path = ledger_path / "corrections.json"
            ledger_path = ledger_path / "ledger.json"
        entries = load_ledger(ledger_path)
        corr = load_corrections(corrections_path) if corrections_path else None
        errors, warnings = validate(entries, corr, args.units)
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        if errors:
            print("\n".join(f"error: {m}" for m in errors), file=sys.stderr)
            print(f"ledger: {len(errors)} error(s); nothing written", file=sys.stderr)
            return 1
        counts = category_counts(entries)
        print(f"ledger: {len(entries)} entries valid  [" + ", ".join(f"{c} {n}" for c, n in counts.items() if n) + "]")
        if corr:
            content, missing = coverage(entries, corr)
            unit = corr["source"].get("unit", "unit")
            print(f"  coverage: {len(content) - len(missing)} of {len(content)} non-empty {unit}s cited"
                  + (f"; uncited {unit}s: {compress(missing)}" if missing else ""))
        dated, triggered = build_index(entries)
        print(f"  index: {len({i for _, i, _ in dated})} dated, {len(triggered)} trigger-based")
        if args.check:
            return 0
        source = args.source or (corr["source"].get("ref") if corr else None)
        title = args.title or (corr["source"].get("metadata", {}).get("title") if corr else None)
        out = Path(args.out) if args.out else ledger_path.with_name("ledger.md")
        guard_out(out)
        out.write_text(render_md(entries, title, source), encoding="utf-8")
        print(f"  wrote {out}")
        return 0
    except LedgerFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except UsageError as exc:
        print(f"ledger.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
