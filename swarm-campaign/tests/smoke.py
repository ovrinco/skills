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

import copy
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp);fixture=ROOT/"examples/pack"
    shutil.copy2(fixture/"requirements.json",d/"requirements.json")
    original=json.loads((fixture/"pack.json").read_text())
    def check(value,expected):
        pack=d/"pack.json";pack.write_text(json.dumps(value))
        run([sys.executable,"scripts/check_pack.py",pack],expected=expected)
    check(original,0)
    changed=copy.deepcopy(original);changed["source_sha256"]="0"*64;check(changed,1)
    changed=copy.deepcopy(original);changed["tasks"]=changed["tasks"][:1];check(changed,1)
    changed=copy.deepcopy(original);changed["tasks"][1]["writes"]=["monitor.py"];check(changed,1)
    changed=copy.deepcopy(original);changed["tasks"][0]["writes"]=["private/secret.txt"];check(changed,1)
    changed=copy.deepcopy(original);changed["tasks"][0]["writes"]=["../escape.txt"];check(changed,2)
    changed=copy.deepcopy(original);changed["tasks"][0]["requires"][0]["text"]="weakened";check(changed,1)
    changed=copy.deepcopy(original);changed["tasks"][0]["acceptance"]=[];check(changed,1)
print("PASS source hash, exact requirements, coverage, ownership, protected paths and scope")
