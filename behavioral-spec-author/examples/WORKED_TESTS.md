# Example visible tests
Synthetic authored reference. No independent model derivation is claimed.

| Spec ID | Given | Do | Expect |
| --- | --- | --- | --- |
| S1 | Fresh editor | Open | Empty title field |
| S2 | Empty field | Type a valid title | Visible draft |
| S3 | Draft | Start save | Pending state |
| S4 | Valid title | Complete save | Saved title |
| S5 | Prior saved title | Submit invalid title | Error with prior saved title unchanged |
| V1 | Empty input | Save | Enter a title |
| V2 | Load unavailable | Open | Unable to load notes |
| I1 | Draft | Type | Updated visible draft |
| I2 | Prior saved title | Save invalid value | Prior saved state retained |
| N1 | Prior saved title | Reject save then reopen | Same saved title |

Loading animation is waiting on the design source.
