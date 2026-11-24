#!/usr/bin/env python3
"""Flag a pack that postpones the real product, before it runs (OC-05 result line 3).

usage: postpone_check.py CAMPAIGN_ROOT [WAVE_DIR ...]   (default: every wave*/ directory under the root)

Rule source: OUTCOME_CONTRACT_STANDARD.md R4 (line 48): "A pack that postpones the outcome itself (a "step zero",
a decision packet, a mock) says so on its first line and is flagged to the operator before it runs; it is never
reported as delivering the outcome." Every finding is BLOCKING; exit 1 if any, else 0. Deterministic; no model.

  P1 (R4 first line)  DEPLOYMENT_ORDER.md line 1, a directive's title or Posture names a step zero, a decision
                      packet, a mock, a precursor, "foundation first" or "later we build".
  Not a postponement (P2, 30 Oct live-pack run): "pay stub", a payslip document, not a code stub.
  Not a postponement (all of P1/P2, chief's ruling 15:15): a term in an inline-code span, a quoted term, a term after a
  citation of R4, a forbidden term, or a term in a sentence that describes a check (rule, check, flag, marker,
  match, detect, fixture, positive/negative, exempt, lint, pattern, names, warning), e.g. "a stub rule", "flags placeholder".
  Headings: the 4 Oct form (## Orientation, ## Work items, ## Acceptance checklist) and today's nine-section form
  (## 1. Orientation, ## 5. Work, ## 7. Acceptance, numbered or plain) are both read (30 Oct).
  P2 (R4 deferral)    the Posture or a Work item defers the product: stub, dummy data, mock-up, placeholder,
                      scaffold only, "build later", "groundwork", "before we build". A line that forbids the thing
                      (never/no/not/without before the word), a quoted term or one after a citation of R4 is not a match.
  P3 (R4 mock)        the cited result line asks for a running tool (invoke, open, use, run, launch, install,
                      be told ... before it runs) and the Acceptance checklist names nothing run (raw, run, exit,
                      rc, installed, invoke, opens, launched).
  P4 (R4 step zero)   the Posture is preparation only (plan, prepare, draft, brief, research, design, propose,
                      decision packet, with no apply/build/install/write/fix/extend/verify) and the cited result line
                      is not itself a paper result (read, find, see, be told, know, proposed, diffs, ledger, on paper).
                      This is the allowance for a plan-only task the charter asks for; its false-positive risk: a
                      charter that wants a plan but words the line as a tool ("Invoke ...") is flagged and needs the
                      dispatcher to say so on the directive's first line and get the operator's yes (R4).
"""
import glob, json, os, re, sys

STEP0 = r"step[ -]zero|decision packet|\bmock(?:-?up)?s?\b|precursor|foundations? first|later we build|build (?:it )?later"
DEFER = (r"(?<!pay )\bstubs?\b|dummy data|\bmock(?:-?up)?s?\b|placeholders?|scaffold(?:ing)? only|build (?:it |the \w+ )?later|"
         r"later we build|groundwork|before we build|foundations? first|step[ -]zero|decision packet")
NEG = re.compile(r"\b(never|no|not|without|nor|don't|do not)\b", re.I)
DESCRIBES = re.compile(r"\b(rules?|checks?|checker|flags?|flagged|markers?|match(?:es|ed)?|detects?|detected|fixtures?|"
                      r"positives?|negatives?|exempt|lint|patterns?|names|warn(?:s|ing)?|R4)\b", re.I)
TOOL_LINE = re.compile(r"\b(invoke|open|use|run|runs|launch|install(?:ed)?|start)\b", re.I)
RAN = re.compile(r"\b(raw|run|ran|exit|rc|installed|invoke[sd]?|opens?|launched|executes?)\b", re.I)
PLAN = re.compile(r"\b(plan|prepare|draft|brief|research|design|propose|decision packet|outline)\b", re.I)
DOES = re.compile(r"\b(apply|build|install|write|fix|extend|verify|implement|run)\b", re.I)
PAPER = re.compile(r"\b(read|find|see|be told|know|proposed|diffs?|ledger|on paper)\b", re.I)


NUM = r"(?:\d+\.\s*)?"  # today's nine-section headings are numbered ("## 5. Work"); the 4 Oct form is not


