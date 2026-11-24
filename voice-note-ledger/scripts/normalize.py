#!/usr/bin/env python3
"""Names-only cleanup of a voice-note transcript (voice-note-ledger, component A).

  normalize.py SOURCE [--out DIR] [--decisions FILE] [--verbatim FILE] [--names FILE] [--name LABEL] [--dry-run]
  normalize.py --check PATH [PATH ...]      exit 1 if any known variant survives in the deliverables
  normalize.py SOURCE --locate PHRASE       print source ids (with @offset) where PHRASE occurs
  normalize.py --lint-names                 validate names.json

SOURCE is a VoxType note folder (or its transcript.json, or a bare folder name under
~/.local/share/voxtype/meetings/), a text file, or "-" for stdin. The script reads the source and
never writes to it or anywhere inside VoxType storage.

Writes <out>/corrected_transcript.md (every segment or line kept at its index) and
<out>/corrections.json (every correction: segment, before, after; plus flagged items).
Default <out> is ~/06_memory/runs/voice/<note folder>/ . Only project and product names and their
capitalization are changed; every other byte of every segment is preserved. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
NAMES_PATH = SKILL_DIR / "names.json"
VOXTYPE_ROOT = Path.home() / ".local" / "share" / "voxtype"
MEETINGS_DIR = VOXTYPE_ROOT / "meetings"
RUNS_ROOT = Path.cwd() / "voice-output"
SCHEMA = "voice-note-ledger/corrections@1"
CARRIER = "corrected_transcript.md"
CORRECTIONS = "corrections.json"
WINDOW = 200  # characters either side of an ambiguous word searched for a supporting cue
SEP = r"[ \t\u00a0]+"
NAME_KEYS = {"canonical", "variants", "notes", "gated_variants", "cues", "blockers", "cue", "window", "recognized_forms", "form_rules"}


class UsageError(Exception):
    """Bad input or usage. The CLI exits 2."""


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------

def norm_form(s: str) -> str:
    return re.sub(SEP, " ", s.lower())


def phrase_regex(phrase: str) -> str:
    return SEP.join(re.escape(p) for p in phrase.split(" "))


def word_regex(forms) -> "re.Pattern[str]":
    ordered = sorted(set(forms), key=lambda f: (-len(f), f))
    return re.compile(r"(?<!\w)(?:" + "|".join(phrase_regex(f) for f in ordered) + r")(?!\w)", re.I)


def overlaps(spans, s: int, e: int) -> bool:
    return any(a < e and s < b for a, b in spans)


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_") or "note"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def within_one(a: str, b: str) -> bool:
    """True when a and b differ by exactly one insertion, deletion, substitution or adjacent swap."""
    if a == b:
        return False
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diffs = [i for i in range(la) if a[i] != b[i]]
        if len(diffs) == 1:
            return True
        return (len(diffs) == 2 and diffs[1] == diffs[0] + 1
                and a[diffs[0]] == b[diffs[1]] and a[diffs[1]] == b[diffs[0]])
    if la > lb:
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


# --------------------------------------------------------------------------------------------
# names.json
# --------------------------------------------------------------------------------------------

def lint_names(data) -> list:
    """Return a list of problems (empty when names.json is sound)."""
    problems = []
    if not isinstance(data, list) or not data:
        return ["names.json must be a non-empty JSON array of entries"]
    canon_seen = {}
    owner = {}
    canon_forms = {}
    for i, e in enumerate(data):
        label = f"entry {i}"
        if not isinstance(e, dict):
            problems.append(f"{label}: not an object")
            continue
        c = e.get("canonical")
        if not isinstance(c, str) or not c or c != c.strip():
            problems.append(f"{label}: 'canonical' must be a non-empty string with no surrounding spaces")
            continue
        label = repr(c)
        key = norm_form(c)
        if key in canon_seen:
            problems.append(f"{label}: duplicate canonical (also entry {canon_seen[key]})")
        canon_seen[key] = i
        canon_forms[key] = c
        for k in e:
            if k not in NAME_KEYS:
                problems.append(f"{label}: unknown key {k!r}")
        notes = e.get("notes")
        if not isinstance(notes, str) or not notes.strip():
            problems.append(f"{label}: 'notes' must be a non-empty string")
        if "cue" in e and not isinstance(e["cue"], bool):
            problems.append(f"{label}: 'cue' must be true or false")
        if "window" in e and (not isinstance(e["window"], int) or isinstance(e["window"], bool)
                              or not 20 <= e["window"] <= 1000):
            problems.append(f"{label}: 'window' must be an integer from 20 to 1000")
        lists = {}
        for field in ("variants", "gated_variants", "cues", "blockers", "recognized_forms"):
            if field not in e:
                if field == "variants":
                    problems.append(f"{label}: missing 'variants'")
                lists[field] = []
                continue
            v = e[field]
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                problems.append(f"{label}: {field!r} must be an array of strings")
                lists[field] = []
                continue
            seen = set()
            for x in v:
                if not x or x != x.strip() or x != x.lower() or "  " in x or "\n" in x:
                    problems.append(f"{label}: {field} entry {x!r} must be lowercase, trimmed, single-spaced, non-empty")
                if field == "cues" and x[:1] in ("+", "-") and not x[1:].strip():
                    problems.append(f"{label}: cue {x!r} needs a word after the prefix")
                if x in seen:
                    problems.append(f"{label}: duplicate {field} entry {x!r}")
                seen.add(x)
            lists[field] = v
        rules = e.get("form_rules", {})
        if not isinstance(rules, dict):
            problems.append(f"{label}: form_rules must be an object")
        else:
            recognized = {key} | set(lists["variants"]) | set(lists["gated_variants"]) | set(lists["recognized_forms"])
            for form, rule in rules.items():
                if form not in recognized or not isinstance(rule, dict) or rule.get("default") not in {"apply", "flag", "keep"}:
                    problems.append(f"{label}: invalid form rule")
                    continue
                for kind in ("name", "ordinary", "uncertain"):
                    cue = rule.get(kind, {})
                    if not isinstance(cue, dict):
                        problems.append(f"{label}: invalid occurrence cues")
                        continue
                    for field in ("terms", "left", "right", "patterns"):
                        if not isinstance(cue.get(field, []), list) or not all(isinstance(x, str) for x in cue.get(field, [])):
                            problems.append(f"{label}: invalid occurrence cue list")
                    for pattern in cue.get("patterns", []) + cue.get("left", []) + cue.get("right", []):
                        try: re.compile(pattern, re.I)
                        except re.error: problems.append(f"{label}: invalid occurrence regex")
        for x in lists["gated_variants"]:
            if x in lists["variants"]:
                problems.append(f"{label}: {x!r} is both a variant and a gated variant")
        for field in ("variants", "gated_variants", "recognized_forms"):
            for x in lists[field]:
                f = norm_form(x)
                if f == key:
                    continue
                if f in owner and owner[f] != key:
                    problems.append(f"{label}: {field} entry {x!r} is already claimed by {canon_forms.get(owner[f], owner[f])!r}")
                owner[f] = key
    for f, k in owner.items():
        if f in canon_seen and f != k:
            problems.append(f"variant {f!r} of {canon_forms[k]!r} equals the canonical name {canon_forms[f]!r}")
    return problems


class Names:
    """Compiled view of names.json."""

    def __init__(self, entries, path=None, digest=None):
        self.entries = entries
        self.path = str(path) if path else None
        self.digest = digest
        self.alts = {}  # normalized form -> (entry index, tier) with tier in canon|auto|gated
        for idx, e in enumerate(entries):
            canon_l = norm_form(e["canonical"])
            gated = {norm_form(v) for v in e.get("gated_variants", [])}
            self.alts[canon_l] = (idx, "gated" if canon_l in gated else "canon")
            for v in e["variants"]:
                f = norm_form(v)
                if f != canon_l:
                    self.alts[f] = (idx, "auto")
            for f in gated:
                if f != canon_l:
                    self.alts[f] = (idx, "gated")
            for f in e.get("recognized_forms", []):
                self.alts[norm_form(f)] = (idx, "recognized")
        self.rx = word_regex(self.alts)
        self.cue_forms = sorted(
            f for f, (i, t) in self.alts.items() if t not in {"gated", "recognized"} and self.entries[i].get("cue", True))
        self.near_targets = [(e["canonical"].lower(), e["canonical"])
                             for e in entries if re.fullmatch(r"[A-Za-z]{6,}", e["canonical"])]
        self._cue_cache = {}
        self._adj_cache = {}
        self._blocker_cache = {}

    def adjacent_regexes(self, idx):
        """Compile the +word (next word) and -word (previous word) cues of an entry."""
        if idx in self._adj_cache:
            return self._adj_cache[idx]
        cues = self.entries[idx].get("cues", [])
        gap = r"[ \t\u00a0\-]{1,3}"
        after = [norm_form(c[1:]) for c in cues if c.startswith("+")]
        before = [norm_form(c[1:]) for c in cues if c.startswith("-")]
        a = re.compile(gap + r"(" + "|".join(phrase_regex(f) for f in sorted(after, key=lambda f: (-len(f), f)))
                       + r")(?!\w)", re.I) if after else None
        b = re.compile(r"(?<!\w)(" + "|".join(phrase_regex(f) for f in sorted(before, key=lambda f: (-len(f), f)))
                       + r")" + gap + r"$", re.I) if before else None
        self._adj_cache[idx] = (a, b)
        return a, b

    def cue_regex(self, idx):
        if idx in self._cue_cache:
            return self._cue_cache[idx]
        e = self.entries[idx]
        cues = e.get("cues", [])
        if not cues:  # no cues means flag-only: an ordinary word that is never corrected automatically
            self._cue_cache[idx] = None
            return None
        words = {norm_form(c) for c in cues if c != "@names" and c[0] not in "+-"}
        words.update(f for f, (i, t) in self.alts.items() if i == idx and t not in {"gated", "recognized"})  # own canonical and variants
        if "@names" in cues:
            words.update(self.cue_forms)
        rx = word_regex(words) if words else None
        self._cue_cache[idx] = rx
        return rx

    def blocked(self, idx, text, s, e) -> bool:
        blockers = self.entries[idx].get("blockers")
        if not blockers:
            return False
        rx = self._blocker_cache.get(idx)
        if rx is None:
            rx = word_regex(norm_form(b) for b in blockers)
            self._blocker_cache[idx] = rx
        lo, hi = max(0, s - 60), min(len(text), e + 60)
        return any(m.start() <= s and m.end() >= e for m in rx.finditer(text, lo, hi))

    def window(self, idx) -> int:
        return self.entries[idx].get("window", WINDOW)


def load_names(path=None) -> Names:
    p = Path(path) if path else NAMES_PATH
    try:
        raw = p.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UsageError(f"{p}: cannot read names.json ({exc})")
    problems = lint_names(data)
    if problems:
        raise UsageError(f"{p}: names.json is invalid:\n  " + "\n  ".join(problems))
    return Names(data, p, sha256_bytes(raw))


# --------------------------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------------------------

class Source:
    def __init__(self, kind, ref, label, texts, first_index, path=None, sha256=None, meta=None):
        self.kind = kind  # "voxtype" or "text"
        self.ref = ref
        self.label = label
        self.texts = list(texts)
        self.first_index = first_index  # segments are zero-based, lines are one-based
        self.path = path
        self.sha256 = sha256
        self.meta = meta or {}

    @property
    def unit(self) -> str:
        return "segment" if self.kind == "voxtype" else "line"

    def index(self, pos: int) -> int:
        return self.first_index + pos

    def marker(self, idx: int) -> str:
        return f"[{idx}]" if self.kind == "voxtype" else f"[L{idx}]"

    def cite(self, idx: int, offset=None) -> str:
        if self.kind == "voxtype":
            return f"{self.ref}:{idx}" + (f"@{offset}" if offset is not None else "")
        return f"L{idx}"


def make_voxtype_source(segments, folder="test-note", path=None, meta=None) -> Source:
    return Source("voxtype", f"voxtype:{folder}", folder, segments, 0, path, None, meta)


def make_text_source(text: str, label="text") -> Source:
    return load_text_bytes(text.encode("utf-8"), label, None)


def load_voxtype(tj: Path) -> Source:
    raw = tj.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UsageError(f"{tj}: not valid UTF-8 JSON ({exc})")
    segs = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segs, list):
        raise UsageError(f"{tj}: no 'segments' list, so this is not a VoxType transcript.json")
    texts = []
    for i, s in enumerate(segs):
        t = s.get("text") if isinstance(s, dict) else None
        if not isinstance(t, str):
            raise UsageError(f"{tj}: segment {i} has no text string")
        texts.append(t)
    meta = {"total_chunks": data.get("total_chunks")}
    mj = tj.parent / "metadata.json"
    if mj.is_file():
        try:
            m = json.loads(mj.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            m = {}
        if isinstance(m, dict):
            for k in ("title", "started_at", "ended_at", "duration_secs", "status", "imported_from", "chunk_count",
                      "audio_retained"):
                if k in m:
                    meta[k] = m[k]
    folder = tj.parent.name
    return Source("voxtype", f"voxtype:{folder}", folder, texts, 0, str(tj), sha256_bytes(raw), meta)


def load_text_bytes(raw: bytes, label: str, path) -> Source:
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UsageError(f"{path or label}: not valid UTF-8 ({exc})")
    meta = {}
    if s.startswith("\ufeff"):
        s = s[1:]
        meta["bom"] = True
    if "\r\n" in s and s.count("\r") == s.count("\r\n"):
        s = s.replace("\r\n", "\n")
        meta["eol"] = "crlf"
    else:
        meta["eol"] = "lf"
    lines = s.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
        meta["final_newline"] = True
    else:
        meta["final_newline"] = False
    if not lines:
        raise UsageError(f"{path or label}: empty input")
    return Source("text", f"text:{label}", label, lines, 1, path, sha256_bytes(raw), meta)


def load_source(arg: str, label=None) -> Source:
    if arg == "-":
        return load_text_bytes(sys.stdin.buffer.read(), label or "stdin", None)
    p = Path(arg).expanduser()
    if p.is_dir():
        tj = p / "transcript.json"
        if not tj.is_file():
            raise UsageError(f"{p}: no transcript.json, so this is not a VoxType note folder")
        return load_voxtype(tj)
    if p.is_file():
        if p.suffix.lower() == ".json":
            return load_voxtype(p)
        return load_text_bytes(p.read_bytes(), label or slug(p.stem), str(p))
    raise UsageError(f"{arg}: not found")


# --------------------------------------------------------------------------------------------
# what must never be edited: code, URLs and paths, and operator-marked verbatim spans
# --------------------------------------------------------------------------------------------

_CODE_SPAN = re.compile(r"(?<!`)(`{1,3})(?!`)(.+?)(?<!`)\1(?!`)")
_URL = re.compile(r"://|^www\.", re.I)
_EMAIL = re.compile(r"\w@\w+\.\w")
_FILEDOM = re.compile(r"[A-Za-z0-9_]\.[A-Za-z][A-Za-z0-9]*")
_STRIP = "\"'`()[]{}<>,;:!?*"


def code_spans(text: str):
    return [m.span() for m in _CODE_SPAN.finditer(text)]


def fenced_lines(texts) -> set:
    fenced, opener = set(), None
    for i, t in enumerate(texts):
        m = re.match(r"^ {0,3}(`{3,}|~{3,})", t)
        if opener is None:
            if m:
                opener = m.group(1)[0]
                fenced.add(i)
        else:
            fenced.add(i)
            if m and m.group(1)[0] == opener:
                opener = None
    return fenced


def is_technical(text: str, s: int, e: int) -> bool:
    """True when the match sits inside a URL, e-mail, path, file name or domain-like token."""
    left = s
    while left > 0 and not text[left - 1].isspace():
        left -= 1
    right = e
    while right < len(text) and not text[right].isspace():
        right += 1
    tok = text[left:right].strip(_STRIP)
    if not tok:
        return False
    core = tok.rstrip(".")
    if _URL.search(tok) or _EMAIL.search(core):
        return True
    if tok.startswith(("/", "~/", "./", "../", "\\")) or re.match(r"[A-Za-z]:\\", tok):
        return True
    if re.match(r"\.[A-Za-z_]", tok):
        return True
    if "/" in core and "." in core:
        return True
    if "\\" in tok:
        return True
    return bool(_FILEDOM.search(core))


def find_exact(text: str, needle: str):
    out, start = [], 0
    while True:
        i = text.find(needle, start)
        if i < 0:
            return out
        out.append((i, i + len(needle)))
        start = i + max(1, len(needle))


def find_words(text: str, phrase: str):
    pre = r"(?<!\w)" if (phrase[0].isalnum() or phrase[0] == "_") else ""
    post = r"(?!\w)" if (phrase[-1].isalnum() or phrase[-1] == "_") else ""
    return [m.span() for m in re.finditer(pre + phrase_regex(phrase) + post, text)]


# --------------------------------------------------------------------------------------------
# scanning
# --------------------------------------------------------------------------------------------

def find_cue(names: Names, idx: int, ctx: str, s: int, e: int):
    """Why this ordinary word is the name: an adjacent cue word, or a cue within the entry's window (default WINDOW)."""
    after, before = names.adjacent_regexes(idx)
    if after:
        m = after.match(ctx, e)
        if m:
            return m.group(1).lower() + " (next word)"
    if before:
        m = before.search(ctx[max(0, s - 40):s])
        if m:
            return m.group(1).lower() + " (previous word)"
    rx = names.cue_regex(idx)
    if rx is None:
        return None
    reach = names.window(idx)
    left = ctx[max(0, s - reach):s]
    right = ctx[e:e + reach]
    best = None
    last = None
    for m in rx.finditer(left):
        last = m
    if last:
        best = (len(left) - last.end(), last.group(0))
    first = rx.search(right)
    if first and (best is None or first.start() < best[0]):
        best = (first.start(), first.group(0))
    return best[1].lower() if best else None


