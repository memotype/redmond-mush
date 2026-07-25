# Character Sheet and Chargen Architecture

## 1. Purpose

Redmond needs two related but distinct domains:

- a permanent character sheet that represents the authoritative current
  mechanical state of a character
- a chargen session that represents the mutable, versioned process used to
  build, validate, submit, review, and approve that character

This document defines the concrete persistence boundaries for those domains
before models, migrations, or commands are implemented.

## 2. Final Resolution

The permanent sheet and the chargen process are separate.

- `CharacterSheet` is the permanent authoritative mechanical state
- `ChargenSession` is the mutable chargen workflow

Normal player chargen does not write draft values into a permanent sheet.

Approval creates the permanent sheet atomically from the approved chargen
result.

This separation supports:

- abandoned drafts
- future rebuild or respec workflows
- staff-created or imported characters that do not use ordinary player
  chargen
- immutable historical chargen records even when newer rules profiles exist

## 3. Evennia Authority Boundary

Repository evidence continues to support Evennia as the authority for:

- character key or visible object name
- ordinary object description fields
- location
- movement
- sessions
- command attachment
- permissions and locks
- controlling account relationships
- in-world object behavior

The current seams for those fields are already visible in:

- `src/redmond_server/game/typeclasses/characters.py`
- `src/redmond_server/game/world/prompts.py`

The sheet domain should not duplicate those fields as ordinary mutable
source-of-truth state.

## 4. Core Model Boundary

Each playable Evennia character has:

- zero or one permanent `CharacterSheet` in the MVP
- zero or more `ChargenSession` records

```text
Evennia Character
  |
  +-- zero or one CharacterSheet
  |
  +-- zero or more ChargenSession records
          |
          +-- ChargenSkillSelection records
          +-- ChargenSpecializationSelection records
          +-- ChargenLedgerEntry records
          +-- validation snapshots
```

The permanent sheet and the draft session intentionally duplicate some
fields, especially core attributes.

That duplication is correct because the fields represent different lifecycle
states:

```text
mutable draft selection
  -> validation and approval
  -> permanent approved mechanical state
```

## 5. Permanent CharacterSheet

`CharacterSheet` represents the current approved mechanical state of a
character.

It owns or exposes:

- supplemental identity metadata not already authoritative in Evennia
- approved backstory text
- approved core attributes
- approved skills and specializations
- current mechanical resources kept in scope for the implemented slices
- later approved sheet domains such as qualities, contacts, and optional
  capability profiles
- authorized post-approval changes
- permanent audit history

It does not retain the mutable chargen workflow state.

### 5.1 Sheet identity fields

The sheet may store identity metadata such as:

- alias or street name
- pronouns
- metatype or ancestry
- archetype label
- short concept
- approved backstory
- staff-only notes
- schema version

The sheet should not make these ordinary fields authoritative:

- character name
- public description
- controlling account
- permissions
- location

### 5.2 Sheet status

The MVP permanent sheet states should be:

- `approved`
- `retired`
- `archived`

`unapproved` should be omitted from the MVP.

Normal player chargen creates an approved sheet atomically during approval.
Privileged staff import or manual creation should also create an approved
sheet, with a required actor, reason, source, and permanent audit event.

Every approved `CharacterSheet` must contain a valid backstory.

This applies to:

- ordinary chargen approval
- staff import
- manual staff creation

Privileged creation paths must not bypass permanent-sheet backstory
validation.

Staff import and manual staff creation should use the same normalization and
validation policy as player chargen backstory handling.

The status field is still useful in the MVP even though existence usually
implies approval.

Reasons:

- `retired` and `archived` are meaningful state transitions
- explicit status makes queries and future workflow extensions clearer
- approval metadata alone does not replace a domain status field once
  multiple post-approval states exist

## 6. ChargenSession

`ChargenSession` represents a versioned chargen attempt for one Evennia
character.

It owns:

- lifecycle state
- the immutable rules profile reference
- effective starting-budget snapshots
- current draft backstory
- current draft attribute selections
- current draft skill and specialization selections
- chargen ledger history
- live and persisted validation artifacts
- review notes and timestamps
- the link to the finalized permanent sheet after approval

### 6.1 Session states

Active states:

- `draft`
- `submitted`
- `changes_requested`

