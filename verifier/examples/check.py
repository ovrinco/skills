from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
fixtures = root / "fixtures"
script = root.parent / "scripts/accept_check.py"
cases = []
for case in sorted(fixtures.iterdir()):
    report = case / "report.md"
    if not report.is_file():
        continue
    command = [sys.executable, "-I", str(script), str(fixtures / "root"), str(report)]
    if (case / "candidate").is_dir():
        command.append(str(case / "candidate"))
    result = subprocess.run(command, capture_output=True, text=True)
    expected = 1 if case.name.startswith("p") else 0
    assert result.returncode == expected, (case.name, result.stdout, result.stderr)
    cases.append(case.name)
assert len(cases) == 16, cases
print("PASS: 16 retained acceptance-checker regression fixtures match their expected exit codes.")
