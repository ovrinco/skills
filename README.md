# OVRIN Skills

These are working methods for people who build with agents. Each directory pairs a readable procedure with examples, fixtures, or scripts that show what a good result looks like. Pick a skill for the work in front of you. The collection has twenty adapted methods and integrations, plus a compact introduction to coordinating contributors.

## Start with one handoff

Imagine handing an unfinished parser to someone who has never seen it. They need to know what the input looks like, which file to open, and how to tell whether their change worked. Open the [hand-off method](hand-off/SKILL.md), then compare the [state of play](hand-off/examples/STATE.md), [work brief](hand-off/examples/BRIEF.md), and [blocker report](hand-off/examples/BLOCKER.md) for the same example. Each gives its reader a different next action.

## Find a skill

| When you need to… | Reach for |
| --- | --- |
| Define a result someone can observe | [Charter author](charter-author/SKILL.md) |
| Specify how a screen behaves | [Behavioral specification](behavioral-spec-author/SKILL.md) |
| Carry a design decision across revisions | [Design stage](design-stage/SKILL.md) |
| Record a decision and trace what it changes | [Decision record](decision-record-author/SKILL.md) |
| Turn a transcript into cited actions and questions | [Voice-note ledger](voice-note-ledger/SKILL.md) |
| Export a conversation and cite its turns | [Chat distillation](chat-distill/SKILL.md) |
| Give another session enough context to continue | [Hand-off](hand-off/SKILL.md) |
| Commission research that will resolve a decision | [Deep research prompt](deep-research-prompt/SKILL.md) |
| Study another implementation at a pinned revision | [Pattern mining](pattern-mine/SKILL.md) |
| Coordinate contributors around one demonstrable outcome | [Swarm campaign](swarm-campaign/SKILL.md) or the shorter [coordination primer](swarm-core/SKILL.md) |
| Give a Rust tool several entry points to one implementation | [Rust conventions](rust-ovrin-conventions/SKILL.md) |
| Keep independent acceptance cases out of builder materials | [Holdout extraction](holdout-extract/SKILL.md) |
| Check the delivered product as a user would | [Verifier](verifier/SKILL.md) |
| Evaluate whether a skill works across fresh cases | [Skill proof](skill-proof/SKILL.md) |
| Explain disk use and prepare a reviewable cleanup list | [Disk cleanup](disk-cleanup/SKILL.md) |
| Back up a project and verify its restoration | [Project backup](project-backup/SKILL.md) |
| Inspect or extend a tracker workbook | [System tracker](system-tracker/SKILL.md) |
| Resume an interrupted task using scoped evidence | [Zeno continuity](zeno-continuity/SKILL.md) |
| Control a supported LANCOOL lighting configuration | [RGB hardware profile](ian-lights/SKILL.md) |
| Work through the guarded OmaWhatsApp bridge | [OmaWhatsApp integration](omawhatsapp/SKILL.md) |

## Try one on your own material

Read the chosen procedure and its example first. For a first trial, use an invented input, give a fresh session the instructions and supporting files it needs, and keep expected results aside until the session finishes. For a script-backed skill, use its included checks to inspect what the software actually does. A passing parser test, backup restoration, or workbook readback answers a different question than a new model applying the whole method.

Two companion skills used on Omarchy are maintained upstream. The installed instructions matched the pinned v4.0.3 sources for [desktop customization](https://github.com/basecamp/omarchy/tree/0534987009061cbe2dacdde4ad564092ab698d12/default/agents/skills/omarchy) and [crash diagnosis](https://github.com/basecamp/omarchy/tree/0534987009061cbe2dacdde4ad564092ab698d12/default/agents/skills/diagnose-crash).

**[Explore OVRIN Labs](https://ovrinlabs.ca/)** · [Citium research](https://citium.ovrinlabs.ca/) · [Zavent data tools](https://zaventdata.com/)

[First-party license](LICENSE) · [RGB dependency notices](ian-lights/THIRD_PARTY.md) · [OmaWhatsApp source and licensing](omawhatsapp/SOURCE_STATUS.md) · [Contributing](CONTRIBUTING.md) · [Private security reports](SECURITY.md)
