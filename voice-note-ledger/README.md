# voice-note-ledger

Names-only transcript correction, ambiguity receipts and a source-cited action/question ledger.

Read SKILL.md for the complete workflow and inspect examples/ before real use.

## Requirements

Python3 standard library. Structured transcript input is optional; no recognizer or tracker is required.

## Receiving check

From this directory run:

    python3 tests/smoke.py

## Boundaries

Native recording imports and tracker writes need separately chosen adapters. No fresh-model extraction proof is claimed.

First-party code is covered by the collection Apache-2.0 LICENSE. Examples are invented. Source/adaptation provenance is in SOURCE_BASIS.json.
