from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent
script = root.parent / "scripts/outcome_check.py"
original = (root / "campaign/OUTCOME.md").read_text()
with tempfile.TemporaryDirectory(prefix="charter-receiving-") as tmp:
    candidate = Path(tmp)
    path = candidate / "OUTCOME.md"
    def run(text, expected):
        path.write_text(text)
        result = subprocess.run([sys.executable, str(script), str(candidate)],
                                capture_output=True, text=True)
        assert result.returncode == expected, result.stdout + result.stderr
    run(original, 0)
    run(original.replace("## Sources (F10)", "## Sources"), 1)
    run(original.replace("Result lines 2.", "Result lines 8."), 1)
    wave = candidate / "wave1"
    wave.mkdir()
    (wave / "T01_wrong.md").write_text("Outcome: OC-01, result line 99: Unselected work.")
    run(original, 1)
print("PASS: complete charter accepted; missing field, unproved result and unknown directive result rejected.")
