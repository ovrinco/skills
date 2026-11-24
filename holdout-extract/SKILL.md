---
name: holdout-extract
description: "Derive verifier-only checks from source corrections and inspect builder inputs for accidental exposure."
---

# Withheld behavioral checks

Use prior authorized corrections to test an outcome beyond the public proof journey. Checks remain observable on the product and tied to required results. A separate closing verifier receives them after normal journey observations.

## Inputs and scope

The caller supplies the outcome, source decisions and design record, plus separate builder and verifier input locations. Read only those authorized sources. Research or engine-only work may have no interface holdout due; explain the applicable scope instead of inventing one.

Visible tests are intentionally readable by builders. Actual withheld checks are controlled verifier inputs. The caller defines authoring and reader roles. Do not let a builder role read the checks it is meant to face.

## Derive the rows

Use templates/HOLDOUT.md. Each row has ID, surface, an observable correct behavior, result-line ID, source locator and source strength.

1. Use explicit direction, correction and rejection records as explicit sources.
2. Use an observed and accepted default as a silent source only when the project supplies evidence of that standing.
3. Exclude a reviewer's taste, an unaccepted default or an inferred requirement as owner-derived checks.
4. Specify something a person can actually observe: a command effect, visible state, persistence after restart or a correct value.
5. Name the required result it protects. Remove rows that protect no selected result or stated failure condition.
6. Preserve the source locator and express the check without copying private speech.
7. Add project-specific honesty conditions where actually required, such as meaningful labels, accurate unknown states and absence of developer stand-ins.

Look beyond duplicating the public journey. A corrected second-page state or restart condition may reveal a gap the public steps do not exercise. Keep the set bounded by useful coverage and the caller's capacity.

## Store and inspect separation

Place actual checks outside builder input roots, with a hash record and declared reader scope. A public demonstration fixture can show the format; it is distinct from a real project's confidential evaluation material.

Before giving builder inputs to a worker, inspect paths, file contents and manifests for references to the withheld location or marker. Use the read-only helper:

    python3 scripts/exposure_check.py --withheld PATH --marker UNIQUE_MARKER BUILDER_INPUT_ROOT...

Give it only builder roots. It reports zero searched files as an error and reports path/marker exposure. Supply symlinks explicitly for review; the helper flags them instead of following them.

The scan cannot establish access control or detect every paraphrased/copied check. Use filesystem/tool isolation where the project requires stronger separation. The caller must also review agent context and any other supplied materials.

If exposure occurred, record which role could read it, whether the task ran, and which checks are spent. Replace the exposed checks before a later independent proof. Keep original evidence private.

## Closing verification

The closing verifier performs and records the public journey first, then reads the supplied checks. Report a failed explicit check by ID, protected result and evidence. Keep its wording out of builder-readable reports.

A failed silent check raises an outcome clarification for the owner. Keep it distinct from failure of an explicit requirement. A later correction changes the requirement through its actual authority.

## Try the example

Use examples/INPUT.md and the public teaching records to draft rows. Do not inspect the expected criteria until done. Run examples/check.py to exercise empty input, path leakage, marker leakage and a clean builder packet.

## Evidence and limits

The public fixtures are teaching material. They are not hidden production checks. Current receiving tests cover the local separation helper; new authoring and role separation behavior need a fresh-session proof on these exact public instructions.
