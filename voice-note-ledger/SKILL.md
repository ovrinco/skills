---
name: voice-note-ledger
description: "Correct names conservatively in a supplied transcript and extract a source-linked ledger with receipts and unresolved-name handling."
---

# Voice note ledger

Use an explicit text file, stdin or structured transcript JSON supplied by the user. Audio needs its authorized transcription tool first. This package starts no recognizer or network service.

## Conservative correction
Read the transcript and the chosen dictionary. Run python3 scripts/normalize.py SOURCE --out OUTPUT --names names.json. The complete normalizer keeps every source unit and index, protects code/URLs/paths/verbatim spans and preserves non-name text. Text lines are one-based; structured segments are zero-based.

Read corrections.json before proceeding. Ambiguous names remain unresolved. Use --decisions FILE for explicit apply/keep/flag decisions, each with the original segment/line, spelling, replacement and reason. Use --verbatim FILE for exact protected spans. Never guess an identity to make a check pass.

Run python3 scripts/normalize.py --names names.json --check OUTPUT. --locate PHRASE prints unit/offset references; --lint-names validates the dictionary; --dry-run writes nothing. The default output is the local voice-output directory. An explicit --out is preferred.

Outputs are corrected_transcript.md and corrections.json with source/output hashes, unit bounds, every correction, unresolved identities and protected spans. The structural receipt implements a correction-reader compatibility contract. It does not prove a separate index accepted the file.

## Ledger
Read the whole corrected transcript and author ledger.json. Each item has id, category, area, capture, stance, timing and sources. Use VN-001 upward in source order. Capture one fact per item, retain tentative/estimated stance and cite actual source units. Text references are L1 or L1-L3. Structured references are voxtype:folder:segment or ranges, with @offset for a single long segment.

Categories are Action, Open question, Reminder, Research, Proposal, Direction / constraint, Hypothesis, Observation, Reference, Decision and Risk / dependency. Decisions require a choice the speaker made. A date in a reminder does not schedule it.

Run python3 scripts/ledger.py OUTPUT when ledger.json and corrections.json are together. The helper validates entries and source ranges and produces ledger.md with a date/trigger index. --check writes nothing; --corrections FILE or --units N supplies explicit bounds; --from-md TABLE converts a validated table back to JSON.

Read uncited units for material omitted from the ledger. Run the names check over all outputs. Report corrections, remaining ambiguity and category counts.

## Integrations and proof
The transcript-only path needs Python3 and the supplied dictionary. Structured VoxType-shaped JSON is accepted by explicit path. Native note discovery, recording import and tracker filing are optional integrations selected separately by the user. This package does not modify native recordings or schedule tasks.

The bundled Orchard/Cedar examples are invented. Run python3 tests/smoke.py for text correction/preservation, receipt production, valid ledger rendering and invalid-source rejection.