Final states:

- `approved`
- `abandoned`
- `superseded`

The MVP allows at most one active chargen session per Evennia character.

### 6.2 Backstory ownership

Backstory follows the same lifecycle boundary as the rest of chargen:

```text
ChargenSession.backstory
  -> submission and staff review
  -> CharacterSheet.backstory
```

Before approval:

- the authoritative backstory belongs to `ChargenSession`
- the player may edit it only while the session is `draft` or
  `changes_requested`
- the player may view it while the session is `submitted`, but may not edit
  it
- staff reviewing the chargen session may view it

After approval:

- the authoritative approved backstory belongs to `CharacterSheet`
- the exact reviewed text is copied during the same atomic finalization
  transaction as attributes, skills, and specializations
- ordinary players may not directly edit the approved backstory

The MVP should not add a separate backstory model or a separate
`backstory_status` field.

## 7. Authoritative Draft Selection Storage

The remaining ambiguity in the earlier design was that `ChargenSession` was
said to own draft selections, but the prior model list did not specify the
concrete storage for those selections.

That ambiguity is now resolved.

The authoritative current draft state is:

- a draft backstory text field on `ChargenSession`
- explicit attribute fields on `ChargenSession`
- normalized draft skill records in `ChargenSkillSelection`
- normalized draft specialization records in
  `ChargenSpecializationSelection`

The ledger is not the source of truth for current selections.

The permanent sheet is not created early merely to hold draft values.

### 7.1 Draft backstory

`ChargenSession.backstory` is the authoritative current draft backstory.

It should be planned conceptually as:

```text
ChargenSession.backstory
  Django TextField
  null=False
  blank=True
  default=""
```

with these intended behaviors:

- an empty string represents the absence of a draft backstory
- neither field should use `NULL` in the MVP
- may be blank while chargen is incomplete
- stores normalized `\n` line endings
- preserves paragraphs and meaningful internal line breaks
- removes unnecessary trailing blank lines before persistence
- rejects empty or whitespace-only text when saving or submitting
- enforces a maximum character length owned by the chargen domain rather
  than buried in a command implementation

The preferred MVP ownership for the maximum length is a named chargen-domain
policy constant or validation setting, not a magic number in a command and
not a budget-rule value in `ChargenRulesProfile`.

Reason:

- backstory length is product input policy rather than an immutable ruleset
  budget
- the repo's current architecture already separates workflow, validation, and
  presentation concerns
- a named domain limit can later move to a broader config surface without
  changing the ownership model

### 7.2 Shared backstory normalization and validation

Backstory write paths should use one shared domain-level operation,
conceptually:

```text
normalize_backstory(candidate_text)
```

This shared operation or policy should own:

- line-ending normalization to `\n`
- preservation of meaningful paragraphs and internal line breaks
- removal of unnecessary trailing blank lines
- rejection of empty or whitespace-only content
- maximum-length validation using the domain-owned backstory limit

The same operation or policy should be used by:

- player chargen backstory entry
- player draft replacement
- staff import
- manual staff creation
- any future authorized permanent-sheet backstory mutation

Normalization logic should not live in presentation code and should not be
duplicated separately in each command path.

### 7.3 Draft core attributes

`ChargenSession` should carry explicit draft fields for:

- `body`
- `agility`
- `reaction`
- `strength`
- `willpower`
- `logic`
- `intuition`
- `charisma`
- `edge`
- `magic`
- `resonance`

This is intentionally parallel to the permanent sheet.

These draft fields support:

- direct structural validation
- direct budget queries
- readable abandoned session state
- deterministic approval-time copy into the permanent sheet

### 7.4 Draft skills

`ChargenSkillSelection` should store the current selected skill state for one
session.

Suggested fields:

- foreign key to `ChargenSession`
- stable `skill_id`
- rating
- optional narrow metadata only if needed by the first supported rules

### 7.5 Draft specializations

`ChargenSpecializationSelection` should store the current selected
specialization state for one draft skill.

Suggested fields:

- foreign key to `ChargenSkillSelection`
- specialization identifier or display name

If the first supported slice does not yet implement specializations, this
model still belongs in the design and in the assigned implementation slice,
but the actual writable command surface may defer using it until skills are
in scope.

