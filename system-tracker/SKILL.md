---
name: system-tracker
description: Inspect or safely extend a workbook from its current structure and declared record authority.
---

# Tracker and workbook inspection

Determine which artifact is authoritative before writing. A workbook may be an export or a user's live record. If a database-backed tracker CLI is declared authoritative, read/write through that supported interface and treat workbook copies as exports. Never infer permission to alter the source of truth from a request to inspect an export.

The bundled scripts/xlsx_dump.py and scripts/xlsx_insert_rows.py are real stdlib tools for a bounded XLSX subset. Python 3.11 or newer is sufficient. Run the dump on the chosen workbook first to discover sheet names, table ranges and columns, then dump the relevant sheet/table. Use the current headers and field meanings. Claims of verified status require actual evidence.

For an authorized edit on a copy, use xlsx_insert_rows.py SOURCE --sheet TAB --insert '{"before":3,"values":{"A":"new","B":"example"}}' --out NEW.xlsx. The before row must exist. It inherits the template row's column/style structure and adjusts rows, merges, conditional ranges and known table/filter ranges. Formula cells, shared-string templates and dependent cross-sheet references are guarded restrictions. Use an explicit fresh output path. Keep the source bytes intact, including through symlink aliases.

Reopen the output ZIP/XML, discover and dump again, compare neighbors and relevant references, then reopen through LibreOffice when claiming office interoperability. A successful command alone is incomplete evidence. Refusal means choose a supported edit or a documented application workflow. Do not silently replace formula or shared-string content.

The real tracker database adapter is an external project dependency, not supplied by these XLSX utilities. Configure any such adapter from the target project's own documented contract. This public skill deliberately carries the generic inspection and guarded-copy tools rather than private database state or house field vocabularies.

Run python3 examples/check.py for invented XLSX insertion/inline-string/table-range/source-preservation and invalid-formula checks. Read examples/INPUT.md before doing the example. First-party helpers and examples are Apache-2.0.
