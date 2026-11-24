---
name: decision-record-author
description: "Record decisions with source, standing and supersession, then identify the authorized document changes they require."
---

# Decision records and their effects

Record decisions so later work can distinguish the operator's decision, a tentative idea and an agent's interpretation. Corrections append a new entry that names the earlier one. Keep the prior history readable.

## Inputs and authority

The caller supplies the authorized source, ledger path, record format, writable scope and affected project documents. Read those sources and recent entries for the same subject. A decision inside one implementation task belongs in its task record unless the caller asks for wider governance.

Personal material and credentials stay outside this record. Rephrase the operational decision and retain an exact authorized source locator. A conversational source alone does not grant permission to alter unrelated rule files, trackers or settings. If the role lacks write authority, prepare a proposed entry and impact list.

## Append the decision

Use templates/ENTRY.json and the project's schema. The fields are:

- id. Allocate the next identifier using the ledger's supported writer or its documented single-writer procedure.
- time. Record when the decision was made. Distinguish import time or an uncertain time.
- source. Use a locator that can be reopened, such as a decision message, transcript segment or source file.
- scope. Name the affected product or standing practice.
- decision. Choose the kind, such as direction, correction, permission, answer, intent or question.
- detail. Use separate named fields for separate points. Attribute expectations and uncertainty.
- detail.standing. Preserve stated, floated and drafted status. Identify mixed standing by field where necessary.
- detail.open. Name unanswered questions and their decision owner.
- detail.orchestrator_reading. Keep any inference separate. Treat it as drafted in downstream documents.
- detail.amends or detail.supersedes. Identify the earlier entries changed by this one.
- detail.touches. Identify the rule, charter, brief or tracking record affected.
- detail.orchestrator_action. State what has actually happened.

Keep independent facts distinct. An approval identifies the proposal or action approved. A conditional decision states its condition. A wrong entry gets a new corrective entry. Retain older legacy records in their original form.

Before writing, inspect the current version to avoid stale ID allocation. Use the project's writer/locking API where concurrent writes are possible. This package provides a record format and read-only citation lint; it does not implement an atomic ledger service.

Validate JSON syntax and inspect the change against the source. The citation checker can then inspect supported Markdown result rows:

    python3 scripts/citation_check.py --ledger PATH_TO_LEDGER --register PATH_TO_PUBLIC_REGISTER --json FILE...

The register argument is optional. Every file is explicit. See references/CITATION_SCOPE.md for supported source-locator conventions and limits.

## Standing governance changes

Create an additional governance record only when a standing rule changes. Use templates/GOVERNANCE.md. Record decision, forces, named alternatives and their reasons, impact, authority/source and supersession. A direction about one product can remain in the decision ledger.

Change only authorized files. Retain previous versions according to project policy. Do not make proposed policy appear adopted through publication of the template.

## Propagate the effect

1. Identify all affected rules, charters, implementation briefs and tracking entries.
2. Apply an authorized change at its source, citing the decision. An implementation note cannot substitute for correcting the controlling requirement.
3. At a safe work boundary, update assignments that depend on it. An explicit stop or risk of damage takes effect according to its authority.
4. Keep future work proposed until accepted. Keep floated ideas tentative. Use the project's supported tracker interface if tracking is in scope.
5. Record remaining work in the project queue. Keep it separate from what the decision already accomplished.

## Try the example

Read examples/INPUT.md and examples/ledger.json. Prepare a new entry and an impact list. Check against examples/EXPECTED.md after authoring. Run examples/check.py to exercise valid and invalid source standing.

## Evidence and limits

The source checker reads files and reports findings. Source IDs and syntax alone do not establish that a source was read or correctly understood. Fresh-session behavior of this public adaptation remains unverified; examples and mechanical checks are supplied for receiving rehearsal.