## 8. Permanent Approved Equivalents

Permanent approved data is stored separately from draft selections.

Approved equivalents are:

- approved backstory on `CharacterSheet`
- core attributes on `CharacterSheet`
- approved skills on `CharacterSkill`
- approved specializations on `CharacterSpecialization`

Approval deterministically copies materialized approved values from the
session domain into the permanent sheet domain.

`CharacterSheet.backstory` should be planned conceptually as:

```text
CharacterSheet.backstory
  Django TextField
  null=False
  blank=False
```

with these intended behaviors:

- neither field should use `NULL` in the MVP
- `CharacterSheet.backstory` must contain normalized, non-whitespace text
  when the permanent sheet is created
- `blank=False` is not by itself a database guarantee for a `TextField`
- the approval service must enforce the permanent backstory invariant
- ordinary permanent-sheet creation must not bypass this invariant

## 9. Immutable Rules Profiles

Each `(profile_key, version)` pair is an immutable rules definition.

Example:

```text
redmond_standard, version 1
redmond_standard, version 2
```

After any session references a profile version:

- its rules values must not be edited in place
- it may be marked unavailable for new sessions
- older sessions must continue to resolve against the exact referenced row

`ChargenSession` should:

- reference the exact immutable `ChargenRulesProfile` row
- snapshot the effective starting budgets used by that session

A separate numeric `profile_version_snapshot` is redundant in the MVP if the
foreign key already targets a unique immutable version row.

The MVP should snapshot actual effective values instead, starting with:

- `starting_karma_snapshot`

Do not build a universal budget abstraction before the rules require it.

## 10. Chargen Ledger Semantics

`ChargenLedgerEntry` is an append-only history of meaningful budget
mutations.

It records how the current build was assembled, but current selections
remain authoritative for the present draft state.

Examples:

- attribute purchase
- attribute refund
- skill purchase
- skill refund
- staff adjustment
- correction entry
- explicitly supported rules-based automatic adjustment

Ordinary operations should not edit or delete existing ledger entries.

Corrections should use compensating entries, for example:

```text
attribute purchase     -20 karma
correction refund      +20 karma
corrected purchase     -15 karma
```

Future repair tooling may append specially marked correction entries with:

- acting staff member
- required reason
- reference to the affected entry when useful
- timestamp

The initial design should not include an ordinary mechanism for rewriting
ledger history.

## 11. Validation Persistence

Live validation and persisted validation snapshots are different things.

### 11.1 Live validation

Ordinary validation is recalculated on demand from:

- the current draft backstory
- current draft selections
- current draft skill selections
- current draft specialization selections
- the immutable rules profile
- the session's effective budget snapshots

The player may inspect current validation errors at any time.

### 11.2 Persisted validation snapshots

A validation snapshot is persisted when:

- the player submits the session

The session is revalidated immediately before approval.

The approval audit event should record the approval-time validation summary,
result, or stable digest.

Any draft mutation after `changes_requested` invalidates the earlier
submission snapshot.

Old validation results are not authoritative after the draft changes.

### 11.3 Backstory validation

Submission validation must require a nonblank backstory.

Conceptually, the validation issue should look like:

```text
path: chargen.backstory
code: backstory_required
message: A character backstory is required before submission.
```

The backstory does not have its own separate approval flag.

Approval of the submitted `ChargenSession` approves the backstory together
with the mechanical build.

The stored chargen backstory should already be normalized before submission.

Approval should validate the stored value again.

Approval must copy the exact reviewed stored text.

Approval should not perform a new transformation that could make the
permanent text differ from what staff reviewed.

When staff requests backstory changes:

1. the session moves to `changes_requested`
2. review notes describe the requested revision
3. the player may replace the backstory
4. the previous submission-validation snapshot becomes stale
5. the complete session must be resubmitted

## 12. Final MVP Model List

Every proposed MVP model is assigned to an implementation slice.

### Models landing in Slice A

- `CharacterSheet`
- `CharacterSkill`
- `CharacterSpecialization`

### Models landing in Slice B

- no new persistence models

### Models landing in Slice C

- no new persistence models

### Models landing in Slice D

- `ChargenRulesProfile`
- `ChargenSession`
- `ChargenSkillSelection`
- `ChargenSpecializationSelection`
- `ChargenLedgerEntry`

