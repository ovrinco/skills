# Atlas cleanup discussion

The filesystem uses 120 GB of 200 GB. The target's 40 GB of logical references is an inventory locator. Supplied extent evidence identifies 24 GB exclusively held compressed data plus 8 GB shared with a retained worktree. That accounts for 32 GB of distinct known physical extents, leaving 88 GB of filesystem use to explain with the other holders and metadata. The media/original/rollback sizes have no exclusive compressed-allocation proof, so they cannot complete the physical account by simple addition.

| Class | Standing | Physical return | What remains and cost |
| --- | --- | --- | --- |
| Generated target leaf | Proposed for the user's choice | 24 GB from supplied exclusive-extent evidence | Source, lock, toolchain and retained worktree remain. Rebuild takes 10 minutes. |
| Duplicate media name | Keep one name; optional name tidy | 0 GB while the retained hardlink references the inode | The 15 GB inode stays reachable. Removing a second name is not new physical recovery. |
| Older release | Conditional, still held | Unpriced | The live rollback consumer must be retired or replaced by a verified recovery route before removal is proposed. |
| Unique original records | Preserve | Unpriced | No retained copy or rebuild route is supplied. |

The priced proposal totals 24 GB. Conditional physical savings are unmeasured. Recover the generated target first if the user chooses, because its present consumers and rebuild route are resolved. A new measurement should bind selected paths, device/inode, times and extent basis into the exact proposal version. The present table uses supplied synthetic evidence and authorizes no deletion. Original records and rollback remain preserved.
