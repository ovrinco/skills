from pathlib import Path
import json
import subprocess
import sys
import tempfile
import shutil
import hashlib
ROOT = Path(__file__).resolve().parents[1]
def run(args, expected=0):
    result = subprocess.run([str(x) for x in args], cwd=ROOT, text=True, capture_output=True, timeout=90)
    assert result.returncode == expected, (args, result.returncode, result.stdout, result.stderr)
    return result

run([sys.executable,"scripts/normalize.py","--lint-names"])
source = ROOT / "examples/transcript.txt"
before = source.read_bytes()
with tempfile.TemporaryDirectory() as temp:
    out = Path(temp) / "projection"
    run([sys.executable,"scripts/normalize.py",source,"--out",out,"--names",ROOT/"names.json"])
    text = (out/"corrected_transcript.md").read_text()
    assert "Orchard pump" in text and "Cedar sensor" in text
    assert "https://orchrd.example" in text and "orchrd_code" in text
    receipt = json.loads((out/"corrections.json").read_text())
    assert receipt["summary"]["corrections"] >= 2 if "corrections" in receipt["summary"] else len(receipt["corrections"]) >= 2
    shutil.copy2(ROOT/"examples/ledger.json",out/"ledger.json")
    run([sys.executable,"scripts/ledger.py",out])
    assert (out/"ledger.md").is_file()
    entries = json.loads((out/"ledger.json").read_text())
    entries[0]["sources"] = ["L99"]
    (out/"ledger.json").write_text(json.dumps(entries))
    run([sys.executable,"scripts/ledger.py",out,"--check"],expected=1)
assert source.read_bytes() == before
print("PASS names, protected spans, source preservation, ledger rendering and invalid locator")