### Models landing in Slice E

- no new persistence models

### Models landing in Slice F

- no new persistence models

### Models landing in Slice G

- `CharacterSheetAuditEvent`

### Models landing in Slice H

- `CharacterQuality`
- later contacts or capability-profile models as concrete scope requires

`CharacterQuality` is intentionally moved out of the earlier broad MVP model
list because the current implementation sequence does not need it to prove
the permanent-sheet and chargen boundaries.

## 13. Important Fields and Constraints

### 13.1 CharacterSheet

Suggested MVP fields:

- one-to-one to the Evennia character
- `status`
- identity metadata kept in scope
- `backstory`
- explicit core attribute fields
- stable special fields needed by the MVP:
  `edge`, `essence`, `magic`, `resonance`
- approval metadata:
  `approved_at`, `approved_by`
- `schema_version`
- timestamps

Suggested constraints and indexes:

- unique one-to-one relationship to the Evennia character
- index on `status`
- check constraints for non-negative or valid rating ranges where the first
  rules slice already knows them safely

The MVP should treat one sheet row per character as the normal invariant.

### 13.2 CharacterSkill

Suggested MVP fields:

- foreign key to `CharacterSheet`
- stable `skill_id`
- rating

Suggested constraints and indexes:

- unique on `(sheet, skill_id)`
- index on `(sheet, skill_id)`
- rating range check constraint when the first rules slice defines one

### 13.3 CharacterSpecialization

Suggested MVP fields:

- foreign key to `CharacterSkill`
- specialization identifier or name

Suggested constraints and indexes:

- unique on `(skill, specialization identifier or name)`
- index on `skill`

### 13.4 ChargenRulesProfile

Suggested MVP fields:

- `profile_key`
- `version`
- availability flag for new-session creation
- `starting_karma`
- timestamps

Suggested constraints and indexes:

- unique on `(profile_key, version)`
- index on `(profile_key, is_available_for_new_sessions)`

### 13.5 ChargenSession

Suggested MVP fields:

- foreign key to the Evennia character
- nullable foreign key to the finalized `CharacterSheet`
- `status`
- foreign key to `ChargenRulesProfile`
- `starting_karma_snapshot`
- `backstory`
- explicit draft core attribute fields
- explicit draft special fields in scope:
  `edge`, `magic`, `resonance`
- submission, review, approval, abandonment, and supersession timestamps as
  needed
- review notes field
- optional persisted submission-validation snapshot
- actor references for creation and review when useful
- timestamps

Suggested constraints and indexes:

- index on `(character, status)`
- index on `(character, created_at)`
- conditional uniqueness for one active session per character
- check constraints for valid draft rating ranges where safe to express in
  the first rules slice
- check constraint requiring `finalized_sheet` when `status = approved`

Intended text-field behavior:

- `ChargenSession.backstory` should be blank-allowed during draft work
- `CharacterSheet.backstory` should be populated by approval finalization
- neither field should use `NULL` in the MVP when an empty string cleanly
  represents absence
- command and service validation remain authoritative for enforcing the
  configured backstory length limit
- a later `TextField(max_length=...)` may document the intended limit, but
  it does not replace domain validation

### 13.6 ChargenSkillSelection

Suggested MVP fields:

- foreign key to `ChargenSession`
- stable `skill_id`
- rating

Suggested constraints and indexes:

- unique on `(session, skill_id)`
- index on `(session, skill_id)`
- rating range check constraint when known

### 13.7 ChargenSpecializationSelection

Suggested MVP fields:

- foreign key to `ChargenSkillSelection`
- specialization identifier or name

Suggested constraints and indexes:

- unique on `(skill_selection, specialization identifier or name)`
- index on `skill_selection`

### 13.8 ChargenLedgerEntry

Suggested MVP fields:

- foreign key to `ChargenSession`
- `entry_type`
- `budget_kind`
- section or category
- reference identifier
- signed amount
- reason
- acting account reference
- timestamp
- optional structured metadata
- optional reference to the corrected entry when the entry is a repair or
  compensation record

Suggested constraints and indexes:

- index on `(session, created_at)`
- index on `(session, budget_kind)`
- check constraint limiting MVP `budget_kind` to `karma`
- append-only behavior enforced by service policy and later narrow repair
  tooling, not by exposing general update operations

