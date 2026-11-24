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

import base64
import struct
import zlib
run([sys.executable,"scripts/check_prompt.py","examples/prompt.md"])
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp)
    bad=d/"bad.md"
    bad.write_text("```\nExample Private Company\n```\n")
    run([sys.executable,"scripts/check_prompt.py",bad],expected=1)
    reports=d/"reports";reports.mkdir()
    # A blank, valid synthetic PNG tests unreadable-image preservation through real Tesseract.
    width,height=64,32
    def chunk(tag,raw):
        return struct.pack(">I",len(raw))+tag+raw+struct.pack(">I",zlib.crc32(tag+raw)&0xffffffff)
    image=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+chunk(b"IDAT",zlib.compress((b"\0"+b"\xff"*(width*3))*height))+chunk(b"IEND",b"")
    report=reports/"sample.md"
    report.write_text("Unreadable ![blank][image1]\nUnsupported ![remote][image2]\n[image1]: <data:image/png;base64,"+base64.b64encode(image).decode()+">\n")
    before=report.read_bytes()
    run([sys.executable,"scripts/restore_images.py",reports,"--out",d/"reading","--workers","1"])
    text=(d/"reading/sample.md").read_text()
    assert "![blank][image1]" in text and "![remote][image2]" in text
    assert report.read_bytes()==before
    repeated=subprocess.run([sys.executable,str(ROOT/"scripts/restore_images.py"),str(reports),"--out",str(d/"reading")],text=True,capture_output=True)
    assert repeated.returncode!=0
print("PASS brief checker, private-name rejection, real OCR unreadable/unsupported preservation and collision refusal")