def _correction(s, e, before, canon, form, basis, cue=None):
    it = {"kind": "correction", "start": s, "end": e, "before": before, "after": canon, "name": canon,
          "variant": form, "basis": basis}
    if cue:
        it["cue"] = cue
    return it


def sentence_span(text, s, e):
    """Only the sentence containing this occurrence may supply name evidence."""
    lo = 0
    for delimiter in ".!?":
        lo = max(lo, text.rfind(delimiter, 0, s) + 1)
    hi = len(text)
    for delimiter in ".!?":
        p = text.find(delimiter, e)
        if p >= 0:
            hi = min(hi, p)
    # Segment/line separators alone do not end a sentence.
    return lo, hi


def occurrence_cue(spec, text, s, e, canonical=None):
    """Evidence is dictionary data. Name evidence is sentence constrained."""
    reach = spec.get("window", 80)
    lo, hi = sentence_span(text, s, e) if spec.get("sentence") else (0, len(text))
    left = text[max(lo, s - reach):s]
    right = text[e:min(hi, e + reach)]
    local = left + " " + right
    for term in spec.get("terms", []):
        if word_regex([term]).search(local):
            return term
    for field, part in (("left", left), ("right", right), ("patterns", local)):
        for pattern in spec.get(field, []):
            if re.search(pattern, part, re.I):
                return "dictionary pattern"
    matched = text[s:e]
    if spec.get("canonical_case") and canonical and matched == canonical:
        return "canonical spelling"
    if spec.get("capitalized") and matched[:1].isupper():
        return "capitalized project rendering"
    if spec.get("mid_capital") and matched[:1].isupper():
        before = text[lo:s].rstrip()
        if before and before[-1] not in ".!?":
            return "mid-sentence capitalization"
    return None


