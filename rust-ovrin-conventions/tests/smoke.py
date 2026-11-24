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

rustc=shutil.which("rustc")
assert rustc, "installed rustc must be on PATH"
source=ROOT/"examples/thin-front/src"
with tempfile.TemporaryDirectory() as temp:
    t=Path(temp);library=t/"liborchard_input.rlib";binary=t/"orchard-input"
    run([rustc,"--edition=2021","--crate-name","orchard_input","--crate-type","lib",source/"lib.rs","-o",library])
    run([rustc,"--edition=2021",source/"main.rs","--extern","orchard_input="+str(library),"-o",binary])
    assert run([binary,"open"]).stdout.strip()=="open"
    assert run([binary,"invalid"],expected=2).stderr.strip()=="InvalidState"
    run([rustc,"--edition=2021","--test",source/"lib.rs","-o",t/"library-tests"])
    run([t/"library-tests"])
print("PASS shared library and thin CLI, invalid input and library tests")
