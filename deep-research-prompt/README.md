# deep-research-prompt

Failure-grounded research briefing and return review, with prompt checks and bounded local image restoration.

Read SKILL.md for the complete workflow and inspect examples/ before real use.

## Requirements

Python3; Tesseract for OCR. All other checks use the standard library.

## Receiving check

From this directory run:

    python3 tests/smoke.py

    python3 tests/ocr_readable.py

## Boundaries

OCR supports specific Markdown reference-style base64 PNG/JPEG inputs. Consequential values need visual comparison.

First-party code is covered by the collection Apache-2.0 LICENSE. Examples are invented. Source/adaptation provenance is in SOURCE_BASIS.json.
