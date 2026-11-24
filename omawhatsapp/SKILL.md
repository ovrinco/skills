---
name: omawhatsapp
description: Operate an installed guarded WhatsApp bridge with explicit authorization and private-data boundaries.
---

# OmaWhatsApp integration

Use the supplied runtime/omawhatsapp.py bridge with its runtime/omawhatsapp_assets.py sibling, or a verified compatible installation. The local snapshot identifies the wacli parity registry as 0.17.1. It requires an independently installed supported wacli binary for real operations; neither a linked account nor wacli is included. Set WACLI_BIN explicitly for a receiving installation.

Check a user's requested operation against the actual helper capabilities. Focused local chat commands keep normal work inside the indexed DM/standalone-group boundary. Advanced calls use the guarded wacli registry; future unknown commands fail closed. The presence of a command in the registry is not evidence of a successful runtime operation.

Local reads, remote reads, sync, account linking, mutations, private exports and external streams are separate authorization classes. Obtain the class from the actual request. Resolve exact targets before mutation. An uncertain send must not be retried automatically. Opening a chat does not grant a read receipt or a change to privacy preferences. Honor offline mode and never create a real test write.

All account stores, message bodies, JIDs, media, event streams and raw status are private. Keep them out of repositories, issue reports and screenshots. Project status to only the fields needed. Do not read session.db or write wacli.db directly. A filesystem export needs its exact authorized destination; repository exports carry a second explicit boundary.

Read references/operations.md and references/wacli-parity.md for the actual focused and advanced contracts. The public adaptation uses the configured helper path instead of an operator home path. Runtime failures are reported honestly, including partial completion. Do not change sync preferences, upgrade the helper or link an account merely to complete a read request.

Run python3 examples/check.py for real registry/argument/authorization refusals on invented inputs with subprocess calls prohibited. This proves bounded guard behavior only. Actual linking/sync/send/receipt/media flows require separately authorized runtime checks on the receiving installation.

The runtime source is byte-identical to pinned upstream OmaWhatsApp v0.13.1 helpers, with MIT and third-party notices retained. SOURCE_STATUS.md records the exact commit and supported boundary. Keep the upstream grant and attribution distinct from the first-party instruction adaptation. First-party public instruction/example adaptation follows the repository license.
