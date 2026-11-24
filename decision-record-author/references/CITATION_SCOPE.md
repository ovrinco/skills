# Citation-check scope

The checker retains the installed method's line-oriented Markdown and OD-date-ID parser. Input ledger is JSON with an entries array or a top-level array. Each entry has id and source. Supported direct-source conventions are voxtype locators or chat locators with a full session UUID. The optional register contains Markdown R-prefixed IDs.

Pass explicit files and a ledger. Numbered Markdown result rows keep standing and source in their final cell. Unknown decision IDs, stated rows resting on a reading, and stated rows lacking a supported direct source are findings. The tool reads and reports; it appends no ledger entry.

The checker does not verify source truth, user authority, source reachability or concurrent write safety. A generic file reference can be preserved in a decision entry, but it is not automatically classified as an authoritative stated source by this checker. Review that case through the project's actual source rules.
