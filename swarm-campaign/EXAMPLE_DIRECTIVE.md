# Orchard valve parser

## Orientation
Deliver a parser that returns timestamp and valve state for the supplied sample.

## Requirements
Serve requirement parse-state in examples/pack/requirements.json exactly as recorded.

## Inputs
The frozen requirements file and its SHA-256 in pack.json; the existing accepted source if present.

## Writable scope
Project-relative monitor.py. A separate assignment owns docs/usage.md.

## Work
Implement the parser, validate required fields and preserve earlier observations after invalid input. Use the supported normal entry point.

## Resources
Local CPU-only work and temporary test data. Agent execution is released only by its user's task authority.

## Acceptance
Parse the valid sample and demonstrate the missing-timestamp error with unchanged prior state.

## Output
monitor.py and the actual command/result evidence.

## Recovery
Repair routine failures. Report an unavailable indispensable producer and continue independent work.
