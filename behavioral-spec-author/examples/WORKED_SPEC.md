# Example title editor specification
Source: examples/INPUT.md and OUTCOME.md, synthetic example.
Result lines 1 and 2, stated teaching requirement.

## States
| ID | State and entry | Visible content | Action | Exit |
| --- | --- | --- | --- | --- |
| S1 | First open, no data | Empty field | Type title | S2 |
| S2 | Edited title | Typed value | Save | S3 |
| S3 | Save pending | Saving | Wait | S4 or S5 |
| S4 | Save accepted | Saved title | Edit | S2 |
| S5 | Save rejected or load failed | Error words, retained input | Correct or retry | S2 or S3 |

## Values
| ID | Engine value | Visible words |
| --- | --- | --- |
| V1 | empty title rejection | Enter a title |
| V2 | unavailable stored state | Unable to load notes |

## Inputs
| ID | Input | States | Effect | Failure |
| --- | --- | --- | --- | --- |
| I1 | Type | S1 S2 S5 | Update draft | Keep existing saved state |
| I2 | Save | S2 S5 | Validate and save | Preserve prior saved title |

## Never
| ID | Expectation | Source |
| --- | --- | --- |
| N1 | A rejected save preserves prior saved content | OUTCOME.md result 2 |

## Open
Exact loading animation is an attributed design choice awaiting its owner.