### 13.9 CharacterSheetAuditEvent

Suggested MVP fields:

- foreign key to `CharacterSheet`
- event type
- acting account reference
- acting character reference when relevant
- reason
- source
- previous value payload
- new value payload
- approval-time validation summary or digest when relevant
- timestamp

Suggested constraints and indexes:

- index on `(sheet, created_at)`
- index on `(sheet, event_type)`

## 14. One-Active-Session Constraint Strategy

The MVP should enforce at most one active chargen session per Evennia
character, where active means:

- `draft`
- `submitted`
- `changes_requested`

### 14.1 Database constraint

Use a conditional unique constraint on the Evennia character reference for
rows whose `status` is in the active-state set.

Conceptually:

```text
unique(character) where status in active_states
```

This is appropriate for both PostgreSQL and modern SQLite through Django's
conditional unique-constraint support.

### 14.2 PostgreSQL behavior

PostgreSQL can enforce the conditional unique constraint directly and also
supports row-level locking during transitions and approval work.

### 14.3 SQLite behavior

Modern SQLite can enforce the conditional unique constraint through a
partial unique index emitted by Django.

SQLite does not provide PostgreSQL-style row-level locking, so the service
layer must still:

- wrap active-session creation and status transitions in transactions
- expect integrity errors if two writers race
- retry or surface a clean domain error rather than assuming the pre-check
  alone is sufficient

### 14.4 Service-layer backstop

Regardless of backend, service logic must still:

- check for an existing active session before creating a new one
- treat the database constraint as the final backstop
- handle integrity errors deterministically

## 15. Atomic Approval Transaction

Approval must be one atomic transaction.

Canonical sequence:

1. Resolve the submitted `ChargenSession`.
2. Lock the session and any other required rows as strongly as the database
   backend supports.
3. Confirm that the session state permits approval.
4. Revalidate the complete current session, including:
   - backstory
   - attributes
   - skills
   - specializations
   - budget state
   - rules-profile invariants
5. Confirm that the normalized backstory contains non-whitespace text.
6. Verify that the character does not already have a conflicting permanent
   sheet.
7. Create the permanent `CharacterSheet`, including the exact reviewed
   backstory.
8. Copy approved core attributes and special fields.
9. Create permanent `CharacterSkill` rows.
10. Create permanent `CharacterSpecialization` rows.
11. Create the permanent approval audit event.
12. Link the chargen session to the resulting sheet.
13. Mark the chargen session approved and finalized.
14. Commit the transaction.

Any failure must roll back all effects together, including:

- sheet creation
- backstory copy
- attribute state
- skills
- specializations
- audit event
- session transition

### 15.1 Concurrency protections

The design must prevent:

- two staff members approving the same session twice
- a draft mutation racing with approval
- a second active session being created during finalization
- retries after failure creating duplicate sheet or skill rows

Recommended transaction concepts:

- Django `transaction.atomic()`
- row locking with `select_for_update()` where supported
- uniqueness constraints as the idempotency backstop
- state checks immediately before mutating

PostgreSQL should use row-level locking on the session row and any other
critical rows involved in approval.

SQLite should rely on atomic transactions, integrity constraints, and clean
retry or failure handling, because `select_for_update()` does not provide the
same semantics there.

### 15.2 Approval audit treatment for backstory

The permanent approval audit event should prove which reviewed backstory was
finalized without storing an unnecessary second full copy of the prose in a
generic audit payload.

Preferred audit metadata:

- source chargen-session identifier
- acting staff account
- approval timestamp
- backstory character count
- optional stable digest or hash of the normalized approved text
- approval-time validation summary or digest

The authoritative approved prose remains on `CharacterSheet.backstory`.

The MVP should not duplicate the full backstory in `previous_value`,
`new_value`, or another generic audit payload merely because the audit model
supports structured data.

A future dedicated revision-history feature may preserve explicit text
versions if the product later requires it. That is outside the MVP.

## 16. Service Boundaries

Redmond should keep the accepted service separation.

```text
sheets/
  models.py
  queries.py
  mutations.py
  validation.py
  audit.py

chargen/
  models.py
  selections.py
  budget.py
  validation.py
  review.py

rules/
  pools.py

presentation/
  sheets.py
  chargen.py
```

