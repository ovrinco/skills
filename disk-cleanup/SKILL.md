---
name: disk-cleanup
description: Explain actual disk holders and prepare measured, source-preserving cleanup choices.
---

# Disk account and cleanup choices

Start with the user's selected scope and existing audits. Recover completed work before measuring again. For a whole-drive request, identify current filesystem/mount capacity, large holders and snapshots, then drill largest-first. For selected files, stay within that selection. Private stores get aggregate sizes unless content access is expressly authorized.

Measure what the numbers mean. Logical file bytes, allocated references and exclusive physical extents are different. On compressed or reflinked storage, a large folder sum can greatly exceed disk capacity. Never add parents and children, aliased inodes or shared extents as independent recovery. If exclusive bytes cannot be established, label that uncertainty. Read-only filesystem/FIEMAP evidence and a documented compression sample may support an estimate; a stale compression multiplier does not.

Explain why each large holder exists: authored source, unique records, generated builds, dependency caches, release versions, original media or repeated imports. Check actual consumers through current release records and readable process cwd/exe/fd/maps. A path name, age or historical STOP/CLOSE file alone cannot prove disposability. Verify rebuild dependencies, cost, licenses and offline availability. An in-use or unresolved item stays conditional while independent investigation continues.

For duplicate candidates, establish retained-copy identity using device/inode and complete matching content. Record size, timestamps, traversal completeness and relevant aliases. Equality proves redundancy, not independent physical recovery. Preserve originals, unique work, accepted evidence and native histories. An old removal approval carries no fresh authority.

Deliver a readable holder account and the actual class decision table described in references/decision-table.md. Give separate disjoint proposed/conditional/optional totals, with each row's size basis and retained/rebuild route. Do not make unchosen games or models the proposed total. Unpriced holdings remain visible. A page already shown is immutable; bind a new version's exact subordinate identities and hashes. Organization moves need a separate proposal.

This skill prepares evidence and choices. Deletion, trash, moves, cache eviction and executor runs require the user's separate concrete instruction. Keep read-only measurement finite and low priority; price temporary/output bytes before a large scan. A partial scan remains partial.

The bundled invented dataset in examples/INPUT.md can be answered without inspecting a real drive. It tests shared-space reasoning, current consumers and a useful proposal. No removal executable is supplied. First-party method and synthetic examples are Apache-2.0.