def form_action(names, idx, form, tier, text, s, e, ctx, base):
    entry = names.entries[idx]
    rule = entry.get("form_rules", {}).get(form)
    if not rule:
        legacy = find_cue(names, idx, ctx, base+s, base+e)
        return ("apply", legacy) if tier != "gated" or legacy else ("flag", None)
    nspec = rule.get("name", {})
    name = occurrence_cue(nspec, ctx, base+s, base+e, entry["canonical"])
    if nspec.get("legacy"):
        # orch-v11 Plan A point 2: inherited gated forms retain their installed
        # cue window; all other name cues retain round2 sentence boundaries.
        if form in entry.get("gated_variants", []):
            legacy = find_cue(names, idx, ctx, base+s, base+e)
        else:
            lo, hi = sentence_span(ctx, base+s, base+e)
            sentence = ctx[lo:hi]
            legacy = find_cue(names, idx, sentence, base+s-lo, base+e-lo)
        if legacy:
            name = legacy
    ordinary = occurrence_cue(rule.get("ordinary", {}), text, s, e)
    uncertainty = occurrence_cue(rule.get("uncertain", {}), text, s, e)
    if uncertainty or (name and ordinary):
        return "flag", "uncertain or conflicting occurrence cues"
    if name:
        return "apply", name
    if ordinary:
        return "keep", ordinary
    return "flag", None


