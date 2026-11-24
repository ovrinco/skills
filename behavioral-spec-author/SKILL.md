---
name: behavioral-spec-author
description: "Specify observable surface behavior, then derive visible acceptance tests in a separate assignment."
---

# Behavioral specification and visible tests

A specification connects an outcome to the states and actions of the surface a person uses. Derive visible tests from that specification before implementation. Keep the specification author, test author and implementer identifiable.

## Inputs and role

Read the supplied outcome, requirement sources, design sheet with amendments and design record. For a terminal surface, also read its help and exercise the permitted public interface. Specify one result line and one surface, or a named part of it. A direct small change can be expressed fully in its implementation brief.

The caller supplies the output location, writable scope, role assignments and any permitted tool/data access. Harness and model choice follow that caller's authority. Design appearance belongs to the design source. Withheld checks belong to their separate owner and stay unread by this task.

## Write the specification

Use templates/SPEC.md. Keep one compact page per part. Split a large surface into coherent parts instead of omitting cases.

1. Head the page with the outcome identity, result line, its standing, surface and source references.
2. Enumerate states with stable S identifiers. For each, record when it applies, what the person sees, what they can do and where it transitions. Cover first run, empty, one, many, large, loading, error, stale/concurrent changes, connection loss and overlays as applicable. Explain an inapplicable class.
3. For reported values, assign V identifiers and map engine values to displayed words. Include an unavailable or unknown value and any state-dependent rendering.
4. For inputs, assign I identifiers and name the relevant states, visible effect and failure behavior. Include keyboard, click, drag and data-driven events where supported.
5. For critical actions, state preconditions, confirmation if required by the source, in-progress behavior, success, failure and side effects. Address irreversible, destructive, bulk and external actions.
6. Derive N identifiers for the specific prohibited behavior established by the outcome and project decisions.
7. Trace each relevant proof-journey step through those identifiers.
8. Record unanswered points or source conflicts, with the owner of the answer. Attribute a proposed behavioral default as proposed. An unsupported threshold remains open.

Every row cites a source. Preserve the standing of tentative and author-proposed material. Current authorized corrections override the rows they explicitly supersede; keep a readable amendment trail. Use the approved design wording for display text. A visual or wording gap goes back to the design owner.

Before handing the page to the next author, ensure each state has a way in and a way out or is final, each input has applicable states, each reported value has its text, and unresolved questions are explicit.

## Derive visible tests as a separate assignment

The test author reads the specification, outcome and public interface. Supply only those inputs. Internal code and actual withheld checks stay outside this assignment.

Use templates/TESTS.md and derive one observable check for each state, value, input, critical action, N row and journey step. Name each test by the specification ID. Describe the starting state, action, expected observation and evidence method. An automatic trigger has both met and unmet checks.

Drive keys, commands and visible controls. Assertions about internal implementation require a different test. Record an unobservable requirement as a gap. A row awaiting a design decision has a waiting entry.

End with a complete trace table mapping every ID to a check, gap or wait. Keep the approved test set fixed while implementation proceeds. If a test is wrong, amend the source specification with reason and date, then derive the affected tests again.

## Try the example

Read examples/INPUT.md and examples/OUTCOME.md. Produce a specification, then give it to a separate reader to derive tests. Keep examples/EXPECTED.md away from both authors until review.

## Receiving check

    python3 examples/check.py

## Evidence and limits

The example is a synthetic document exercise. Receiving checks validate its file set and source links. A current model's trigger behavior and independent derivation require fresh-session observation. Historical internal proof is not claimed for this public text.
