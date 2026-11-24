#!/usr/bin/env python3
"""
xlsx_insert_rows.py -- insert rows into a tracker sheet with full renumbering.

Generalizes the hand-written Enriched_04 -> Enriched_05 edit so it works no
matter where the workbook lives or how many rows/tabs/tables it has. The
source workbook is NEVER modified; output goes to --out (or a normalized
suffix of the source name).

Usage:
  python3 xlsx_insert_rows.py SRC.xlsx --sheet Notes \
      --insert '{"before": 86, "values": {"A":"0","B":"https://...","C":"Investigate",...}}' \
      [--insert '{"before": 96, "values": {...}}'] \
      [--out OUT.xlsx] [--template ROWNUM]

Rules (they follow whatever the CURRENT sheet does, not hardcoded facts):
  - "before" is an EXISTING row number in the current file; the new row is
    inserted immediately before it. Multiple --insert are applied in document
    order.
  - Every existing row at/after the first insertion shifts by the number of
    inserted rows before it. Cell refs, <x:mergeCell> refs, and
    <x:conditionalFormatting sqref=...> row numbers are all renumbered, and
    table ref ranges (ref="A10:L160" -> A10:L162) extend automatically because
    the end row renumbers past the insertion.
  - The template row (default: the populated row just above the first
    insertion) supplies the column set and cell style attributes. Only columns
    present in "values" are written; all others become empty cells.
  - Guard rails: refuses to run when the sheet uses formula cells (<x:f>),
    when shared strings appear in the template region (inline <x:v> strings
    only), or when another sheet references this one by cell address.
  - Every boolean/A cell style and column set is inherited from the template,
    so the tool stays correct as the sheet evolves.

Stdlib only. No openpyxl/pip required.
"""
import re, sys, json, zipfile, os, posixpath
import xml.etree.ElementTree as ET

NS = re.compile(r"<(/?)(?:[A-Za-z0-9_]+:)([A-Za-z0-9_.]+)")
def strip_ns(x):
    return NS.sub(r"<\1\2", x)

def workbook_map(z):
    wb = strip_ns(z.read("xl/workbook.xml").decode("utf-8"))
    rels = strip_ns(z.read("xl/_rels/workbook.xml.rels").decode("utf-8"))
    rid2target = {}
    for m in re.finditer(r'<Relationship\s+[^>]*?(?:Id="(\w+)"[^>]*?Target="([^"]+)"|Target="([^"]+)"[^>]*?Id="(\w+)")', rels):
        rid, target = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        rid2target[rid] = target.lstrip("/")
    out = {}
    for m in re.finditer(r'<sheet\s+[^>]*name="([^"]+)"[^>]*r:id="(\w+)"', wb):
        name, rid = m.group(1), m.group(2)
        target = rid2target.get(rid, "")
        if not target.startswith("xl/"):
            target = posixpath.normpath(posixpath.join("xl", target))
        fname = target.rsplit("/", 1)[-1]
        idx = int(re.search(r"(\d+)", fname).group(1))
        out[name] = (target, idx)
    return out

def sheet_tables(z, sheet_path):
    relpath = posixpath.dirname(sheet_path) + "/_rels/" + posixpath.basename(sheet_path) + ".rels"
    if relpath not in z.namelist():
        return []
    tables = []
    for relation in ET.fromstring(z.read(relpath)):
        target = relation.get("Target", "")
        if relation.get("TargetMode") == "External":
            continue
        path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(sheet_path), target))
        if target.startswith("xl/"):
            path = target
        if path.startswith("xl/tables/") and path.endswith(".xml") and path in z.namelist():
            tables.append(path)
    return tables

def parse_rows(xml):
    md = re.search(r"<sheetData>(.*?)</sheetData>", xml, re.S)
    out = []
    for m in re.finditer(r'<row\s+[^>]*r="(\d+)"[^>]*>(.*?)</row>', md.group(1), re.S):
        out.append((int(m.group(1)), m.group(0)))
    return out