def scan_unit(names: Names, text: str, ctx: str, base: int, silent, protected):
    """Log guarded actions without changing non-name bytes."""
    items, covered = [], []
    for m in names.rx.finditer(text):
        s, e = m.span()
        covered.append((s, e))
        if overlaps(silent, s, e) or overlaps(protected, s, e):
            continue
        matched = m.group(0)
        form = norm_form(matched)
        idx, tier = names.alts[form]
        canon = names.entries[idx]["canonical"]
        if is_technical(text, s, e):
            if matched != canon:
                items.append({"kind": "skipped", "start": s, "end": e, "text": matched, "candidate": canon,
                              "why": "url_or_path"})
            continue
        if names.blocked(idx, text, s, e):
            continue
        if matched == canon:
            identity_rule = names.entries[idx].get("form_rules", {}).get(form, {}).get("uncertain", {})
            # orch-v11 Plan A point 1: keep explicit identity flags, suppress
            # ordinary-conflict flags for already exact canonical spellings.
            if not occurrence_cue(identity_rule, text, s, e):
                continue
        action, cue = form_action(names, idx, form, tier, text, s, e, ctx, base)
        if action == "flag":
            items.append({"kind": "unresolved", "start": s, "end": e, "text": matched, "candidate": canon,
                          "why": "ambiguous", "note": cue or "occurrence has no decisive name or ordinary cue"})
        elif action == "apply" and matched != canon:
            basis = "cue" if tier == "gated" and cue else ("case" if form == norm_form(canon) else ("cue" if cue else "variant"))
            items.append(_correction(s, e, matched, canon, form, basis, cue))
    return items, covered


def near_misses(names: Names, text: str, covered, silent, protected):
    out = []
    for m in re.finditer(r"[A-Za-z]{6,}", text):
        s, e = m.span()
        if (s > 0 and (text[s - 1].isalnum() or text[s - 1] == "_")) or \
                (e < len(text) and (text[e].isalnum() or text[e] == "_")):
            continue
        if overlaps(covered, s, e) or overlaps(silent, s, e) or overlaps(protected, s, e):
            continue
        tl = m.group(0).lower()
        if tl in names.alts:
            continue
        for target, canon in names.near_targets:
            if within_one(tl, target):
                if not is_technical(text, s, e):
                    out.append({"kind": "unresolved", "start": s, "end": e, "text": m.group(0), "candidate": canon,
                                "why": "near_miss",
                                "note": "one edit away from a known name and not in names.json; confirm or ignore"})
                break
    return out


def neighbours(texts):
    """For each position, the nearest non-empty text before and after it ('' if none)."""
    n = len(texts)
    prev, nxt = [""] * n, [""] * n
    last = ""
    for i in range(n):
        prev[i] = last
        if texts[i].strip():
            last = texts[i]
    last = ""
    for i in range(n - 1, -1, -1):
        nxt[i] = last
        if texts[i].strip():
            last = texts[i]
    return prev, nxt


def context_for(prev: str, text: str, nxt: str):
    ctx = (prev + "\n" if prev else "") + text + ("\n" + nxt if nxt else "")
    return ctx, (len(prev) + 1 if prev else 0)


# --------------------------------------------------------------------------------------------
# sidecars: decisions and verbatim spans
# --------------------------------------------------------------------------------------------

def read_sidecar(path, what: str):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UsageError(f"{path}: cannot read {what} file ({exc})")
    if isinstance(data, dict):
        data = data.get(what)
    if not isinstance(data, list):
        raise UsageError(f"{path}: expected a JSON array of {what}")
    return data


def _unit_of(d: dict):
    for k in ("segment", "line", "unit"):
        if k in d:
            return d[k]
    return None


def _in_range(source: Source, idx) -> bool:
    return (isinstance(idx, int) and not isinstance(idx, bool)
            and source.first_index <= idx < source.first_index + len(source.texts))


