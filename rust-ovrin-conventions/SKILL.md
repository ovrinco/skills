---
name: rust-ovrin-conventions
description: "Apply concrete Rust errors, thin-front architecture, dependency and receiving-build conventions while preserving the project’s behavior."
---

# Rust engineering conventions

Read the crate's manifest, toolchain, error types, entry points and callers before changing Rust source or Cargo metadata. Preserve existing behavior and the receiving project's conventions. This edition provides engineering criteria and public examples with machine configuration chosen locally.

## Typed errors
Expose a typed library error and result alias. Include useful context without leaking private input. Convert foreign errors once at a boundary and return nonzero for a failed CLI operation. A top-level application wrapper can be appropriate; avoid turning every internal failure into an unstructured string.

Validate external input rather than unwrapping it. An expect names an invariant established by the code. Preserve error structure across frontend boundaries so every caller can report the same failure.

## Dependencies
Explain what a new crate/feature supplies that existing code lacks. Consider the standard library, direct implementation size, transitive cost, maintenance and license compatibility. Preserve manifest style and a locked receiving build.

Pin the supported toolchain where appropriate. Offline builds need supplied or cached dependencies. Fresh-machine releases need documented acquisition or vendoring. A missing authorized dependency is a concrete prerequisite to resolve.

Forbid unsafe code when practical. Where needed, document the invariant at the boundary and check the affected callers.

## Library and fronts
The library owns formats, persistence, queries and product rules. CLI, terminal, server and GUI fronts call it. Add a needed core operation to the library with behavior checks, then keep each frontend thin.

One package and a workspace can both work. Follow actual requirements. Optional feature flags should not conceal the supported basic path. Avoid a new async runtime or framework without a demonstrated product reason.

The dependency-free examples/thin-front crate shares input validation and typed errors between its library and CLI. references/FRONTENDS.md explains optional application boundaries.

## Meaningful tests and review
Keep unit tests near the implementation and behavior checks at public boundaries. Scratch state lives in temporary folders, separate from installed user data. Check invalid input, retries, interruption/recovery and callers' preserved behavior where relevant. Do not mirror implementation merely to increase assertions.

Before sealing use the project's formatter, clippy and required tests on the selected toolchain. Record commands and environment. Compilation alone does not prove GUI workflow or every runtime branch. Review findings identify concrete file/line evidence in the assigned scope, ordered by impact.

## Build ownership
Use a shared project target when concurrent work would duplicate expensive outputs. Coordinate its owner and lock, CPU/disk budget and resource caps. Reuse accepted build artifacts for downstream checks and price independent copies. Release optimization is for the actual artifact/performance proof.

Toolchain paths, CPU affinity and thermal thresholds are host settings. Follow actual host protections while independent source work continues. The receiving project chooses its dependencies and authorized fetching policy.

Run python3 tests/smoke.py to compile the sample with installed rustc, exercise valid/invalid CLI behavior and run its library tests.
