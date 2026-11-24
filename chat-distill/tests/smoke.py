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

with tempfile.TemporaryDirectory() as temp:
    out = Path(temp)/"export"
    for provider in ["claude","codex"]:
        source = ROOT/"examples"/(provider+".jsonl")
        original = source.read_bytes()
        run([sys.executable,"scripts/export_chat_log.py","export","--source",source,"--provider",provider,"--out-root",out])
        exported = next((out/provider).rglob("export.md"))
        text = exported.read_text()
        assert "## U1" in text and "## A1" in text and "Orchard" in text
        assert source.read_bytes() == original
        if provider=="claude":
            assert "sk-"+"x"*32 not in text and "[masked:" in text
            essence = Path(temp)/"essence.md"
            essence.write_text("# Essence\n1. A monitor was requested and its state output described. U1, A1\n")
            run([sys.executable,"scripts/check_essence.py",exported,essence])
            essence.write_text("# Essence\n1. An unknown claim. U999\n")
            run([sys.executable,"scripts/check_essence.py",exported,essence],expected=1)
print("PASS native synthetic provider export, masking, source identity and cited essence")
