# Scripts

This directory contains public-safe product maintenance scripts.

Current Milestone 1 entrypoints:

- `init_local.sh`
  - create local secret settings if needed
  - migrate the SQLite database
  - ensure a bootstrap superuser exists
  - run the one-time Evennia world bootstrap when needed
  - run the idempotent Redmond seed step
- `reset_local.sh`
  - stop Evennia for this local game dir
  - clean up stale pid and restart files if a prior local run exited badly
  - remove the local SQLite database
  - rerun `init_local.sh`
- `backup_local.sh`
  - archive the local SQLite database and generated secret settings
- `restore_local.sh <archive>`
  - restore a local backup archive and reapply the Redmond seed step
- `status_local.sh`
  - print JSON diagnostics for local database, pidfiles, and runtime flags
- `accounts_list.sh`
  - print local accounts with ids, usernames, emails, and admin role state
- `account_create.sh <username> <password> [email] [--superuser]`
  - create a new local account
  - reload a live local server so the new account is immediately usable
  - primary account creation now satisfies the `DB-up only` recovery contract
  - optional staff-channel sync may be deferred when runtime-only world access
    is unavailable
- `account_set_password.sh <username> <new-password>`
  - reset a local account password
  - reload a live local server so the new password is immediately usable
  - current implementation satisfies the `DB-up only` recovery contract
- `account_set_admin.sh <username> <true|false>`
  - promote or demote an account's local admin/superuser role
  - reload a live local server so role changes take effect immediately
  - primary role changes now satisfy the `DB-up only` recovery contract
  - optional staff-channel sync may be deferred when runtime-only world access
    is unavailable
- `test_fast.sh`
  - run the quick product test suite for edit-time feedback
- `test_full.sh`
  - run the full product test suite, including slower integration cases

## Recovery contract notes

Milestone 1 recovery uses a `DB-up only` contract:

- supported degraded-state guarantee:
  - game dir, settings, and database still load
  - live Evennia runtime may be stopped or unhealthy
- not covered:
  - arbitrary database corruption
  - lower-level environment repair

Current recovery classification:

- meets `DB-up only` now:
  - `accounts_list.sh`
  - `account_create.sh`
  - `account_set_password.sh`
  - `account_set_admin.sh`
  - `status_local.sh`
  - `backup_local.sh`
- `restore_local.sh` also satisfies the contract for archive recovery.
  - reseed is now best-effort follow-up work and may be deferred with a
    warning when runtime-only world access is unavailable
- live runtime convenience only:
  - automatic reload after mutating account scripts

Phase 2 should preserve these shell wrappers while separating recovery-safe
bootstrap operations from runtime-only side effects such as live reload and
staff-channel synchronization.

Scripts that depend on private governance or private export workflow must stay
out of the OSS product tree.

For contributor automation and test helpers, prefer the bootstrap CLI surface
behind these scripts, such as `python -m redmond_server.bootstrap doctor`,
`account-list`, `account-verify-password`, and `set-ooc-room-name`, instead of
ad hoc inline Django or Evennia snippets.

The bootstrap tests also use one narrow internal env seam,
`REDMOND_TEST_FAIL_STAFF_SYNC=1`, to force deferred staff-channel sync while
still exercising the real bootstrap subprocess flow. Treat it as test-only.
