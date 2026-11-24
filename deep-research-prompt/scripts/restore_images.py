#!/usr/bin/env python3
"""Restore supported reference-style base64 images in Markdown using bounded local Tesseract."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import subprocess
import tempfile

DEFINITION = re.compile(r"^\[(image\d+)\]: <data:image/(png|jpeg);base64,([A-Za-z0-9+/=]+)>\s*$", re.M)
REFERENCE = re.compile(r"!\[([^\]]*)\]\[(image\d+)\]")

def restore(source, output, workers):
    if not source.is_dir():
        raise FileNotFoundError("reports directory does not exist")
    files = sorted(source.glob("*.md"))
    if output.resolve() == source.resolve() or source.resolve() in output.resolve().parents:
        # A child named restored is a documented output, never a recursive input.
        if output.resolve() != source.resolve() / "restored":
            raise ValueError("use a separate output directory or the direct restored child")
    if any((output / f.name).exists() for f in files):
        raise FileExistsError("refusing to replace an existing restored report")
    output.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    with tempfile.TemporaryDirectory(prefix="research-ocr-") as temp:
        for report in files:
            text = report.read_text(encoding="utf-8")
            definitions = {}
            for match in DEFINITION.finditer(text):
                key, ext, encoded = match.groups()
                if key in definitions:
                    raise ValueError("duplicate image definition")
                if len(encoded) > 16 * 1024 * 1024:
                    raise ValueError("embedded image exceeds the 12 MiB input limit")
                raw = base64.b64decode(encoded, validate=True)
                total_bytes += len(raw)
                if total_bytes > 64 * 1024 * 1024:
                    raise ValueError("embedded images exceed the 64 MiB per-run limit")
                image = Path(temp) / (key + "." + ext)
                image.write_bytes(raw)
                definitions[key] = image
            def ocr(item):
                key, path = item
                result = subprocess.run(["tesseract", str(path), "stdout", "--psm", "7"],
                                        text=True, capture_output=True, timeout=30)
                value = result.stdout.strip().replace("\n", " ") if result.returncode == 0 else ""
                return key, value
            with ThreadPoolExecutor(max_workers=workers) as pool:
                values = dict(pool.map(ocr, definitions.items()))
            counts = {"restored": 0, "unreadable": 0, "unsupported": 0}
            consumed = set()
            def replace(match):
                key = match.group(2)
                if key not in definitions:
                    counts["unsupported"] += 1
                    return match.group()
                if not values[key]:
                    counts["unreadable"] += 1
                    return match.group()
                consumed.add(key)
                counts["restored"] += 1
                return "⟦" + values[key] + "⟧"
            result = REFERENCE.sub(replace, text)
            result = DEFINITION.sub(lambda m: "" if m.group(1) in consumed else m.group(), result)
            (output / report.name).write_text(result, encoding="utf-8")
            print(report.name, counts)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--workers", type=int, default=2, choices=range(1,5))
    args = parser.parse_args()
    restore(args.reports, args.out or args.reports / "restored", args.workers)

if __name__ == "__main__":
    main()
