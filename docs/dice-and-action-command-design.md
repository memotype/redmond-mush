# Dice And Action Command Design

This document is a design draft for Redmond's first dice and action-command
slice. It is intentionally implementation-oriented, but it does not yet
commit the project to a specific parser or full rules inventory.

## Purpose

Redmond should feel like a Shadowrun MUSH, not a generic dice calculator.

That means players should usually express intent in domain terms such as
casting, attacking, summoning, sneaking, or resisting, while the server maps
that intent onto deterministic rules code and dice-pool resolution.

The design goal is to support both:

- action-first commands that feel natural in play
- a smaller generic roll surface for staff tools, debugging, and edge cases

## Current Repository Reality

The current Redmond command layer is still minimal.

- `commands.command.MuxCommand` provides the Redmond-aware MUX command base.
- `commands.default_cmdsets` wires the default account and character cmdsets.
- `commands.prompt.CmdPrompt` is the main existing example of a repo-owned
  command.
- No repo-owned dice, casting, combat, or chargen commands are implemented
  yet.

This document therefore defines the intended shape of the first gameplay dice
slice rather than documenting existing behavior.

## Design Principles

### 1. Action-first player experience

The normal player-facing surface should center on what the character is doing,
not on raw pool arithmetic.

Good:

```text
cast stunbolt 5
cast invisibility 3 on nyx
shoot ganger
attack ganger with katana
summon fire spirit 6
assense nyx
soak 4
```

Less preferred as the primary surface:

```text
roll 12
roll 14 vs 4
roll 10 threshold 3
```

### 2. One shared deterministic engine

Even when commands differ at the syntax level, they should all resolve
through a shared rules boundary.

Preferred flow:

```text
command input
-> parsed player intent
-> rules test request
-> dice engine
-> structured result
-> player-facing presentation
```

This keeps command parsing, rules math, and text presentation from collapsing
into one monolithic command class.

### 3. Generic rolls still matter

A generic `roll` command remains useful for:

- staff adjudication
- debugging and test harnesses
- temporary gameplay coverage before a domain command exists
- corner cases where a custom action verb is not worth adding yet

The generic roll surface should exist, but it should not define the overall
tone of gameplay.

### 4. Incremental grammar over freeform NLP

The first parser should be compact, explicit, and MUSH-friendly.

Avoid trying to support broad natural language such as:

```text
cast force 5 stunbolt at nyx with edge and reagents
```

Prefer small stable grammars that can grow safely:

```text
cast <spell> <force>
cast <spell> <force> on <target>
attack <target>
attack <target> with <weapon>
roll <pool>
```

### 5. Rules logic stays server-side and testable

`APP.md` already requires deterministic server-side rules logic. Dice,
thresholds, opposed tests, drains, and derived summaries should resolve in
Python code with test coverage rather than in command text.

## Command Surface Model

The design uses three command tiers.

## Tier 1: Generic roll commands

These are the lowest-level user-visible commands.

Example syntax:

```text
roll <pool>
roll <pool> vs <opposed_hits>
roll <pool> threshold <threshold>
roll <pool> limit <limit>
roll <pool> threshold <threshold> limit <limit>
```

Possible later additions:

```text
roll <pool> +<modifier>
roll <pool> -<modifier>
roll <pool> /edge
```

Tier 1 should remain intentionally narrow. It is not meant to model every
Shadowrun action directly.

## Tier 2: Domain action verbs

These should become the normal player-facing interface for common gameplay.

Early candidates:

- `cast <spell> <force>`
- `cast <spell> <force> on <target>`
- `attack <target>`
- `attack <target> with <weapon>`
- `shoot <target>`
- `shoot <target> with <weapon>`
- `summon <spirit> <force>`
- `assense <target>`
- `soak <incoming_damage>`
- `resist drain`

These verbs let the player specify the tactical choice that matters in play:

- which spell
- which force
- which target
- which weapon
- which named action

