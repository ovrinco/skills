# OC-01 Example outcome

## Outcome (F1)
A user can save a nonempty note title and receives a clear rejection for an empty title.

## Proof (F2)
1. Save a valid title and observe it retained. Result lines 1.
2. Submit an empty title and observe rejection with existing data unchanged. Result lines 2.

## Results (F3)
| # | Result | Standing and source |
| --- | --- | --- |
| 1 | A nonempty title is retained. | stated OD-2026-01-01-01 |
| 2 | An empty title is rejected without changing a saved title. | stated OD-2026-01-01-01 |

## Not done if (F4)
An empty title is silently accepted, or the rejection changes the saved record.

## Grace (F5)
Internal storage format can be chosen by the implementer.

## Ownership boundary (F6)
The editor owns this behavior. Synchronization has separate ownership.

## Dependencies (F7)
The supported local editor entry point.

## Work and roles (F8)
Specify behavior, derive visible tests, implement, then independently observe the two result lines.
No account or global settings changes are authorized.

## Status (F9)
Synthetic example requirements. Implementation and independent observations are pending.

## Sources (F10)
OD-2026-01-01-01 in ledger.json is synthetic teaching input.
