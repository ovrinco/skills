#!/usr/bin/env python3
"""accept_check.py CAMPAIGN_ROOT TASK_REPORT [CANDIDATE_DIR]

Acceptance checks for a task before it is called done (OC-05 line 4, proof 2).
  A1 stub rule (narrowed, chief's ruling 15:15): only stub markers in delivered code paths, never a bare word in a
     name, an enum, docs or prose. In code files: the unimplemented, todo and not-implemented panic macros,
     raising NotImplementedError, TODO/FIXME/XXX in a comment, and a fixed placeholder literal (a string literal that
     is itself placeholder, dummy, lorem ipsum or TBD text, as a function's return or a shown value). Any file
     named mock_* outside test paths. Exempt: tests/, test/, fixtures/, __tests__/, *_test.*, *.test.*, *.spec.*,
     and rule text (a line that defines a pattern, or carries "accept-check: rule-text").
  A2 walk rule: any walk record whose Walker is its Builder is refused (30 Oct; read on one line, two lines or a
     table row); when the report's cited result line
     needs a running tool, the report carries a walk record:
       ## Walk record
       Walker: <session id>      Builder: <session id>   (must differ)
       Installed: <installed path or build hash>
       Steps: <one or more step lines or table rows>
       Evidence: <path that exists>
Exit 1 on any BLOCKING finding, printed as RULE file:line message. Exit 2 on usage error.
"""
import os, re, sys

CODE_EXT = {".rs", ".py", ".qml", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".svelte", ".vue", ".go", ".c", ".h", ".cc",
            ".cpp", ".hpp", ".zig", ".java", ".kt", ".swift", ".rb", ".lua", ".sh", ".bash", ".zsh", ".fish", ".nix"}
COMMENT = r"(?://|#|/\*|--|;)"  # accept-check: rule-text
LITERAL = r"[\"'](?:placeholder|dummy|lorem ipsum|tbd|todo|fixme|mock)\b[^\"']*[\"']"  # accept-check: rule-text
STUB = [  # accept-check: rule-text
    (re.compile(r"\bunimplemented!\s*\("), "unimplemented!()"),
    (re.compile(r"\btodo!\s*\("), "todo!()"),
    (re.compile(r"panic!\s*\(\s*\"[^\"]*not (yet )?implemented", re.I), "panic! not implemented"),
    (re.compile(r"\braise\s+NotImplementedError\b"), "raise NotImplementedError"),
    (re.compile(COMMENT + r".*\b(TODO|FIXME|XXX)\b"), "developer note in a comment"),
    (re.compile(LITERAL, re.I), "fixed placeholder literal"),
]
MOCK_FILE = re.compile(r"^mock_", re.I)
EXEMPT_DIR = re.compile(r"(^|/)(tests?|fixtures|__tests__|__fixtures__|testdata)(/|$)")
EXEMPT_FILE = re.compile(r"(_test\.[A-Za-z0-9]+|\.(test|spec)\.[A-Za-z0-9]+|^test_[^/]*\.py)$")
RULE_TEXT = re.compile(r"accept-check: rule-text|re\.compile\(|Regex::new\(|new RegExp\(")
SKIP_DIRS = {".git", "node_modules", "target", "dist", "__pycache__", ".venv"}

TOOL_LINE = re.compile(r"running tool|installed build|on the installed|launch|start the tool|open(s|ed)? the (tool|app|window)", re.I)


def stub_rule(cand):
    out = []
    for dirpath, dirs, files in os.walk(cand):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, cand)
            if EXEMPT_DIR.search(rel) or EXEMPT_FILE.search(fn):
                continue
            if MOCK_FILE.search(fn):
                out.append(("A1", p, 1, "file named mock_* outside test paths"))
            if os.path.splitext(fn)[1].lower() not in CODE_EXT:
                continue  # docs, manifests and data: product words there are not stubs
            try:
                with open(p, "rb") as f:
                    raw = f.read()
            except OSError:
                continue
            if b"\0" in raw[:4096]:
                continue  # binary
            for i, line in enumerate(raw.decode("utf-8", "replace").split("\n"), 1):
                if RULE_TEXT.search(line):
                    continue
                for rx, what in STUB:
                    if rx.search(line):
                        out.append(("A1", p, i, f"{what} in a delivered code path"))
                        break
    return out


