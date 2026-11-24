---
name: design-stage
description: "Author a graphical design sheet and append-only design record, then review actual builds against project sources."
---

# Design direction and build review

Design a change from the surface and evidence that already exist. Write the sheet builders use, preserve its correction history and inspect each actual build before the user review. The sheet remains drafted until its direction is accepted through the project's review process.

## Inputs and roles

Read the outcome's surface list, project design references, current product, relevant source decisions and the earlier sheet with amendments. The caller supplies authority, writable scope, review environment and role assignments.

Design appearance and behavior specification are complementary. This skill defines look, layout and visible wording. A behavioral specification defines triggering states and transitions. Implementation is a separate role. Presentation decks and logos may use their own specialized authoring process.

Inspect the pinned product/reference at the relevant window sizes. Describe the inherited layout and requested delta. If a reference cannot be observed, mark the fact unconfirmed and identify the observation needed. Keep source decisions distinct from the author's taste.

## Write the design sheet

Use templates/DESIGN_SHEET.md with these sections:

1. Screen invariants. State project-specific constraints from the authorized source. Attribute proposed defaults.
2. Window composition. Sketch the regions and their content in reading order.
3. Surfaces. Give each its purpose, regions and empty state.
4. State wording. Map reported state to displayed words and urgency, including an unavailable value.
5. Keys and pointer actions that the design specifies.
6. Vocabulary. Record agreed labels and terminology where exact wording matters.
7. Builder constraints. Explain specific failure modes to avoid and cite their source.
8. Open points. Record each unresolved choice, owner and delegated default. Keep floated ideas visibly tentative.

Write what the builder cannot derive from the inherited conventions or supplied requirements. The sheet does not silently add a required outcome.

Project-specific style belongs in the supplied constraints. This portable method does not impose a palette, model provider, icon family, font, shadow policy or application frame. A data-backed status must match what the engine reports; unresolved data needs honest wording. When a source requests a different design, record the authorized delta.

## Amend without losing the trail

Use templates/ADDENDUM.md. Number every effective change. Each point identifies the old sheet location it replaces or the location it adds to, its source record and time. An unnumbered paragraph cannot change the design.

Append later changes with their time and source. Preserve earlier points. A clarification between reviews becomes a source-linked record row and, if it changes the sheet, an amendment.

## Keep the design record

Use templates/DESIGN_RECORD.md. One row describes one observable behavior or visual property with a stable ID, source time, surface, positive expectation, kind, source, sheet/amendment location and viewed release.

Kinds preserve authority:

- direction. An authorized source specifies it before implementation.
- correction. The owner changes something proposed or built.
- rejected. The owner refuses a shown proposal.
- let-stand. The owner saw it on a named release and accepted it or let it remain within the project's review convention.
- finding. A reviewer observed it.
- default. The author proposed it and review has not established acceptance.

A later row supersedes, confirms or answers an earlier row. Preserve its earlier kind. A let-stand claim needs both the owner review and evidence that the feature was in that release. Without both it remains a default or finding.

Keep the record readable by builders. Actual withheld-check text and selection belong in separate verifier-only material. A reviewer preference never becomes an owner-derived withheld check.

## Review each actual build

Use the permitted runtime and data, at relevant viewports and states. Record release identity and observation conditions. Check reading order, empty/error wording, clipping, labels, legibility, density, interactions and each prior defect.

Write a numbered defect list with reproducible observations and source expectations. Distinguish a defect against agreed direction from a new proposal. Identify the affected owner and release effect. Record a withdrawn finding with its original ID and reason.

After owner review, record their operational decision by source reference, update the design record and append the necessary sheet points. Keep the running product and source evidence available for review.

## Try the example

Read examples/INPUT.md and the supplied sheet/record. Write the requested addendum using templates/ADDENDUM.md. Review against examples/EXPECTED.md afterward. A request to create a deck is a neighboring authoring task and should be routed according to the available presentation capability.

## Receiving check

    python3 examples/check.py

## Evidence and limits

The package supplies a synthetic document exercise and receiving checks. Its historical internal reproof had a neighboring-skill routing failure. This public text needs fresh-session routing and behavior proof. No historic blanket pass is claimed.