def resolve_decisions(source: Source, decisions):
    by_unit, errors = {}, []
    for n, d in enumerate(decisions or []):
        tag = f"decision {n}"
        if not isinstance(d, dict):
            errors.append(f"{tag}: not an object")
            continue
        idx = _unit_of(d)
        if not _in_range(source, idx):
            errors.append(f"{tag}: {source.unit} {idx!r} is out of range")
            continue
        action = d.get("action")
        before = d.get("before")
        if action not in ("apply", "keep", "flag"):
            errors.append(f"{tag}: action must be apply, keep or flag")
            continue
        if not isinstance(before, str) or not before:
            errors.append(f"{tag}: 'before' must be the exact text in the source")
            continue
        if action == "apply" and not (isinstance(d.get("after"), str) and d["after"]):
            errors.append(f"{tag}: apply needs a non-empty 'after'")
            continue
        text = source.texts[idx - source.first_index]
        spans = find_words(text, before)
        if not spans:
            errors.append(f"{tag}: {before!r} not found as a whole word in {source.unit} {idx}")
            continue
        occ = d.get("occurrence")
        if occ is not None:
            if not isinstance(occ, int) or occ < 1 or occ > len(spans):
                errors.append(f"{tag}: occurrence {occ!r} out of range (1 to {len(spans)})")
                continue
            spans = [spans[occ - 1]]
        for s, e in spans:
            by_unit.setdefault(idx, []).append({
                "start": s, "end": e, "action": action, "before": text[s:e], "after": d.get("after"),
                "reason": d.get("reason") or d.get("note")})
    if errors:
        raise UsageError("decisions file: " + "; ".join(errors))
    return by_unit


def resolve_verbatim(source: Source, spans):
    by_unit, errors = {}, []
    for n, d in enumerate(spans or []):
        tag = f"verbatim span {n}"
        if not isinstance(d, dict):
            errors.append(f"{tag}: not an object")
            continue
        idx = _unit_of(d)
        needle = d.get("text")
        if not _in_range(source, idx):
            errors.append(f"{tag}: {source.unit} {idx!r} is out of range")
            continue
        if not isinstance(needle, str) or not needle:
            errors.append(f"{tag}: 'text' must be the exact quoted words")
            continue
        found = find_exact(source.texts[idx - source.first_index], needle)
        if not found:
            errors.append(f"{tag}: text not found exactly in {source.unit} {idx}")
            continue
        occ = d.get("occurrence")
        if occ is not None:
            if not isinstance(occ, int) or occ < 1 or occ > len(found):
                errors.append(f"{tag}: occurrence {occ!r} out of range (1 to {len(found)})")
                continue
            found = [found[occ - 1]]
        for s, e in found:
            by_unit.setdefault(idx, []).append((s, e))
    if errors:
        raise UsageError("verbatim file: " + "; ".join(errors))
    return by_unit


# --------------------------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------------------------

class Result:
    def __init__(self, source: Source, names: Names):
        self.source = source
        self.names = names
        self.corrected = []
        self.corrections = []
        self.unresolved = []
        self.kept = []
        self.protected = []
        self.skipped = []

    def summary(self) -> dict:
        by_basis, by_name, units = {}, {}, set()
        key = self.source.unit
        for c in self.corrections:
            by_basis[c["basis"]] = by_basis.get(c["basis"], 0) + 1
            by_name[c["name"]] = by_name.get(c["name"], 0) + 1
            units.add(c[key])
        by_why = {}
        for u in self.unresolved:
            by_why[u["why"]] = by_why.get(u["why"], 0) + 1
        return {
            "corrections": len(self.corrections),
            "units_changed": len(units),
            "by_basis": dict(sorted(by_basis.items())),
            "by_name": dict(sorted(by_name.items(), key=lambda kv: (-kv[1], kv[0]))),
            "unresolved": len(self.unresolved),
            "unresolved_by_kind": dict(sorted(by_why.items())),
            "kept": len(self.kept),
            "protected": len(self.protected),
            "skipped": len(self.skipped),
        }


def _apply_items(text: str, items) -> str:
    out, pos, delta = [], 0, 0
    for it in sorted(items, key=lambda x: (x["start"], x["end"])):
        s, e = it["start"], it["end"]
        out.append(text[pos:s])
        if it["kind"] == "correction":
            out.append(it["after"])
            it["out_start"] = s + delta
            it["out_end"] = it["out_start"] + len(it["after"])
            delta += len(it["after"]) - (e - s)
        else:
            out.append(text[s:e])
            it["out_start"], it["out_end"] = s + delta, e + delta
        pos = e
    out.append(text[pos:])
    return "".join(out)


def process(source: Source, names: Names, decisions=None, verbatim=None) -> Result:
    res = Result(source, names)
    overrides = resolve_decisions(source, decisions)
    keep_spans = resolve_verbatim(source, verbatim)
    fenced = fenced_lines(source.texts) if source.kind == "text" else set()
    prevs, nexts = neighbours(source.texts)
    key = source.unit
    for pos, text in enumerate(source.texts):
        idx = source.index(pos)
        if pos in fenced or not text:
            if overrides.get(idx) or keep_spans.get(idx):
                raise UsageError(f"{key} {idx} is a fenced code block or empty and cannot take decisions or verbatim spans")
            res.corrected.append(text)
            continue
        silent = code_spans(text)
        protected = sorted(keep_spans.get(idx, []))
        ctx, base = context_for(prevs[pos], text, nexts[pos])
        items, covered = scan_unit(names, text, ctx, base, silent, protected)
        items += near_misses(names, text, covered, silent, protected)
        ovs = overrides.get(idx, [])
        if ovs:
            spans = sorted((o["start"], o["end"]) for o in ovs)
            for (a, b), (c, d) in zip(spans, spans[1:]):
                if c < b:
                    raise UsageError(f"decisions overlap in {key} {idx}")
            for o in ovs:
                if overlaps(protected, o["start"], o["end"]):
                    raise UsageError(f"a decision in {key} {idx} touches a verbatim span")
            items = [it for it in items if not overlaps(spans, it["start"], it["end"])]
            for o in ovs:
                s, e, before = o["start"], o["end"], o["before"]
                if o["action"] == "apply" and o["after"] != before:
                    it = _correction(s, e, before, o["after"], norm_form(before), "decision")
                    if o["reason"]:
                        it["reason"] = o["reason"]
                    items.append(it)
                elif o["action"] in ("apply", "keep"):
                    it = {"kind": "kept", "start": s, "end": e, "text": before}
                    if o["reason"]:
                        it["reason"] = o["reason"]
                    items.append(it)
                else:
                    items.append({"kind": "unresolved", "start": s, "end": e, "text": before, "why": "flag",
                                  "note": o["reason"] or "flagged for the operator"})
        for s, e in protected:
            items.append({"kind": "protected", "start": s, "end": e, "text": text[s:e], "marker": "sidecar"})
        occupied = sorted((it["start"], it["end"]) for it in items)
        for (a, b), (c, d) in zip(occupied, occupied[1:]):
            if c < b:
                raise UsageError(f"internal: overlapping items in {key} {idx}")
        res.corrected.append(_apply_items(text, items))
        for it in sorted(items, key=lambda x: (x["start"], x["end"])):
            entry = {key: idx, "start": it["start"], "end": it["end"]}
            kind = it["kind"]
            if kind == "correction":
                for k in ("before", "after", "name", "variant", "basis", "cue", "reason"):
                    if k in it:
                        entry[k] = it[k]
                entry["out_start"], entry["out_end"] = it["out_start"], it["out_end"]
                res.corrections.append(entry)
            else:
                for k in ("text", "candidate", "why", "note", "reason", "marker"):
                    if k in it:
                        entry[k] = it[k]
                if kind == "unresolved":
                    lo, hi = max(0, it["start"] - 60), min(len(text), it["end"] + 60)
                    entry["context"] = text[lo:hi]
                if kind in ("kept", "protected"):
                    entry["out_start"], entry["out_end"] = it["out_start"], it["out_end"]
                getattr(res, {"unresolved": "unresolved", "kept": "kept", "protected": "protected",
                              "skipped": "skipped"}[kind]).append(entry)
    verify_roundtrip(res)
    return res