The server should infer or compute the dice pool and other consequences from
character state, equipped gear, spell metadata, and future situational
modifiers.

## Tier 3: Advanced command modifiers

MUSH-style switch or modifier syntax should remain available for compact
advanced control, but only after the basic command surface is stable.

Examples:

```text
cast stunbolt 5 /reckless
shoot ganger /called
roll 12 /edge
```

This tier is optional for the first implementation slice.

## Proposed Internal Boundaries

The design should eventually separate the following concerns:

- command parsing
- rules-test request construction
- dice rolling and hit counting
- result evaluation
- player-facing text rendering

An implementation-friendly model would look roughly like this:

```text
commands/
  roll.py
  magic.py

world/
  or rules/
    dice.py
    tests.py
    magic.py
```

The exact module names can be adapted to the current Evennia directory shape,
but the behavior split should remain clear.

## Proposed Result Shapes

Even before the full rules catalog exists, the dice layer should return
structured results rather than ad hoc strings.

Example conceptual fields:

- `pool`
- `hits`
- `ones`
- `glitch`
- `critical_glitch`
- `limit`
- `applied_hits`
- `threshold`
- `success`
- `opposed_hits`
- `net_hits`
- `rolled_values`

Not every player-facing command must display every field, but the engine
should preserve them so tests and higher-level actions can use them.

## Shadowrun-Specific Expectations

The first dice system should feel compatible with common Shadowrun play habits:

- d6 pool rolling
- hit counting on 5s and 6s
- glitch and critical glitch reporting
- threshold tests
- opposed tests
- optional later support for limits, Edge, drain, soak, and initiative

The MVP does not need to implement the full Shadowrun action catalog.
However, the first slice should avoid boxing the project into a generic RPG
roller that will feel awkward once casting, combat, and drain are added.

## Presentation Guidance

Output should be terse, readable, and MUSH-friendly.

Example result style:

```text
Spellcasting Test: Stunbolt at Force 5
Pool 12 -> 4 hits
Drain pending.
```

Or for a generic roll:

```text
Roll 12 -> 4 hits
Glitch.
```

Presentation rules:

- keep the first line action-oriented when the command is action-oriented
- expose raw pool values when useful, but do not force the player to supply
  them directly for common domain verbs
- keep output short enough for regular telnet or MUD-client play
- preserve enough structure that logs and tests can assert on behavior

## MVP Recommendation

The first implementation slice should be intentionally small:

1. deterministic dice-pool engine
2. generic `roll` command
3. one real action-first command, preferably `cast`

Why `cast` first:

- it proves the action-first command model
- it exercises named actions rather than raw pool-only input
- it gives Redmond a distinctly Shadowrun-flavored command early
- it creates a natural future seam for drain resolution

Suggested first grammar:

```text
roll <pool>
roll <pool> threshold <threshold>
cast <spell> <force>
cast <spell> <force> on <target>
```

The initial `cast` command can use placeholder spell metadata if needed, as
long as the placeholder interface is explicit and testable.

## Deliberate Non-Goals For The First Slice

Do not try to solve all of these in the first implementation:

- full spell catalogs
- full combat resolution
- initiative passes
- Edge action complexity
- freeform English parsing
- full situational modifier systems
- chargen-derived final balance tuning

Those can layer on top of a sound command-plus-engine foundation.

## Open Design Questions

The next design review should settle:

1. whether the first public-facing command should be `cast` or another verb
2. whether limits appear in the MVP or wait for a later slice
3. whether generic `roll` should be character-only, staff-only, or available
   to all logged-in users
4. how much raw roll detail should be exposed in ordinary command output
5. whether advanced switches such as `/edge` should be designed now or only
   after the basic verbs land

## Recommended Next Step

After review, convert this document into a narrow implementation plan for:

- one dice-engine module
- one generic roll command
- one action-first `cast` command
- deterministic unit and command tests
