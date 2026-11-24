from pathlib import Path
import json
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
script = root.parent / "scripts/citation_check.py"
with tempfile.TemporaryDirectory(prefix="decision-receiving-") as tmp:
    temp = Path(tmp)
    ledger = temp / "ledger.json"
    outcome = temp / "OUTCOME.md"
    baseline = (root / "OUTCOME.md").read_text()
    data = json.loads((root / "ledger.json").read_text())
    def run(expected):
        ledger.write_text(json.dumps(data))
        result = subprocess.run([sys.executable, str(script), "--ledger", str(ledger),
                                 "--json", str(outcome)], capture_output=True, text=True)
        assert result.returncode == expected, result.stdout + result.stderr
    outcome.write_text(baseline)
    run(0)
    outcome.write_text(baseline.replace("OD-2026-01-01-01", "OD-2026-01-01-99"))
    run(1)
    outcome.write_text(baseline)
    data["entries"][0]["source"] = "brief:author-reading"
    run(1)
print("PASS: direct-source example accepted; unknown IDs and stated-on-reading rejected.")
