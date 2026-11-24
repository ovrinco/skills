from pathlib import Path
import re

root = Path(__file__).resolve().parent
record = (root / "DESIGN_RECORD.md").read_text()
amendment = (root / "WORKED_ADDENDUM.md").read_text()
rows = re.findall(r"^\| (A\d+) \| ([^|]+) \| ([^|]+) \| (DR-\d+) \| ([^|]+) \|", amendment, re.M)
assert rows
for identity, place, change, record_id, source in rows:
    assert re.match(r"(adds to|replaces) ", place)
    assert record_id in record and source.strip() in record
assert "DR-03" in amendment and "proposed default" in amendment
assert "S1.1" in amendment and "S1.2" in amendment
print("PASS: numbered amendment retains source/record links, preserved constraints and unaccepted style standing.")
