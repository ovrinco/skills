from pathlib import Path
import base64
import struct
import zlib
import tempfile
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
image = (ROOT/"examples/number-42.png").read_bytes()
with tempfile.TemporaryDirectory() as temp:
    reports=Path(temp)/"reports";reports.mkdir()
    p=reports/"readable.md"
    p.write_text("Value ![number][image1]\n[image1]: <data:image/png;base64,"+base64.b64encode(image).decode()+">\n")
    original=p.read_bytes()
    result=subprocess.run([sys.executable,str(ROOT/"scripts/restore_images.py"),str(reports),"--workers","1"],text=True,capture_output=True,timeout=45)
    assert result.returncode==0,(result.stdout,result.stderr)
    output=(reports/"restored/readable.md").read_text()
    assert "42" in output, output
    assert p.read_bytes()==original
print("PASS real Tesseract restores the invented value 42 without changing the original")
