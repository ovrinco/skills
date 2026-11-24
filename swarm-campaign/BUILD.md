# Software joins

Start with the supported entry journey. Identify ownership of persisted state and the exact producer/consumer formats, failures, retry and cancellation semantics. One owner can specify, implement and self-check a coherent capability. Integration checks should use the actual shared library and public entry point.

Build once per accepted source batch where practical. Keep scratch state separate from installed data. Test persistence, interruption and version errors that can break the intended workflow. Install only when authorized, preserving previous executable and data rollback information. Independent proof uses the installed or delivered artifact, not a mock that hides the join.