Responsibilities:

- `sheets.queries` reads permanent sheet state
- `sheets.mutations` performs authorized post-approval changes
- `sheets.validation` checks permanent sheet invariants
- `sheets.audit` creates durable permanent events
- `chargen.selections` owns current draft mutations
- `chargen.budget` calculates costs, refunds, totals, and remaining budget
- `chargen.validation` checks build legality and readiness
- `chargen.review` owns submit, request-changes, abandon, and approve
  transitions
- `rules.pools` constructs dice pools from structured sheet query results
- `presentation` converts structured data into player and staff text

Persistence models must not contain:

- ANSI rendering
- terminal-width decisions
- command parsing
- dice-pool rules
- full workflow orchestration

## 17. Planned Backstory Commands

The current command and prompt infrastructure is still minimal:

- Redmond uses the repo-owned `MuxCommand` base for command lifecycle and
  prompt emission
- prompt customization currently lives in `commands/prompt.py`
- `server/conf/inputfuncs.py` and `server/conf/cmdparser.py` are placeholders
  rather than an existing multiline editor framework

The backstory workflow should therefore plan to reuse the same Redmond
command and session interaction model rather than inventing a second
incompatible prompt framework.

### 17.1 Player draft entry

Planned command:

```text
+chargen/backstory
```

This is a multiline paste or entry command.

Planned interaction:

1. the command tells the player to paste or type the backstory
2. the player enters as many lines as needed
3. a single `.` on a line by itself terminates input
4. the terminator is not stored

Example planned prompt:

```text
Enter your character's backstory.
Paste or type as many lines as needed.
Enter a single . on a line by itself when finished.
```

The MVP should not design a full-screen editor, telnet line editor, cursor
navigation system, or editing language.

### 17.2 Temporary buffer lifecycle

Backstory capture should use temporary command or session state, not
incremental persistence.

For a new backstory:

1. capture lines into a temporary buffer
2. stop when the player enters `.` on a line by itself
3. normalize the candidate:
   - normalize line endings to `\n`
   - preserve meaningful internal line breaks and paragraphs
   - remove unnecessary trailing blank lines
4. validate the candidate:
   - reject empty or whitespace-only text
   - reject text over the configured domain limit
5. save the valid candidate to `ChargenSession.backstory`
6. confirm success

For replacing an existing backstory:

1. capture the proposed replacement into a temporary buffer
2. stop when the player enters `.` on a line by itself
3. normalize the candidate:
   - normalize line endings to `\n`
   - preserve meaningful internal line breaks and paragraphs
   - remove unnecessary trailing blank lines
4. validate the candidate:
   - reject empty or whitespace-only text
   - reject text over the configured domain limit
5. do not overwrite the existing stored backstory during capture,
   normalization, or validation
6. after successful validation, ask:

```text
Replace your existing backstory with this text? [yes/no]
```

1. on `yes`, persist the validated candidate
2. on `no`, discard it and retain the existing backstory
3. invalid confirmation input should follow the project's normal yes or no
   prompt behavior

An invalid blank or oversized candidate must not reach the replacement
confirmation prompt.

The previously stored backstory must remain unchanged during capture,
normalization, validation, and confirmation.

A disconnect, timeout, cancellation, or command failure before a successful
save must preserve the existing stored value.

### 17.3 Draft-view commands

Players need a read-only draft view:

```text
+chargen/backstory/view
```

This should display the current draft backstory or clearly report that none
has been entered.

Staff need a targeted draft-view form:

```text
+chargen/backstory <character>
```

This should:

- require staff permission
- resolve the named character through normal character lookup conventions
- target the named character's one active chargen session
- if exactly one active session exists, display its current backstory
- if no active session exists, report that the character has no active
  chargen session
- clearly identify it as chargen-state text
- report cleanly when the active session has no backstory
- not guess among historical `approved`, `abandoned`, or `superseded`
  sessions
- not silently display the approved permanent-sheet backstory from this
  command
- reserve historical chargen-session inspection for a later explicit
  session-identifier workflow
- deny targeted access to ordinary players

### 17.4 Approved-sheet commands

Players need an approved-sheet backstory command:

```text
+sheet/backstory
```

