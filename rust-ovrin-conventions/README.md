# rust-ovrin-conventions

Concrete Rust errors, dependencies, thin fronts, tests and build-ownership criteria with a compiled example.

Read SKILL.md for the complete workflow and inspect examples/ before real use.

## Requirements

Python3 and an installed rustc on PATH for smoke tests. Cargo is used for the sample crate in normal project work.

## Receiving check

From this directory run:

    python3 tests/smoke.py

## Boundaries

Machine paths and resource policies belong to the receiving project. The sample does not claim GUI framework integration.

First-party code is covered by the collection Apache-2.0 LICENSE. Examples are invented. Source/adaptation provenance is in SOURCE_BASIS.json.
