---
name: skill-proof
description: "Test an agent skill through fixed trigger, neighboring and boundary cases in fresh authorized sessions."
---

# Behavioral proof of an agent skill

A skill's behavior is established by actual use on fixed cases. Keep the expected answer and criteria fixed before a fresh runner sees the request. Record the exact skill hash, model configuration and observations.

## Scope and authority

This method evaluates task skills. Editing skill wording, source review and proving a product use their own checks. Changes to global authority, accounts, memory or security policy require their own authorized review. A routing test does not grant that authority.

The caller names the skill version, supported harness, runner model/effort, allowed tools, spending/resources and writable case areas. Separate the case author/judge from the fresh runner. Keep criteria and unrelated live project context out of the runner's inputs.

If fresh sessions are unavailable or unauthorized, write a preparation result with that limitation. A prepared test file or an author's judgment cannot stand in for an observed behavioral run.

## Fix the cases before running

Use templates/CASES.md. Include a must-trigger request and a neighboring request that should be handled without this skill. Include a meaningful boundary case when the role should stop or hand off. Add a case for each important known failure.

Use a small working public project or another authorized real task. A synthetic fixture can exercise mechanics, and must be identified as such. Stable on-disk inputs and reset steps make a case repeatable. Do not fabricate a claimed observation.

For each case record its identity, kind, exact request, model configuration, required input state, how it will be restored, what can be supplied if clarification is needed and the appropriate owner. Keep the request natural; it should not name the skill unless that is the real use case.

## Fix the criteria separately

Use yes/no criteria observable in the runner's log and files. Derive them from the declared job and boundaries. A borderline remains unproven.

Specify the correct answer before the run where correctness is part of the test. Must-trigger cases check skill loading, output completeness and scope. Neighbor cases check that the skill remains unloaded and the task is still handled. Boundary cases check that the correct handoff or stop occurs.

Keep criteria hidden from the runner. Do not adjust them during the case to make the result pass.

## Run with fresh state

1. Make one isolated case area per case/model. Put the candidate skill at the supported harness discovery path, with required support files and actual input assets.
2. Keep unrelated private project state and other case outputs unavailable to the runner. Preserve normal neighboring skills when their routing is part of the test.
3. Start a fresh authorized session with the exact request. Set model and reasoning configuration explicitly. Record harness version and selected scope.
4. Keep concurrent work within the caller's declared capacity. A runner does not launch additional sessions unless the task explicitly permits it.
5. Record evidence that the intended SKILL.md was loaded, the files it read/wrote, commands it ran and the resulting artifact.
6. Close the owned session, retain its log, and restore the case state by the authorized preservation procedure.

The public package supports file-based preparation and a harness-neutral run record. The actual session launch command is supplied by the user or harness adapter; no paid or model call is hidden in these scripts.

## Judge and preserve

Use templates/RESULTS.md. Each row records date, skill hash, harness/model/effort, case, each criterion, session/evidence and result. A behavioral pass requires every required criterion and case on the named bytes. Older bytes and an unrun model have their own status.

On failure, record the exact observation. Make a bounded change with its reason, then rerun affected cases plus the full fixed set before claiming the modified version passed. Preserve baseline results. Keep the caller's retry budget explicit.

Develop a candidate copy, validate it and install only within the caller's authorized update boundary. Keep previous bytes and the hash/results trail.

## Try the example

Read examples/INPUT.md and prepare the case areas using the templates. Keep examples/EXPECTED.md from the runner. examples/check.py checks the structure and hash record of the synthetic preparation fixtures without launching a model.

## Evidence and limits

Historical internal proof does not certify this adapted public text. Receiving checks prove the files and preparation format work. Fresh-session trigger, neighbor and boundary runs remain to be recorded on the exact public hash.
