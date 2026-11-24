#!/usr/bin/env python3
"""
xlsx_dump.py -- dump an evolving .xlsx workbook structure and sheet contents.

Works with any Workbook but is tuned for tracker-style sheets (a table with a
data block and a rich header). Stdlib only (no pip/openpyxl needed).

Usage:
  python3 xlsx_dump.py FILE                     list tabs and their tables
  python3 xlsx_dump.py FILE SHEET               dump one sheet as TSV
  python3 xlsx_dump.py FILE SHEET --table NAME  dump a named table's data block

SHEET is a tab name as it appears in the sheet list ("Notes") or the sheet's
positional file ("sheet1"). Discovery-first: run with no SHEET to see the full
shape, then dump the tab you actually need.
"""
import re, sys, zipfile, os, posixpath
import xml.etree.ElementTree as ET

NS = re.compile(r"<(/?)(?:[A-Za-z0-9_]+:)([A-Za-z0-9_.]+)")
def strip_ns(x):
    return NS.sub(r"<\1\2", x)

def workbook_map(z):
    """sheet tab name -> (sheet file path, sheet index 1-based)."""
    wb = strip_ns(z.read("xl/workbook.xml").decode("utf-8"))
    rels = strip_ns(z.read("xl/_rels/workbook.xml.rels").decode("utf-8"))
    rid2target = {}
    for m in re.finditer(r'<Relationship\s+[^>]*?(?:Id="(\w+)"[^>]*?Target="([^"]+)"|Target="([^"]+)"[^>]*?Id="(\w+)")', rels):
        rid, target = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        target = target.lstrip("/")
        if not target.startswith("xl/"):  # relative to xl/ (LibreOffice writes it this way)
            target = "xl/" + target
        rid2target[rid] = target
    out = {}
    for m in re.finditer(r'<sheet\s+[^>]*name="([^"]+)"[^>]*r:id="(\w+)"', wb):
        name, rid = m.group(1), m.group(2)
        target = rid2target.get(rid, "")
        fname = target.rsplit("/", 1)[-1]
        idx = int(re.search(r"(\d+)", fname).group(1))
        out[name] = (target, idx)
    return out

def sheet_tables(z, sheet_path):
    relpath = posixpath.dirname(sheet_path) + "/_rels/" + posixpath.basename(sheet_path) + ".rels"
    if relpath not in z.namelist():
        return {}
    tables = {}
    for relation in ET.fromstring(z.read(relpath)):
        target = relation.get("Target", "")
        if relation.get("TargetMode") == "External":
            continue
        path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(sheet_path), target))
        if target.startswith("xl/"):
            path = target
        if not path.startswith("xl/tables/") or path not in z.namelist():
            continue
        table = ET.fromstring(z.read(path))
        columns = [c.attrib["name"] for c in table.iter() if c.tag.rsplit("}",1)[-1] == "tableColumn"]
        tables[table.get("displayName", table.get("name", path))] = {"ref": table.get("ref"), "columns": columns, "file": path}
    return tables

def col_to_idx(ref):
    n = 0
    for ch in ref:
        n = n * 26 + (ord(ch.upper()) - ord("A") + 1)
    return n - 1

def idx_to_col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s

def is_col(ref):
    return isinstance(ref, str) and bool(re.fullmatch(r"[A-Z]+", ref))

def shared_strings(z):
    """Shared string table (index -> text); empty if the workbook has none."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(t.text or "" for t in si.iter() if t.tag.endswith("}t")) for si in root if si.tag.endswith("}si")]

def parse_rows(xml, sst=()):
    """Return ordered list of (row_num, {col_letter: value}); shared strings resolved."""
    import xml.etree.ElementTree as ET
    rows = []
    for row in ET.fromstring(xml).iter():
        if not row.tag.endswith("}row"):
            continue
        cells = {}
        for c in row:
            if not c.tag.endswith("}c"):
                continue
            col = re.match(r"[A-Z]+", c.get("r", "")).group(0)
            t = c.get("t")
            v = next((x.text for x in c if x.tag.endswith("}v")), None)
            if t == "inlineStr":
                v = "".join(x.text or "" for x in c.iter() if x.tag.endswith("}t"))
            elif t == "s" and v is not None:
                v = sst[int(v)]
            if v not in (None, ""):
                cells[col] = v.replace("\t", " ").replace("\n", " ")
        rows.append((int(row.get("r")), cells))
    return rows

def dump_rows(rows):
    if not rows:
        return "(no rows)"
    nmax = max((col_to_idx(max(c.keys())) for _, c in rows if c and is_col(max(c.keys()))), default=col_to_idx("V"))
    cols = [idx_to_col(i) for i in range(nmax + 1)]
    lines = ["ROW\t" + "\t".join(cols)]
    for rn, cells in rows:
        lines.append(str(rn) + "\t" + "\t".join(cells.get(cc, "") for cc in cols))
    return "\n".join(lines)

def resolve_sheet(name, wm):
    if name in wm:
        return wm[name][0]
    for tab, (path, idx) in wm.items():
        if path == "xl/worksheets/" + name or name.isdigit() and idx == int(name):
            return path
    raise SystemExit("sheet not found: %s (have: %s)" % (name, ", ".join(wm)))

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    z = zipfile.ZipFile(src)
    wm = workbook_map(z)
    if len(sys.argv) == 2:
        for tab, (path, idx) in sorted(wm.items(), key=lambda kv: kv[1][1]):
            print("tab %02d  %-16s %s" % (idx, tab, path))
            for tname, t in sheet_tables(z, path).items():
                print("      table %-28s ref=%-10s cols=%s" % (tname, t["ref"], ",".join(t["columns"])))
        print("\nUse: xlsx_dump.py %s TABNAME [--table TABLENAME]" % src)
        sys.exit(0)
    sheet = resolve_sheet(sys.argv[2], wm)
    xml = z.read(sheet).decode("utf-8")
    rows = parse_rows(xml, shared_strings(z))
    if "--table" in sys.argv:
        tname = sys.argv[sys.argv.index("--table") + 1]
        t = sheet_tables(z, sheet)[tname]
        ref = t["ref"]
        m = re.match(r"([A-Z]+)(\d+)(?:\:([A-Z]+)(\d+))?", ref)
        c0, r0, c1, r1 = m.groups()
        body = [ (rn, {k: v for k, v in cells.items() if col_to_idx(k) <= col_to_idx(c1)}) for rn, cells in rows ]
        lines = ["ROW\t" + "\t".join(t["columns"])]
        for rn, cells in body:
            if int(r0) <= rn <= int(r1):
                line = [str(rn)]
                for cc in t["columns"]:
                    line.append(cells.get(idx_to_col(len(line)-1), ""))
                lines.append("\t".join(line))
        print("\n".join(lines))
    else:
        print(dump_rows(rows))
    z.close()

if __name__ == "__main__":
    main()