def cited_line(root, text):
    m = re.search(r"Outcome:?\s*(OC-\d+),\s*result line\s*(\d+)\s*:?\s*(.*)", text)
    if not m:
        return None, None
    oc, n, quoted = m.group(1), m.group(2), m.group(3).strip()
    p = os.path.join(root, "OUTCOME.md")
    if os.path.isfile(p):
        sect = None
        for line in open(p, encoding="utf-8", errors="replace"):
            h = re.match(r"^##\s+(OC-\d+)", line)
            if h:
                sect = h.group(1)
            r = re.match(r"^\|\s*" + n + r"\s*\|\s*([^|]+)\|", line)
            if r and (sect == oc or sect is None):
                return f"{oc} line {n}", r.group(1).strip()
    return f"{oc} line {n}", quoted


def self_walk(report, lines, start):
    """A walk record that exists is refused when its walker is its builder (30 Oct: a result line worded without the
    tool words, e.g. 'Ask the installed terminal interface ...', skipped the whole walk rule)."""
    if start is None:
        return []
    found = {}
    for j, l in enumerate(lines[start + 1:]):
        if re.match(r"^#+\s", l):
            break
        for name in ("Walker", "Builder"):
            m = re.search(r"\b" + name + r":\s*`?([^`|\s]+)", l)
            if m and name not in found:
                found[name] = (m.group(1), start + 2 + j)
    if "Walker" in found and "Builder" in found and found["Walker"][0] == found["Builder"][0]:
        return [("A2", report, found["Walker"][1], f"walker '{found['Walker'][0]}' is the builder")]
    return []


def walk_rule(root, report):
    text = open(report, encoding="utf-8", errors="replace").read()
    lines = text.split("\n")
    label, result = cited_line(root, text)
    start = next((i for i, l in enumerate(lines) if re.match(r"^#+\s*Walk record", l, re.I)), None)
    if not result or not TOOL_LINE.search(result):
        return self_walk(report, lines, start)  # a walk by its builder never passes, whatever the line's wording
    def bad(msg, ln=1):
        return [("A2", report, ln, f"{label} needs a running tool: {msg}")]
    if start is None:
        return bad("no '## Walk record' section")
    body = []
    for l in lines[start + 1:]:
        if re.match(r"^#+\s", l):
            break
        body.append(l)
    def field(name):  # a value ends at a table bar, the line's end or the next field on the same line
        for j, l in enumerate(body):
            m = re.search(r"\b" + name + r":\s*`?([^`|]+?)`?\s*(\||$|\s(?=(?:Walker|Builder|Installed|Steps|Evidence):))", l)
            if m:
                return m.group(1).strip(), start + 2 + j
        return None, start + 1
    out = []
    walker, wl = field("Walker")
    builder, bl = field("Builder")
    inst, il = field("Installed")
    ev, el = field("Evidence")
    steps = [l for l in body if re.match(r"^\s*(\d+\.|\|\s*\d+\s*\||-\s+step)", l, re.I)]
    if not walker:
        out += bad("walk record has no Walker id", wl)
    if not builder:
        out += bad("walk record has no Builder id", bl)
    if walker and builder and walker == builder:
        out += bad(f"walker '{walker}' is the builder", wl)
    if not inst or not (os.path.isabs(inst) or re.fullmatch(r"[0-9a-f]{7,64}", inst)):
        out += bad("walk record names no installed path or build hash", il)
    if not steps:
        out += bad("walk record lists no steps run", start + 1)
    if not ev:
        out += bad("walk record has no Evidence path", el)
    else:
        cands = [ev] if os.path.isabs(ev) else [os.path.join(os.path.dirname(report), ev), os.path.join(root, ev)]
        if not any(os.path.exists(c) for c in cands):
            out += bad(f"evidence path '{ev}' does not exist", el)
    return out


def main(argv):
    if len(argv) not in (3, 4):
        print(__doc__.strip().split("\n")[0], file=sys.stderr)
        return 2
    root, report = argv[1], argv[2]
    if not os.path.isfile(report):
        print(f"report not found: {report}", file=sys.stderr)
        return 2
    findings = walk_rule(root, report)
    if len(argv) == 4:
        findings += stub_rule(argv[3])
    for rule, p, ln, msg in findings:
        print(f"BLOCKING {rule} {p}:{ln} {msg}")
    print(f"accept_check: {len(findings)} blocking")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
