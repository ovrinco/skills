---
name: charter-author
description: "Write or amend an outcome charter with source standing, a fixed proof journey and complete requirement accounting."
---

# Outcome charter

A charter states the result a person should be able to achieve and the evidence that will establish it. It remains stable when an implementation falls short. Use this method to create an outcome, change its result lines after a decision, or reconcile an inherited document stack.

## Inputs and boundaries

Use the request, selected requirements, decision references, existing outcome and current product evidence supplied by the caller. Read references/OUTCOME_STANDARD.md and templates/OUTCOME.md. The caller identifies writable scope and authority. A plan or summary can point at a source; retain the distinction between original requirements and an agent's reading.

Read every selected requirement. Record source precedence explicitly. Newest authorized direct direction governs a conflict, followed by the chosen requirements source and project governance. Record an unresolved conflict and its owner instead of silently dropping a side.

A charter identifies surfaces and outcomes. Detailed behavior, design and implementation assignments are subsequent work. Individual neighboring skills can supply those parts when installed, or equivalent project inputs can be given directly.

## Source handling

- Give each requirement an exact source locator and preserve its stated, floated or drafted standing. Separate the required core from proposed implementation detail.
- When a source points to a reference artifact, identify its revision and the change requested against it.
- Keep private personal material out of the delivered charter. Refer to authorized evidence rather than copying private conversation.
- Check live statements about installed, running or missing behavior before writing them. Record a discrepancy between the source and observed state.
- An inference stays an attributed proposal. A later document cannot promote it into an operator decision.

## The charter page

Use all ten fields in the standard. A compact outcome can occupy one page; split supporting material where necessary while keeping the result understandable.

1. Outcome. Write a single observable result in plain language. Describe what the person sees and can do. Attribute its standing.
2. Result lines. Give each a stable numbered identity, observable result, source and standing. Carry every chosen requirement. Identify which parts are proposed and who decides them.
3. Proof. Write the journey and observable expectations before implementation. Every required result has at least one journey step. Give the scope and origin of each threshold and name the evidence location.
4. Not done if. Identify ways the specific result could appear complete while missing the requested behavior. Include incomplete coverage, a substitute implementation or a picture standing in for a running result when the result requires one.
5. Grace. State implementation differences that do not change the result and can be decided within the assignment.
6. Boundary. Identify adjacent ownership and handoff points so work can be routed correctly.
7. Depends on and unblocks. Name inputs, environments or products the outcome needs and work it enables.
8. Work and roles. Map each coherent part to its result lines and observable proof. Record permitted settings and writable scope. Assign actual roles and the caller's chosen harness configuration.
9. Status. State the known release identity, work-folder-only material, gaps and unresolved decisions. Distinguish written, implemented, installed and observed.
10. Sources. List the references needed to recheck the result and its standing.

Record open points with an attributed default where the caller has delegated the choice. A point requiring external authority retains its decision owner. Keep exact settings changes explicit. Unknowns must not become invented requirements.

## Reconcile an old document stack

Work through an explicit bounded list of source files. Maintain a table giving each requirement or document a destination in the charter, an open point, or a cited superseding decision. Carry meaningful constraints and proof conditions through that table.

Where sources conflict, apply the declared source order and record the resolution. Material the author adds remains drafted. Keep previous source bytes according to the caller's preservation policy. Moving or archiving files requires the assignment's authority.

## Check and amend

Read the page as both builder and independent reviewer. Can each proof step be run and judged from the supplied materials? Is every required result reached? Does the page explain current gaps without shrinking the goal?

Run the portable structure check:

    python3 scripts/outcome_check.py PATH_TO_CAMPAIGN

It checks the published ten-field format, numbered results and proof references, and result references in wave directories. Review its JSON findings. A clean result is structural lint, not behavioral proof. The house-specific tracker, model-lane and protected-tree checks of the original campaign validator are outside this portable subset.

On an authorized correction, append a dated amendment with source, affected result IDs and the changed expectation. Keep the previous result readable and derive its affected lower-level documents again. A failed implementation is evidence about the build.

## Try the example

Read examples/INPUT.md and examples/OUTCOME.md. Review the stated and floated material and the amendment request. Use examples/EXPECTED.md only after doing the task. Run examples/check.py for positive and deliberately broken structure cases.

## Evidence and limits

The checker and fixture exercise are mechanical receiving checks. Public adapted behavior still needs fresh-session proof. The method retains the substantive source contract while removing private stores and obsolete lane defaults.