def section(text, *names):
    """The body under the first heading that matches one of names, numbered or not (30 Oct: today's form)."""
    for name in names:
        m = re.search(r"^## " + NUM + name + r"\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if m:
            return m.group(1)
    return ""


def sentence_at(ln, pos):
    """The sentence or clause (split on . ; and a list colon) holding position pos."""
    a = max(ln.rfind(c, 0, pos) for c in (". ", "; ")) + 1
    ends = [e for e in (ln.find(". ", pos), ln.find("; ", pos)) if e >= 0]
    return ln[a:min(ends) if ends else len(ln)]


def hits(pattern, text, base_line, skip_negated):
    out = []
    for i, ln in enumerate(text.splitlines()):
        if skip_negated:
            ln = re.sub(r"`[^`]*`", lambda c: " " * len(c.group(0)), ln)  # inline code names, it does not defer
        for m in re.finditer(pattern, ln, re.I):
            if skip_negated and DESCRIBES.search(sentence_at(ln, m.start())):
                continue  # a sentence describing a check names the term (T1014's title and work items)
            if skip_negated and NEG.search(ln[:m.start()]):
                continue
            if skip_negated and (ln[:m.start()].count('"') % 2 or "R4" in ln[:m.start()]):
                continue  # a quoted term or a citation of R4 names the rule, it does not defer (T1013's own line 22)
            out.append((base_line + i, m.group(0), ln.strip()))
    return out


def line_of(text, fragment):
    return text[:text.find(fragment)].count("\n") + 1 if fragment and fragment in text else 1


def result_lines(root):
    """{(OC-nn, n): text} from OUTCOME.md's result tables, each under its '## OC-nn' heading."""
    lines, oc = {}, None
    p = os.path.join(root, "OUTCOME.md")
    if not os.path.isfile(p):
        return None
    for ln in open(p, encoding="utf-8"):
        h = re.match(r"^## (OC-\d\d)", ln)
        if h:
            oc = h.group(1)
        r = re.match(r"^\|\s*([0-9]+[a-z]?)\s*\|\s*(.+?)\s*\|", ln)
        if oc and r:
            lines[(oc, r.group(1))] = r.group(2)
    return lines


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = os.path.abspath(sys.argv[1])
    waves = [os.path.abspath(w) for w in sys.argv[2:]] or sorted(glob.glob(os.path.join(root, "wave*")))
    results = result_lines(root)
    findings = []
    if results is None:
        findings.append({"rule": "P0", "file": root, "line": 0, "match": "", "message": "OUTCOME.md missing; cannot judge"})
        results = {}
    dep = os.path.join(root, "DEPLOYMENT_ORDER.md")
    if os.path.isfile(dep):
        first = next((l for l in open(dep, encoding="utf-8") if l.strip()), "")
        for _, m, txt in hits(STEP0, first, 1, False):
            findings.append({"rule": "P1", "file": dep, "line": 1, "match": m, "message": f"pack's first line names a postponing pack: {txt}"})
    for w in waves:
        for d in sorted(glob.glob(os.path.join(w, "*.md"))):
            if not re.match(r"[A-Z]\d+", os.path.basename(d)):
                continue
            t = open(d, encoding="utf-8").read()
            if not re.search(r"^## " + NUM + r"(Orientation|Acceptance)\b", t, re.M):
                continue
            title = t.splitlines()[0] if t else ""
            pm = re.search(r"^Posture:.*$", t, re.M)
            posture = pm.group(0) if pm else ""
            # P1: title or posture declares the pack a precursor
            for ln_text, ln_no in ((title, 1), (posture, line_of(t, posture))):
                for _, m, txt in hits(STEP0, ln_text, ln_no, True):
                    findings.append({"rule": "P1", "file": d, "line": ln_no, "match": m, "message": txt})
            # P2: work items defer the product
            work = section(t, "Work items", "Work")
            wl = line_of(t, work)
            seen = {(f["line"], f["match"].lower()) for f in findings if f["file"] == d}
            for n, m, txt in hits(DEFER, posture, line_of(t, posture), True) + hits(DEFER, work, wl, True):
                if (n, m.lower()) not in seen:
                    seen.add((n, m.lower()))
                    findings.append({"rule": "P2", "file": d, "line": n, "match": m, "message": txt})
            om = re.search(r"^Outcome: (OC-\d\d), result lines? ([0-9]+[a-z]?)", t, re.M)
            if not om:
                continue  # no result line at all is outcome_check O2's finding, not this check's
            rtext = results.get((om.group(1), om.group(2)), "")
            acc = section(t, "Acceptance checklist", "Acceptance")
            # P3: the line asks for a running tool, the acceptance runs nothing
            if rtext and TOOL_LINE.search(rtext) and not RAN.search(acc):
                findings.append({"rule": "P3", "file": d, "line": line_of(t, acc), "match": TOOL_LINE.search(rtext).group(0),
                                 "message": f"result line {om.group(1)}/{om.group(2)} asks for a running tool; acceptance names nothing run"})
            # P4: preparation-only posture against a line that is not a paper result
            body = re.sub(r"^Posture:\s*", "", posture).split(".")[0]
            if PLAN.search(body) and not DOES.search(body) and rtext and not PAPER.search(rtext):
                findings.append({"rule": "P4", "file": d, "line": line_of(t, posture), "match": PLAN.search(body).group(0),
                                 "message": f"preparation-only posture; result line {om.group(1)}/{om.group(2)} is not a paper result: {rtext[:80]}"})
    for f in findings:
        print(f"BLOCKING {f['rule']} {f['file']}:{f['line']} [{f['match']}] {f['message']}")
    print(json.dumps({"blocking": len(findings), "waves": len(waves)}))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
