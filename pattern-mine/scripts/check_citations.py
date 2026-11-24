#!/usr/bin/env python3
"""Re-open every file:line and file:line-line citation in a pattern-mine report and say which do not match.

For each report line: each citation's file must resolve under the root (joined as written, else the one file under
the root whose path ends with the cited path; node_modules and dot folders are not searched for that), the cited
lines must lie within the file, and every token the line quotes in backticks must stand in the lines the line cites
(whitespace ignored). A bare `:N` or `:N-M` after a citation on the same line belongs to that citation's file.

Usage: check_citations.py <report> [--root <dir>]   (root defaults to the report's folder)
Exit: 0 every citation matches, 1 any mismatch (each printed), 2 usage error. Standard library only.
"""
import argparse, os, re, sys

CITE = re.compile(r"(?<![\w/.-])(?P<path>[\w@+./-]*[\w-]\.[A-Za-z][\w]{0,9}"
                  r"|(?:[\w@+.-]+/)*(?:LICENSE|LICENCE|NOTICE|COPYING|README|Makefile|Dockerfile)[\w-]*):(?P<a>\d+)(?:\s*[-–]\s*(?P<b>\d+))?(?![\w%])")
BARE = re.compile(r"(?:(?<=`)|(?<=[\s,(])):(?P<a>\d+)(?:\s*[-–]\s*(?P<b>\d+))?(?![\w%:])")
SPAN = re.compile(r"`([^`\n]+)`")
PATHLIKE = re.compile(r"^[\w@+./-]+\.[A-Za-z][\w]{0,5}$")
SKIP_DIRS = {"node_modules", "__pycache__"}


def squash(s):
    return re.sub(r"\s+", "", s.replace("\\|", "|"))


class Tree:
    def __init__(self, root):
        self.root, self.files, self.cache = root, None, {}

    def resolve(self, cited):
        """Return (path, None) or (None, reason)."""
        p = os.path.realpath(os.path.join(self.root, cited))
        root = os.path.realpath(self.root)
        if os.path.commonpath([root, p]) != root:
            return None, "citation escapes the supplied root"
        if os.path.isfile(p):
            return p, None
        if self.files is None:
            self.files = []
            for d, dirs, names in os.walk(self.root):
                dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith("."))
                self.files += [os.path.join(d, n) for n in names]
        tail = "/" + cited.lstrip("./")
        hits = [f for f in self.files if f.endswith(tail) and os.path.commonpath([root, os.path.realpath(f)]) == root]
        if len(hits) == 1:
            return hits[0], None
        if not hits:
            return None, "file not found under " + self.root
        return None, f"ambiguous: {len(hits)} files end with {cited}; cite a longer path"

    def lines(self, path):
        if path not in self.cache:
            with open(path, encoding="utf-8", errors="replace") as fh:
                self.cache[path] = fh.read().splitlines()
        return self.cache[path]


def tokens(line):
    out = []
    for t in SPAN.findall(line):
        t = t.strip()
        if len(t) < 2 or "…" in t or "..." in t or CITE.search(t) or re.match(r"^:\d", t):
            continue
        if PATHLIKE.match(t) or re.match(r"^(https?://|[0-9a-f]{7,40}$)", t):
            continue
        out.append(t)
    return out


def check(report, tree):
    bad, n = [], 0
    with open(report, encoding="utf-8", errors="replace") as fh:
        text = fh.read().splitlines()
    for no, line in enumerate(text, 1):
        found = []
        for m in CITE.finditer(line):
            found.append((m.start(), m.group("path"), m.group("a"), m.group("b"), m.group(0)))
        if not found:
            continue
        first = min(f[0] for f in found)
        for m in BARE.finditer(line):
            if m.start() < first:
                continue
            prev = max((f for f in found if f[0] < m.start() and f[1]), key=lambda f: f[0])
            found.append((m.start(), prev[1], m.group("a"), m.group("b"), m.group(0).strip()))
        found.sort()
        cited_text, label = [], []
        for _, cpath, a, b, raw in found:
            n += 1
            cite = raw if raw.startswith(cpath) else f"{cpath}{raw}"
            label.append(cite)
            a, b = int(a), int(b or a)
            path, why = tree.resolve(cpath)
            if why:
                bad.append((no, cite, why)); continue
            size = len(tree.lines(path))
            if a < 1 or b < a:
                bad.append((no, cite, f"range {a}-{b} is not a range of lines")); continue
            if b > size:
                bad.append((no, cite, f"line {b} is past the end ({cpath} has {size} lines)")); continue
            cited_text.append("\n".join(tree.lines(path)[a - 1:b]))
        if not cited_text:
            continue
        hay = squash("\n".join(cited_text))
        for t in tokens(line):
            if squash(t) not in hay:
                bad.append((no, ", ".join(label), f"quoted `{t}` is not in the cited lines: quote them exactly or cite the lines that hold it"))
    return bad, n


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report")
    ap.add_argument("--root", help="folder the cited paths are resolved against (default: the report's folder)")
    a = ap.parse_args()
    if not os.path.isfile(a.report):
        ap.error(f"no such report: {a.report}")
    root = os.path.abspath(a.root or os.path.dirname(os.path.abspath(a.report)))
    if not os.path.isdir(root):
        ap.error(f"no such root folder: {root}")
    bad, n = check(a.report, Tree(root))
    for no, cite, why in bad:
        print(f"MISMATCH report line {no}: {cite} -- {why}")
    print(f"{n} citations checked against {root}: {len(bad)} mismatch(es)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
