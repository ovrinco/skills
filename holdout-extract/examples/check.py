from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).resolve().parents[1] / "scripts/exposure_check.py"
with tempfile.TemporaryDirectory(prefix="holdout-receiving-") as tmp:
    root = Path(tmp)
    builder = root / "builder"
    builder.mkdir()
    withheld = root / "verifier/checks.md"
    withheld.parent.mkdir()
    withheld.write_text("Teaching verifier inputs")
    def run(expected):
        result = subprocess.run([sys.executable, str(script), "--withheld", str(withheld),
                                 "--marker", "PRIVATE_CHECKSET_73", str(builder)],
                                 capture_output=True, text=True)
        assert result.returncode == expected, result.stdout + result.stderr
    run(1)
    (builder / "brief.md").write_text("Implement title validation through the public interface.")
    run(0)
    (builder / "brief.md").write_text(str(withheld))
    run(1)
    (builder / "brief.md").write_text("PRIVATE_CHECKSET_73")
    run(1)
    (builder / "brief.md").write_text("Public input only")
    (builder / "leak").symlink_to(withheld)
    run(1)
print("PASS: clean input accepted; empty search, path/marker exposure and symlink input rejected.")