def verify_roundtrip(res: Result) -> None:
    """Undo every logged correction in the output and require the source back, byte for byte."""
    src = res.source
    key = src.unit
    by_unit = {}
    for c in res.corrections:
        by_unit.setdefault(c[key], []).append(c)
    for pos, original in enumerate(src.texts):
        idx = src.index(pos)
        text = res.corrected[pos]
        for c in sorted(by_unit.get(idx, []), key=lambda x: x["out_start"], reverse=True):
            if text[c["out_start"]:c["out_end"]] != c["after"]:
                raise AssertionError(f"internal: log offsets do not match output in {key} {idx}")
            text = text[:c["out_start"]] + c["before"] + text[c["out_end"]:]
        if text != original:
            raise AssertionError(f"internal: output differs from the source beyond logged names in {key} {idx}")


# --------------------------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------------------------

def carrier_units(src: Source) -> list:
    """Positions in src.texts that the carrier writes as units. A text source leaves out empty and blank lines, so
    its carrier numbers the written lines [1]..[k] in order (the unit numbering Lorengine's reader requires); the
    source line of each is kept in the carrier head and in corrections.json, so ledger citations stay Ln."""
    if src.kind != "text":
        return list(range(len(src.texts)))
    return [pos for pos, t in enumerate(src.texts) if t.strip()]


def _ranges(nums) -> str:
    out, run = [], []
    for x in nums:
        if run and x == run[-1] + 1:
            run.append(x)
            continue
        if run:
            out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else f"{run[0]}")
        run = [x]
    if run:
        out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else f"{run[0]}")
    return ",".join(out)


def _unranges(spec: str) -> list:
    out = []
    for part in filter(None, spec.split(",")):
        a, _, b = part.partition("-")
        out.extend(range(int(a), int(b or a) + 1))
    return out


UNIT_LINES = "- Unit lines: "


def build_carrier(res: Result) -> str:
    src = res.source
    s = res.summary()
    n = len(src.texts)
    unit = src.unit
    title = f"# Corrected transcript: {src.ref}"
    # Lorengine's reader ends transcript provenance at an editorial heading; the title must never read as one.
    lines = [title, ""] if not _editorial_heading(title) else ["# Corrected transcript", "", f"- Ref: {src.ref}"]
    lines.append(f"- Scope: project and product names and their capitalization only. {s['corrections']} "
                 f"correction(s) in {s['units_changed']} {unit}(s); nothing else was changed.")
    written = carrier_units(src)
    if src.kind == "voxtype":
        lines.append(f"- Units: {n} segments, zero-based. [n] is the segment id used in ledger source references "
                     f"({src.ref}:n).")
    else:
        lines.append(f"- Units: {len(written)} non-empty of {n} source lines, numbered [1] to [{len(written)}] in "
                     f"order; {n - len(written)} empty line(s) are omitted. The next line gives each unit's source line "
                     f"number (Ln), used in ledger references.")
        lines.append(UNIT_LINES + _ranges(src.index(pos) for pos in written))
    lines.append(f"- Flagged, not edited: {s['unresolved']} (see corrections.json).")
    if src.path:
        lines.append(f"- Source: {src.path} (read-only).")
    lines += ["", "---", ""]
    body = []
    for k, pos in enumerate(written):
        mark = src.marker(src.index(pos)) if src.kind == "voxtype" else f"[{k + 1}]"
        body.append(f"{mark} {res.corrected[pos]}")
    return "\n".join(lines) + "\n" + "\n\n".join(body) + "\n"


def parse_carrier(md: str):
    """(kind, [(source index, text)]): segment ids for a voxtype note, source line numbers for a text note, whether
    the carrier numbers its lines [n] with a unit-lines head or (written before 29 Oct 2026) [Ln]."""
    head, sep, body = md.partition("\n---\n\n")
    if not sep:
        raise UsageError("not a corrected_transcript.md written by normalize.py (separator line missing)")
    if body.endswith("\n"):
        body = body[:-1]
    marks = list(re.finditer(r"(?m)^\[(L?)(\d+)\] ", body))
    if body and (not marks or marks[0].start() != 0):
        raise UsageError("corrected_transcript.md: body does not start with a unit marker")
    units = []
    for k, m in enumerate(marks):
        end = marks[k + 1].start() - 2 if k + 1 < len(marks) else len(body)
        units.append((int(m.group(2)), body[m.end():end]))
    mapped = re.search(r"(?m)^" + re.escape(UNIT_LINES) + r"([0-9,-]*)$", head)
    if mapped:
        lines = _unranges(mapped.group(1))
        if len(lines) != len(units) or any(idx != k + 1 for k, (idx, _) in enumerate(units)):
            raise UsageError("corrected_transcript.md: unit lines do not match the numbered units")
        return "text", [(line, text) for line, (_, text) in zip(lines, units)]
    kind = "text" if marks and marks[0].group(1) == "L" else "voxtype"
    return kind, units


def _editorial_heading(text: str) -> bool:
    return text.startswith("#") and any(w in text.lower() for w in ("ledger", "editorial", "actionable", "appendix"))


