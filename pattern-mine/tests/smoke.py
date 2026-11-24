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

import importlib.util
spec=importlib.util.spec_from_file_location("checker",ROOT/"scripts/check_citations.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
tree=ROOT/"examples/upstream"
run([sys.executable,"scripts/check_citations.py",ROOT/"examples/report.md","--root",tree])
with tempfile.TemporaryDirectory() as temp:
    t=Path(temp);up=t/"upstream";up.mkdir()
    (up/"engine.py").write_text("value = 2\n")
    (t/"outside.py").write_text("value = 3\n")
    for content in ["engine.py:1 says `value = 3`.","engine.py:9 says invalid.","../outside.py:1 says `value = 3`."]:
        report=t/"report.md";report.write_text(content)
        run([sys.executable,"scripts/check_citations.py",report,"--root",up],expected=1)
    (up/"escape.py").symlink_to(t/"outside.py")
    report.write_text("escape.py:1 says `value = 3`.")
    run([sys.executable,"scripts/check_citations.py",report,"--root",up],expected=1)
print("PASS literal citations, range, traversal and symlink rejection")
