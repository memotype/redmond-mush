# Scripts

This directory contains public-safe product maintenance scripts.

This file is the operator-facing command reference for the shipped maintenance
scripts. For contributor workflow and validation policy, see
`../CONTRIBUTING.md`.
For script-local contributor notes, including validation harness usage, see
`CONTRIBUTING.md` in this directory.

Shared wrapper config:

- wrappers that source `common.sh` accept `-c` / `--config <path>`
- explicit relative config paths resolve from the caller's current directory
- when `--config` is omitted, wrappers load `product/config/redmond.env`
  relative to the script tree only if that file exists
- `product/config/redmond.env.example` is the committed starting point
- wrapper config files use env-style `KEY=value` assignments only
- path-like values from wrapper config files resolve relative to the config
  file location

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
  - refuse PostgreSQL-backed runs
- `backup_local.sh`
  - archive the local SQLite database and generated secret settings
  - require both files to exist before writing the archive
  - refuse PostgreSQL-backed runs
- `restore_local.sh <archive>`
  - restore a local SQLite backup archive and reapply the Redmond seed step
  - validate the archive completely before replacing live files
  - refuse PostgreSQL-backed runs
- `backup_status.sh`
  - print read-only PostgreSQL backup contract status as bootstrap JSON
- `backup_list.sh`
  - list PostgreSQL restore points through read-only `pgbackrest info`
- `backup_create.sh`
  - create a PostgreSQL full backup through `pgbackrest backup`
  - require a PostgreSQL-backed configuration
  - require an existing pgBackRest repository directory and persistent-file
    contract readiness before mutation
  - write a Redmond metadata snapshot under the configured metadata dir after
    successful backup creation
- `status_local.sh`
  - print bootstrap JSON diagnostics for local database, pidfiles, and
  runtime flags
- `accounts_list.sh`
  - print local accounts with ids, usernames, emails, and admin role state
- `account_create.sh <username> [email] [--superuser]`
  - create a new local account
  - reload a live local server so the new account is immediately usable
  - primary account creation now satisfies the `DB-up only` recovery contract
  - optional staff-channel sync may be deferred when runtime-only world access
    is unavailable
- `account_set_password.sh <username>`
  - reset a local account password
  - reload a live local server so the new password is immediately usable
  - current implementation satisfies the `DB-up only` recovery contract
- `account_set_admin.sh <username> <true|false>`
  - promote or demote an account's local admin/superuser role
  - reload a live local server so role changes take effect immediately
  - primary role changes now satisfy the `DB-up only` recovery contract
  - optional staff-channel sync may be deferred when runtime-only world access
    is unavailable
- `container_start.sh`
  - start the committed game dir inside the reusable container image
  - use supported Evennia start and stop commands only
  - keep normal runtime startup separate from migrations, seed, and admin
    creation

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
- `status_local.sh` is intended to stay useful whenever bootstrap diagnostics
  can run, even when the live Evennia runtime is stopped or unhealthy.
- `restore_local.sh` also satisfies the contract for archive recovery.
  - reseed is now best-effort follow-up work and may be deferred with a
    warning when runtime-only world access is unavailable
  - the archive must contain the full SQLite-local member set before any live
    file replacement begins
- `backup_status.sh` and `backup_list.sh` are read-only PostgreSQL contract
  inspection tools.
  - they must not create backups, prune repositories, restore data, or
    promote a replacement database
- `backup_create.sh` is the first PostgreSQL mutation tool.
  - it always requests a full backup
  - it must not initialize a pgBackRest repository or stanza for the
    operator
- A cron-oriented operator setup can keep instance values in
  `product/config/redmond.env` and call wrappers directly without `cd`.
- live runtime convenience only:
  - automatic reload after mutating account scripts

Phase 2 should preserve these shell wrappers while separating recovery-safe
bootstrap operations from runtime-only side effects such as live reload and
staff-channel synchronization.

Password-handling contract:

- ordinary operator flows must use secure interactive password reads
- account passwords must not be passed through shell arguments or env vars
- automated tests may enable `REDMOND_TEST_PASSWORD_INPUT=1` and feed one
  password value on stdin for password-bearing bootstrap commands

## Compose parity notes

Phase 3 adds an opt-in local Docker Compose workflow for PostgreSQL parity.

- static files are the source of truth:
  - `Dockerfile`
  - `compose.yaml`
  - `.dockerignore`
  - `compose.env.example`
- copy `compose.env.example` to `compose.env` before running Compose
- run Compose explicitly with `docker compose --env-file compose.env ...`
- keep `REDMOND_DATABASE_URL` as the authoritative application database URL
- percent-encode username, password, and database-name components inside
  `REDMOND_DATABASE_URL` whenever URI rules require it
- `test_compose.sh` always overrides the Compose project name with a unique
  disposable validation project and limits cleanup to that project only
- `test_compose.sh` passes the ordinary env file first and a temporary
  validation overlay second so the validation run gets loopback-only
  ephemeral host ports
- normal app startup inside Compose must not run migrations, seed, reset, or
  admin creation automatically
- local backup, restore, and reset remain SQLite-local dev/test tools in this
  phase
- PostgreSQL backup contract defaults now live in
  `src/redmond_server/game/server/conf/_backup.py`
- `REDMOND_BACKUP_DIR` may point the PostgreSQL repository root at local disk
  or a mounted off-host path without changing the wrapper commands
- `REDMOND_PGBACKREST_COMMAND` and `REDMOND_PGBACKREST_STANZA` are the only
  supported PostgreSQL backup-surface overrides in this phase

Contributor validation harnesses such as `test_fast.sh`, `test_full.sh`, and
`test_compose.sh` are documented in `CONTRIBUTING.md` in this directory.
