---
name: chat-distill
description: "Export one authorized Claude Code or Codex session with native parsing, source hashes and masking; optionally verify a cited distillation."
---

# Chat export and distillation

Use when the user requests a session export or a source-cited distillation. Read one identified session per invocation. Normal file summaries need only the supplied file.

## Selection and export
Prefer an explicit --source PATH. Optional selectors are --session-id, --match and --latest --provider claude|codex. Latest can identify another pane. Resolve ambiguity before reading a private source.

Run python3 scripts/export_chat_log.py find --source SOURCE. Then export with python3 scripts/export_chat_log.py export --source SOURCE --out-root OUTPUT. The default is ./chat-output. Native histories remain read-only and output beneath the native .claude/.codex roots is refused.

The exporter supports the native JSONL shapes demonstrated in examples/claude.jsonl and examples/codex.jsonl. It writes export.md and record.json with source identity, bounded byte hash, counts and whether the source changed while being read. Visible user turns receive U indexes and assistant turns receive A indexes. Mid-task user messages and compaction boundaries are retained. System/hidden/tool payloads are excluded; --work-log adds name/target summaries.

Credential patterns are masked before output. Inspect masking counts and the artifact before sharing because unusual secrets may escape pattern matching. Existing output is refused. --replace preserves an older export aside before replacing it. A native format yielding zero turns needs investigation; do not deliver a misleading empty artifact.

## Requested distillation
Only create essence.md when requested. Cover decisions, corrections, implemented work and unresolved questions. Preserve stated versus tentative standing. Every item cites its U/A source turns. Summarize the relevant content without copying user statements or introducing personality judgments.

Run python3 scripts/check_essence.py EXPORT ESSENCE. It validates citation existence, item citations, length, copied eight-word runs and tone headings. Review the source again for substantive completeness and claims beyond the evidence. A project-specific terminology dictionary is optional.

## Proof and delivery
Run python3 tests/smoke.py to exercise synthetic Claude/Codex export, masking, source preservation and essence checks. No actual conversations are bundled. Report output path, visible turn counts, source revision/hash and limitations. Export-only requests finish with the export.