Staff need a targeted approved-sheet form:

```text
+sheet/backstory <character>
```

Expected behavior:

- a player can view their own approved backstory
- authorized staff can view a named character's approved backstory
- ordinary players may not target another character
- the full backstory is shown only through this subcommand
- the normal `+sheet` display should report only compact state such as
  `Backstory: Available`

### 17.5 Status surfaces

`+chargen/status` or `+chargen/summary` should show only completion state,
for example:

```text
Backstory: Complete
```

or:

```text
Backstory: Required
```

It should not dump the full prose.

## 18. Implementation Slices

### Slice A: permanent sheet persistence

- `CharacterSheet`
- `CharacterSheet.backstory`
- `CharacterSkill`
- `CharacterSpecialization`
- migrations
- field and uniqueness constraints
- permanent sheet creation policy

### Slice B: sheet queries and validation

- attribute lookup
- skill lookup
- structural validation
- immutable or structured query results
- tests independent of live sessions

### Slice C: read-only sheet feature

- player `+sheet`
- player `+sheet/backstory`
- staff `+sheet/backstory <character>`
- staff inspection
- presentation formatter
- basic pool construction through `rules.pools`
- command and service tests
- read-only backstory presentation and permission tests

### Slice D: chargen foundation

- `ChargenRulesProfile`
- `ChargenSession`
- `ChargenSession.backstory`
- explicit draft attribute fields
- `ChargenSkillSelection`
- `ChargenSpecializationSelection`
- `ChargenLedgerEntry`
- budget queries
- one-active-session constraint
- immutable profile behavior
- read-only `+chargen/status`
- draft backstory query behavior
- chargen completion-state output
- staff review access planning

### Slice E: writable backstory and attributes

- multiline `+chargen/backstory`
- `.` terminator handling
- temporary capture buffer
- replacement confirmation
- draft-state edit restrictions
- normalization and length validation
- attribute mutation services
- deterministic cost calculation
- purchases and refunds
- append-only ledger entries for budget-affecting changes only
- remaining-karma calculation
- validation errors

### Slice F: writable chargen skills

- skill selection mutations
- specialization support if in scope
- skill costs and refunds
- `+chargen/summary`
- constrained `+chargen/cost` syntax

### Slice G: review, finalization, and audit

- submission validation snapshot
- required-backstory submission validation
- submit transition
- request-changes transition
- staff review visibility for draft backstory
- approval-time revalidation
- atomic sheet finalization
- atomic copy into `CharacterSheet.backstory`
- `CharacterSheetAuditEvent`
- `+sheet/history`
- staff import path if implemented
- permanent approval audit records
- staff-import audit records
- permanent history presentation
- approval audit coverage for backstory finalization

### Slice H: later sheet domains and presentation polish

- `CharacterQuality`
- contacts
- magic or Resonance profile details
- additional resources and trackers
- ANSI policy
- color and framing
- width handling
- reusable presentation helpers

## 19. Planned Test Scenarios

Planned tests should cover:

- new multiline backstory capture
- paragraph preservation
- `.` termination
- terminator excluded from the stored text
- blank input rejection
- length-limit rejection
- confirmed replacement
- declined replacement
- invalid yes or no response handling
- interruption preserving the old backstory
- editing allowed in `draft`
- editing allowed in `changes_requested`
- editing rejected in `submitted`
- player draft backstory view
- staff draft backstory view by character name
- unauthorized targeted draft access denial
- submission rejected without a backstory
- approval copying the exact reviewed backstory
- player approved-sheet backstory view
- staff approved-sheet backstory view
- failed approval creating no partial permanent sheet

Backstory edits should not create `ChargenLedgerEntry` rows.

Detailed prose revision history is a possible later feature, not part of
this MVP design.

## 20. Early Command Surface

Read-only early command surfaces should be:

```text
+sheet
+sheet/skills
+sheet/backstory
+sheet/view <character>

+chargen
+chargen/help
+chargen/status
+chargen/backstory/view
```

Once writable backstory and skill work exists:

```text
+chargen/backstory
+chargen/summary
+chargen/cost <thing>
```

Once review and audit work exists:

```text
+sheet/history
```

The MVP should not add a temporary chargen-only character label.

Use the associated Evennia character key or name.
