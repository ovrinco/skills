from pathlib import Path
import re

root = Path(__file__).resolve().parent
spec = (root / "WORKED_SPEC.md").read_text()
tests = (root / "WORKED_TESTS.md").read_text()
ids = set(re.findall(r"^\| (S\d+|V\d+|I\d+|N\d+) \|", spec, re.M))
covered = set(re.findall(r"^\| (S\d+|V\d+|I\d+|N\d+) \|", tests, re.M))
assert ids and ids == covered
assert covered - {"N1"} != ids, "Dropped persistence coverage must be detected"
assert "waiting" in tests.lower()
print(f"PASS: {len(ids)} specification IDs have visible example coverage; missing-row variant detected.")
