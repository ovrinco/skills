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

examples=ROOT/"examples"
for row in json.loads((examples/"manifest.json").read_text()):
    path=examples/row["path"]
    assert path.is_file() and path.stat().st_size==row["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row["sha256"]
for name in ["STATE.md","BRIEF.md","BLOCKER.md","PACK.md"]:
    text=(examples/name).read_text()
    assert "INPUT.md" in text
    assert "Next action" in text or "EXPECTED.md" in text
print("PASS four handover forms and exact input manifest; human context sufficiency remains judgment")