def esc(v):
    return (v.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;"))

def shift_rows_in(s, counts, targets):
    """In range refs like A10:L160/A163:L163, shift each row number by the
    number of insertions whose target row <= that row."""
    def rep(m):
        col, row = m.group(1), int(m.group(2))
        return "%s%d" % (col, row + sum(1 for t in targets if t <= row))
    return re.sub(r"([A-Z]{1,3})(\d+)", rep, s)

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    args = sys.argv[2:]

    def arg(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    sheet_name = arg("--sheet")
    out = arg("--out")
    template = arg("--template")
    inserts = []
    i = 0
    while i < len(args):
        if args[i] == "--insert":
            spec = json.loads(args[i + 1])
            for s in (spec if isinstance(spec, list) else [spec]):
                inserts.append((s.get("before"), s.get("values", {})))
            i += 2
        else:
            i += 1

    if not sheet_name or not inserts:
        print("need --sheet and at least one --insert"); sys.exit(1)

    z = zipfile.ZipFile(src)
    wm = workbook_map(z)
    if sheet_name not in wm:
        print("sheet not found: %s (have: %s)" % (sheet_name, ", ".join(wm))); sys.exit(1)
    path, _ = wm[sheet_name]

    xml0 = z.read(path).decode("utf-8")
    xml = strip_ns(xml0)

    if re.search(r"<f(?:\s|>)", xml):
        print("REFUSING: sheet uses formula cells; renumbering would corrupt them."); sys.exit(1)

    rows = parse_rows(xml)
    existing = [r for r, _ in rows]
    if not existing:
        print("no rows found"); sys.exit(1)

    targets = []
    for before, _ in inserts:
        if not isinstance(before, int) or before not in existing:
            print("--insert 'before' must be an existing row number; %r invalid" % before); sys.exit(1)
        targets.append(before)

    # Guard: cross-sheet references to a row at/after the first insertion
    # would be corrupted by renumbering. Header refs (rows < first insertion)
    # are safe and allowed.
    min_tgt = min(targets)
    for n in z.namelist():
        if n.startswith("xl/worksheets/") and n != path:
            d = strip_ns(z.read(n).decode("utf-8"))
            for col, row in re.findall(r"'%s'!\$?([A-Z]{1,3})\$?(\d+)" % re.escape(sheet_name), d):
                if int(row) >= min_tgt:
                    print("REFUSING: %s references %s!%s%s at row %s (>= first insertion %s)."
                          % (n, sheet_name, col, row, row, min_tgt)); sys.exit(1)

    # template row: populated row just above the first insertion
    tgt_row = min(targets)
    if template is None:
        cand = [r for r in existing if r < tgt_row]
        template = max(cand) if cand else existing[0]

    tmpl = next((rb for r, rb in rows if r == template), None)
    if tmpl is None:
        print("template row %s not found" % template); sys.exit(1)

    tmpl_cells = re.findall(r'<c\s+r="([A-Z]+)\d+"([^>]*?)(?:/>|>)', tmpl)
    tmpl_cols = [c[0] for c in tmpl_cells]
    tmpl_attrs = [c[1] for c in tmpl_cells]
    tmpl_rowattrs = re.sub(r'r="\d+"', "", re.match(r"<row\s+([^>]*)>", tmpl).group(1)).strip()

    # guard: template cells must be inline <x:v> strings, not shared strings
    if "t=\"s\"" in tmpl:
        print("REFUSING: template row uses shared strings; only inline strings supported."); sys.exit(1)

    def build_new_row(num, values):
        cells = []
        for col, attrs in zip(tmpl_cols, tmpl_attrs):
            v = values.get(col)
            attr_t = re.search(r'\bt="(\w+)"', attrs)
            if v is None or v == "":
                cells.append('<c r="%s%d"%s/>' % (col, num, attrs))
            else:
                tattr = attr_t.group(0) if attr_t else ' t="str"'
                # an inline-string cell holds its text in <is><t>, never <v> (a <v> there is invalid)
                body = ('<is><t xml:space="preserve">%s</t></is>' if 'inlineStr' in tattr
                        else '<v>%s</v>') % esc(v)
                cells.append('<c r="%s%d"%s%s>%s</c>'
                             % (col, num, attrs.replace(tattr, "") if attr_t else attrs,
                                tattr, body))
        return '<row %s r="%d">%s</row>' % (tmpl_rowattrs, num, "".join(cells))

    def renumber_existing(rb, new_r):
        # shift the row element's own r= and every cell ref r="COL<old>" inside
        rb = re.sub(r'(<row\s+[^>]*?)r="%d"' % r, r'\g<1>r="%d"' % new_r, rb, count=1)
        rb = re.sub(r'r="([A-Z]{1,3})%d"' % r, r'r="\g<1>%d"' % new_r, rb)
        return rb

    # Build output rows in document order.
    by_target = {}
    for before, vals in inserts:
        by_target.setdefault(before, []).append(vals)

    placed = 0
    out_rows = []
    for r, rb in rows:
        if r in by_target:
            for vals in by_target[r]:
                out_rows.append(build_new_row(r + placed, vals))
                placed += 1
        out_rows.append(renumber_existing(rb, r + placed))

    new_xml = re.sub(r"<sheetData>.*?</sheetData>",
                     "<sheetData>%s</sheetData>" % "".join(out_rows),
                     xml, flags=re.S)

    # renumber mergeCell + conditionalFormatting row refs
    def fix_attr(x):
        def rep_refs(m):
            pre, val, post = m.group(1), m.group(2), m.group(3)
            return pre + shift_rows_in(val, None, targets) + post
        x = re.sub(r'(<mergeCell\s+ref=")([^"]+)(")', rep_refs, x)
        x = re.sub(r'(<conditionalFormatting\s+sqref=")([^"]+)(")', rep_refs, x)
        return x
    new_xml = fix_attr(new_xml)

    # extend table ref ranges bound to this sheet
    tbl_updates = {}
    for tpath in sheet_tables(z, path):
        txml = strip_ns(z.read(tpath).decode("utf-8"))
        txml2 = re.sub(r'(<table\s+[^>]*ref=")([^"]+)(")',
                       lambda m: m.group(1) + shift_rows_in(m.group(2), None, targets) + m.group(3),
                       txml, count=1)
        # the table's own filter range grows with it
        txml2 = re.sub(r'(<autoFilter\s+[^>]*ref=")([^"]+)(")',
                       lambda m: m.group(1) + shift_rows_in(m.group(2), None, targets) + m.group(3),
                       txml2, count=1)
        tbl_updates[tpath] = txml2

    if out is None:
        m = re.search(r"_Enriched_(\d+)\.xlsx$", src)
        if m:
            out = src[:m.start(1)] + str(int(m.group(1)) + 1) + src[m.end(1):]
        else:
            out = os.path.splitext(src)[0] + "_edited.xlsx"
    if os.path.realpath(out) == os.path.realpath(src) or (os.path.exists(out) and os.path.samefile(out, src)):
        print("refusing to overwrite source; pick a different --out"); sys.exit(1)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in z.namelist():
            data = z.read(n)
            if n == path:
                data = new_xml.encode("utf-8")
            elif n in tbl_updates:
                data = tbl_updates[n].encode("utf-8")
            zo.writestr(n, data)

    print("inserted %d row%s into %s -> %s"
          % (len(inserts), "s" if len(inserts) != 1 else "", sheet_name, out))

if __name__ == "__main__":
    main()