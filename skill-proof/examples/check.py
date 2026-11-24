from pathlib import Path
import json
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
script = root.parent / "scripts/check_cases.py"
skill = root.parent / "SKILL.md"
baseline = json.loads((root / "cases.json").read_text())
with tempfile.TemporaryDirectory(prefix="skillproof-receiving-") as tmp:
    path = Path(tmp) / "cases.json"
    def run(data, expected):
        path.write_text(json.dumps(data))
        result = subprocess.run([sys.executable, str(script), str(path), "--skill", str(skill)],
                                 capture_output=True, text=True)
        assert result.returncode == expected, result.stdout + result.stderr
    run(baseline, 0)
    wrong = json.loads(json.dumps(baseline))
    wrong["skill_sha256"] = "0" * 64
    run(wrong, 1)
    wrong = json.loads(json.dumps(baseline))
    wrong["cases"][1]["id"] = wrong["cases"][0]["id"]
    run(wrong, 1)
print("PASS: case preparation accepted; changed skill hash and duplicate identity rejected. No sessions run.")