def receipt_check(carrier_text: str, obj: dict) -> dict:
    """Lorengine's reader rule for a corrected transcript (src/source_readers.rs correction/corrected_units at
    cbb8b542), applied by the filing step to the bytes it writes: {"admitted": bool, "reason": code or None,
    "units": indexed count}. The reason codes are the reader's own omission codes. The native segment count of a
    voxtype source is checked against the kept source when it is readable."""
    def out(reason, n=0):
        return {"rule": "lorengine source_readers correction@cbb8b542", "admitted": reason is None, "reason": reason,
                "units": n}
    src = obj.get("source") or {}
    path = src.get("path")
    if not isinstance(path, str) or not path.startswith("/") or not src.get("ref"):
        return out("missing_correction_provenance")
    expected = (obj.get("outputs") or {}).get(CARRIER) or ""
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        return out("missing_correction_receipt")
    if sha256_bytes(carrier_text.encode("utf-8")) != expected:
        return out("correction_hash_mismatch")
    seen, idx, cur, derived = set(), [], None, False
    # str.lines() in the reader: "\n" ends a line, a "\r" before it is dropped; nothing else splits.
    for line in (l[:-1] if l.endswith("\r") else l for l in carrier_text.removesuffix("\n").split("\n")):
        m = re.match(r"\[(\d+)\]", line)
        if m:
            n = int(m.group(1))
            if n in seen:
                return out("duplicate_corrected_unit")
            seen.add(n)
            if cur is not None:
                idx.append(cur)
            body = line[m.end():].lstrip()
            derived |= _editorial_heading(body)
            cur = [n, body]
        elif _editorial_heading(line):
            if cur is not None:
                idx.append(cur)
            cur, derived = None, True
        elif cur is not None:
            cur[1] += "\n" + line
    if cur is not None:
        idx.append(cur)
    if any(not body.strip() for _, body in idx):
        return out("empty_corrected_unit", len(idx))
    units = src.get("units")
    if not isinstance(units, int) or isinstance(units, bool) or units < 0:
        return out("missing_correction_units", len(idx))
    first = src.get("first_index") or 0
    nums = sorted(n for n, _ in idx)
    if len(nums) != units or not nums or nums != list(range(first, first + len(nums))):
        return out("correction_unit_count_mismatch", len(nums))
    if src.get("kind") == "voxtype" and path.startswith(str(VOXTYPE_ROOT)):
        try:
            segments = json.loads(Path(path).read_text(encoding="utf-8")).get("segments")
        except (OSError, ValueError, AttributeError):
            segments = 0
        if segments is None:
            return out("missing_native_segments_for_correction", len(nums))
        if isinstance(segments, list) and (first != 0 or len(segments) != units):
            return out("correction_native_unit_count_mismatch", len(nums))
    return out(None, len(nums))


def corrections_json(res: Result, carrier_text: str) -> dict:
    src = res.source
    obj = {
        "schema": SCHEMA,
        "source": {
            "kind": src.kind, "ref": src.ref, "path": src.path, "unit": src.unit, "units": len(src.texts),
            "first_index": src.first_index, "sha256": src.sha256, "metadata": src.meta,
        },
        "names": {"path": res.names.path, "sha256": res.names.digest, "entries": len(res.names.entries)},
        "outputs": {CARRIER: sha256_bytes(carrier_text.encode("utf-8"))},
        "summary": res.summary(),
        "unit_lengths": [len(t) for t in res.corrected],
        "corrections": res.corrections,
        "unresolved": res.unresolved,
        "kept": res.kept,
        "protected": res.protected,
        "skipped": res.skipped,
    }
    if src.kind == "text":
        # The carrier's units are the non-empty lines, numbered from 1; "lines" is the source line count that ledger
        # citations (Ln) are checked against, and "unit_lines" the source line of each unit.
        written = carrier_units(src)
        obj["source"].update(units=len(written), first_index=1, lines=len(src.texts),
                             unit_lines=[src.index(pos) for pos in written])
    obj["receipt_check"] = receipt_check(carrier_text, obj)
    return obj


def guard_out(out: Path, src: Source) -> None:
    target = out.expanduser().resolve()
    banned = [VOXTYPE_ROOT.resolve()]
    if src.kind == "voxtype" and src.path:
        banned.append(Path(src.path).resolve().parent)
    for b in banned:
        if target == b or b in target.parents:
            raise UsageError(f"refusing to write into {b} (VoxType storage and note folders are read-only evidence)")


def write_outputs(res: Result, out: Path) -> list:
    guard_out(out, res.source)
    out = out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    carrier = build_carrier(res)
    (out / CARRIER).write_text(carrier, encoding="utf-8")
    obj = corrections_json(res, carrier)
    (out / CORRECTIONS).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [out / CARRIER, out / CORRECTIONS]


def default_out(src: Source) -> Path:
    return RUNS_ROOT / slug(src.label)


def print_summary(res: Result, written=None, stream=None) -> None:
    stream = stream or sys.stdout
    src, s = res.source, res.summary()
    p = lambda *a: print(*a, file=stream)
    p(f"normalize: {src.ref} ({len(src.texts)} {src.unit}s, {len(res.names.entries)} names)")
    basis = ", ".join(f"{k} {v}" for k, v in s["by_basis"].items()) or "none"
    p(f"  corrections: {s['corrections']} in {s['units_changed']} {src.unit}(s)  [{basis}]")
    if s["by_name"]:
        p("  by name: " + ", ".join(f"{k} {v}" for k, v in s["by_name"].items()))
    kinds = ", ".join(f"{k} {v}" for k, v in s["unresolved_by_kind"].items()) or "none"
    p(f"  flagged, not edited: {s['unresolved']}  [{kinds}]")
    for u in res.unresolved[:40]:
        cand = f" (candidate {u['candidate']})" if u.get("candidate") else ""
        p(f"    {src.unit} {u[src.unit]}: {u['text']!r}{cand} - {u['why']}")
    if len(res.unresolved) > 40:
        p(f"    ... {len(res.unresolved) - 40} more in corrections.json")
    p(f"  kept by decision: {s['kept']}   verbatim spans: {s['protected']}   url/path tokens skipped: {s['skipped']}")
    if src.meta.get("status") not in (None, "completed"):
        p(f"  warning: metadata status is {src.meta.get('status')!r}, not 'completed'")
    for w in written or []:
        p(f"  wrote {w}")


# --------------------------------------------------------------------------------------------
# --check
# --------------------------------------------------------------------------------------------

