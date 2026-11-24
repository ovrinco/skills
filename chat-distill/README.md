# chat-distill

Complete native single-session export with masking and a cited optional distillation checker.

Read SKILL.md for the complete workflow and inspect examples/ before real use.

## Requirements

Python3 standard library. Synthetic Claude Code and Codex examples included.

## Receiving check

From this directory run:

    python3 tests/smoke.py

## Boundaries

Harness schemas change. Pattern masking cannot guarantee removal of every secret.

First-party code is covered by the collection Apache-2.0 LICENSE. Examples are invented. Source/adaptation provenance is in SOURCE_BASIS.json.
