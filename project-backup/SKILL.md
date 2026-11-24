---
name: project-backup
description: Make a bounded, verified project checkpoint with a clean restore proof.
---

# Project backup

Read the requested project's source and actual changes. Identify unique source, uncommitted work, manifests, lockfiles and required restore assets. Distinguish an application checkpoint from a data backup. Explain large original-data contributions before choosing scope. A whole home, archive, run collection or campaign tree requires a specific project selection before inventory.

Use the bundled scripts/project_backup.py. It inventories first, then streams one compressed tarball without a full staging copy. Defaults cap selected input at 4 GiB, files at 100,000 and compressed output at 2 GiB. Narrow generated or duplicated content if those caps are exceeded. Any genuinely larger operation requires explicit size/scope authorization. Exclude generated targets, caches, copied workspaces and downloadable weights while retaining original user material.

Supply sources.json with deliberate named roots. For example, {"application":{"path":"/selected/project","exclude":["test-output"]}}. Run plan --sources sources.json --out plan.json, review the inventory, then create --plan plan.json --name project --base-dir /new/checkpoint-directory. Choose a new private output directory. The archive contains a manifest and restore notes; verify both per-file content and the outer checksum.

For a version checkpoint sharing a data baseline, provide an explicit baseline JSON via plan --shared-data. Its archive and manifest hashes and protected roots must be verified. Never refresh a data baseline merely because the application changed. Use a consistent database snapshot or quiescence; account for WAL. Symlinks are stored as links and remain unfollowed except an explicitly selected resolved top-level root.

Changed source invalidates a plan. A partial archive is failure evidence. Stop the exact owned writer before addressing its generated artifacts. Restore for proof into a new directory and compare selected content; replacing live state requires its own explicit instruction. Report artifact size, verified files, exclusions and restore limits.

Read examples/INPUT.md and perform its checkpoint using the bundled helper. Compare with examples/EXPECTED.md. Run python3 scripts/test_project_backup.py for the real synthetic regression suite. Python 3.11 or newer is required. First-party helper and examples are Apache-2.0 under the repository license.
