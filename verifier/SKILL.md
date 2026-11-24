---
name: verifier
description: "Independently exercise a delivered tool against fixed acceptance, preserve observed coverage and report defects without repair."
---

# Independent verification

Verify a build you did not author. Observe its required behavior through the permitted running interface and write evidence. Keep implementation repair and outcome acceptance with their respective owners.

## Roles and authority

The verifier must be independent of authorship of the delivered work and its implementation direction. Record actual role/session identity. A new pane name alone does not erase authorship.

The caller supplies the outcome, permitted tool/environment/data, release identity, writable report/evidence paths and any explicit hidden inputs. Use the declared scope. A source review and a builder self-check have their own purposes and do not substitute for independent observation.

Do not repair the product, settings, data or requirements while verifying. Report a reproducible fault and return it to the implementation owner. If startup cannot be performed through the documented route, record that finding.

## Observe the fixed journey

Read OUTCOME.md, its result standing and stated failure conditions. Read a visible specification if supplied. Save its hash and the identity of the actual release being exercised.

Exercise the entry point the user is meant to use, using the authorized representative inputs. A fixture can establish a mechanism's behavior when that is the claim. A screenshot or simulated response does not establish a running workflow. Keep actual and simulated scope explicit.

For each journey step record the exact command/action, the observed content and counts, evidence location and verdict. Then give each result line its source standing and verdict. Check stated failure conditions separately. An unrelated issue is a backlog note unless it breaks a selected requirement.

Use templates/REPORT.md. Evidence must identify the command, query or capture method a reader can repeat. Preserve overlapping-sample boundaries and record missing coverage. Reusing an earlier accepted result requires unchanged relevant hashes and an explicit reuse statement.

## Verdict vocabulary

A step is proven or insufficient. A result is:

- proven. Every required part was observed and every supporting journey step is established.
- partly. A named part was observed; give its extent and remaining coverage.
- held. An external permission, environment or resource prevents the required observation; identify that condition.
- insufficient. Observed behavior is wrong or missing, or the result cannot be reached through the delivered tool.

Partial coverage never becomes complete proof. A zero exit or an opened window proves only the corresponding bounded claim. End with counts of required lines proven and a list of everything not checked, with reasons.

## Mechanical acceptance helper

Run the included read-only checker:

    python3 -I scripts/accept_check.py CAMPAIGN_ROOT REPORT [CANDIDATE_DIRECTORY]

It scans delivered code for supported stub patterns and checks self-walk/walk-record fields. Use the documented OC-number result citation and Walk record format in templates/REPORT.md. Script exit 1 reports blocking findings; exit 2 is an input error.

This lint is heuristic. It trusts declared author IDs and evidence-path existence. It cannot authenticate who performed an observation, or prove a log's semantic correctness. Review each finding and record its effect. Do not suppress a failure by changing the acceptance requirement or silently omitting a required check. A false positive needs an attributed resolution and the appropriate supported test-path or rule-text treatment.

Before any destructive or overwriting proof step, check that the caller actually permits it and that the preservation/recovery record exists. Record evidence of the operation and its preconditions. A review of a missing prior record cannot retroactively create it.

## Withheld checks

Only read actual withheld material if the caller supplies it for this role. Record the ordinary journey first. Run withheld checks afterward and report failures by ID, affected result, strength and evidence. Keep their wording out of reports builders can read.

## Try the example

Run examples/check.py. It replays the included positive and negative checker fixtures. Read examples/INPUT.md and perform the small public sample's journey, then author a report as a non-author. Keep examples/EXPECTED.md away until your report is complete.

## Evidence and limits

The checker implementation is preserved from the installed method and the receiving fixture suite exercises its actual exit behavior. That is mechanical proof only. Current-model independent review behavior still needs a fresh session on the published skill hash.