def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def check_text(names: Names, text: str, accounted=None, ambiguous_counts=True):
    """Survivors in free text: (offset, found, expected, kind). Used for non-transcript files."""
    silent = code_spans(text)
    items, _ = scan_unit(names, text, text, 0, silent, accounted or [])
    out = []
    for it in items:
        if it["kind"] == "correction":
            out.append((it["start"], it["before"], it["after"], it["basis"]))
        elif it["kind"] == "unresolved" and it["why"] == "ambiguous" and ambiguous_counts:
            out.append((it["start"], it["text"], it["candidate"], "ambiguous"))
    return out


def check_transcript(names: Names, md_path: Path, corr_path: Path):
    md = md_path.read_text(encoding="utf-8")
    kind, units = parse_carrier(md)
    accounted = {}
    if corr_path and corr_path.is_file():
        try:
            corr = json.loads(corr_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise UsageError(f"{corr_path}: {exc}")
        key = "segment" if kind == "voxtype" else "line"
        for group in ("kept", "protected"):
            for e in corr.get(group, []):
                accounted.setdefault(e[key], []).append((e["out_start"], e["out_end"]))
    texts = [t for _, t in units]
    prevs, nexts = neighbours(texts)
    fenced = fenced_lines(texts) if kind == "text" else set()
    found = []
    for pos, (idx, text) in enumerate(units):
        if pos in fenced:
            continue
        ctx, base = context_for(prevs[pos], text, nexts[pos])
        items, _ = scan_unit(names, text, ctx, base, code_spans(text), sorted(accounted.get(idx, [])))
        for it in items:
            if it["kind"] == "correction":
                found.append((idx, it["start"], it["before"], it["after"], it["basis"]))
            elif it["kind"] == "unresolved" and it["why"] == "ambiguous":
                found.append((idx, it["start"], it["text"], it["candidate"], "ambiguous"))
    return kind, found


def run_check(paths, names: Names, out=None) -> int:
    out = out or sys.stdout
    targets = []
    for raw in paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            for name in (CARRIER, "ledger.md", "ledger.json"):
                if (p / name).is_file():
                    targets.append(p / name)
        elif p.is_file():
            targets.append(p)
        else:
            raise UsageError(f"{raw}: not found")
    if not targets:
        raise UsageError("nothing to check: no corrected_transcript.md, ledger.md or ledger.json found")
    bad = 0
    for t in targets:
        if t.name == CARRIER:
            kind, found = check_transcript(names, t, t.parent / CORRECTIONS)
            mark = "L" if kind == "text" else "segment "
            for idx, off, text, expect, why in found:
                print(f"FAIL {t}: {mark}{idx}: {text!r} should be {expect!r} ({why})", file=out)
            bad += len(found)
            if not found:
                print(f"ok   {t}: no known variant survives", file=out)
        else:
            text = t.read_text(encoding="utf-8")
            found = check_text(names, text, ambiguous_counts=False)
            for off, text_found, expect, why in found:
                print(f"FAIL {t}:{_line_of(text, off)}: {text_found!r} should be {expect!r} ({why})", file=out)
            bad += len(found)
            if not found:
                print(f"ok   {t}: no known variant survives", file=out)
    print(f"check: {'FAIL' if bad else 'OK'} ({bad} surviving variant(s) in {len(targets)} file(s))", file=out)
    return 1 if bad else 0


# --------------------------------------------------------------------------------------------
# --locate and CLI
# --------------------------------------------------------------------------------------------

def locate(res: Result, phrase: str, limit=25):
    """Source ids where PHRASE occurs in the corrected text (offsets are into the corrected segment)."""
    src, hits, needle = res.source, [], phrase.lower()
    for pos, text in enumerate(res.corrected):
        low, start = text.lower(), 0
        while True:
            i = low.find(needle, start)
            if i < 0:
                break
            idx = src.index(pos)
            lo, hi = max(0, i - 50), min(len(text), i + len(phrase) + 50)
            hits.append((src.cite(idx, i if src.kind == "voxtype" else None), text[lo:hi]))
            start = i + max(1, len(needle))
            if len(hits) >= limit:
                return hits
    return hits


def build_parser():
    ap = argparse.ArgumentParser(
        prog="normalize.py", description="Names-only cleanup of a voice-note transcript.",
        epilog="Exit codes: 0 ok, 1 --check found surviving variants (or names.json lint failed), 2 bad input.")
    ap.add_argument("source", nargs="?", help='VoxType note folder or transcript.json, a text file, or "-" for stdin')
    ap.add_argument("--out", help="output directory (default ./voice-output/<note folder>/)")
    ap.add_argument("--names", help="names.json to use (default: the one beside this skill)")
    ap.add_argument("--decisions", help="JSON array of apply/keep/flag decisions for ambiguous words")
    ap.add_argument("--verbatim", help="JSON array of exact quoted spans that must stay untouched")
    ap.add_argument("--name", help="label for text input (used for the default output folder)")
    ap.add_argument("--dry-run", action="store_true", help="print the summary without writing anything")
    ap.add_argument("--check", nargs="+", metavar="PATH",
                    help="grep deliverables (a directory or files) for surviving variants; exit 1 if any")
    ap.add_argument("--lint-names", action="store_true", help="validate names.json and exit")
    ap.add_argument("--locate", metavar="PHRASE", help="print source ids where PHRASE occurs in the corrected text")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        if args.lint_names:
            p = Path(args.names) if args.names else NAMES_PATH
            data = json.loads(p.read_text(encoding="utf-8"))
            problems = lint_names(data)
            if problems:
                print("\n".join(problems), file=sys.stderr)
                return 1
            names = Names(data, p)
            autos = sum(1 for _, t in names.alts.values() if t == "auto")
            gated = sum(1 for _, t in names.alts.values() if t == "gated")
            print(f"names.json OK: {len(data)} entries, {autos} automatic variants, {gated} gated words")
            return 0
        names = load_names(args.names)
        if args.check:
            return run_check(args.check, names)
        if not args.source:
            ap.error("a SOURCE is required (or use --check / --lint-names)")
        src = load_source(args.source, args.name)
        decisions = read_sidecar(args.decisions, "decisions") if args.decisions else None
        verbatim = read_sidecar(args.verbatim, "verbatim") if args.verbatim else None
        res = process(src, names, decisions, verbatim)
        if args.locate:
            for ident, ctx in locate(res, args.locate):
                print(f"{ident}  ...{ctx}...")
            return 0
        if args.dry_run:
            print_summary(res)
            return 0
        out = Path(args.out) if args.out else default_out(src)
        written = write_outputs(res, out)
        print_summary(res, written)
        return 0
    except UsageError as exc:
        print(f"normalize.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
