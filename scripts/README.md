# Scripts

This directory contains the shell commands that help you run, inspect, and
maintain a Redmond server.

If you are contributing code or docs, start with `../CONTRIBUTING.md`. If you
are looking for script-specific contributor guidance, see `CONTRIBUTING.md` in
this directory.

## Shared wrapper config

Most wrappers that source `common.sh` accept `-c` / `--config <path>`.

- explicit relative config paths resolve from the caller's current directory
- when `--config` is omitted, wrappers load `product/config/redmond.env`
  relative to the script tree only if that file exists
- `product/config/redmond.env.example` is the committed starting point
- wrapper config files use env-style `KEY=value` assignments only
- path-like values from wrapper config files resolve relative to the config
  file location

## Initialize a local server

Use `init_local.sh` to set up or finish setting up a local SQLite-backed
instance.

It will:

- create local secret settings if needed
- migrate the SQLite database
- ensure a bootstrap superuser exists
- run the one-time Evennia world bootstrap when needed
- run the idempotent Redmond seed step

## Reset local state

Use `reset_local.sh` when you want a fresh local SQLite-backed instance.

It will:

- stop Evennia for the local game directory
- clean up stale pid or restart files left by a bad shutdown
- remove the local SQLite database
- rerun `init_local.sh`

`reset_local.sh` refuses PostgreSQL-backed runs.

## Inspect local status

Use `status_local.sh` to print local bootstrap and runtime diagnostics as
JSON.

It is meant to stay useful even when the live Evennia runtime is stopped or
unhealthy, as long as the game directory, settings, and database still load.

## Manage accounts

Use these commands for day-to-day local account administration:

- `accounts_list.sh`
  - prints local accounts with ids, usernames, emails, and admin role state
- `account_create.sh <username> [email] [--superuser]`
  - creates a local account
  - reloads a live local server so the new account is immediately usable
- `account_set_password.sh <username>`
  - resets a local account password
  - reloads a live local server so the new password takes effect immediately
- `account_set_admin.sh <username> <true|false>`
  - promotes or demotes a local admin or superuser role
  - reloads a live local server so the role change takes effect immediately

These account commands are designed to keep working even if the live server is
down, as long as Django can still load the local database. Automatic reloads
and staff-channel synchronization are convenience follow-up behavior, not the
core degraded-state guarantee.

Ordinary password-bearing flows use secure interactive reads. Passwords should
not be passed through shell arguments or environment variables. Automated
tests may enable `REDMOND_TEST_PASSWORD_INPUT=1` and feed one password value
on stdin.

## Back up SQLite local state

Use these commands for ordinary SQLite-local dev/test recovery:

- `backup_local.sh`
  - creates one archive containing the local SQLite database and generated
    secret settings
  - requires both files to exist before writing the archive
- `restore_local.sh <archive>`
  - restores one local SQLite backup archive
  - validates the full archive before replacing live files
  - reruns the Redmond seed step as best-effort follow-up work

Important limits:

- these are SQLite-local dev/test tools, not the final production recovery
  workflow
- both commands refuse PostgreSQL-backed runs
- restore may warn that reseed was deferred if runtime-only world access is
  unavailable after extraction

## Inspect PostgreSQL backup readiness

These commands are read-only:

- `backup_status.sh`
  - prints PostgreSQL backup-readiness details as JSON
- `backup_list.sh`
  - lists PostgreSQL restore points through read-only `pgbackrest info`

They are safe inspection tools. They do not create backups, prune repositories,
restore data, or promote a replacement database.

## Create a PostgreSQL backup

Use `backup_create.sh` to request a full PostgreSQL backup through
`pgbackrest backup`.

Current behavior:

- requires a PostgreSQL-backed configuration
- requires an existing pgBackRest repository directory
- requires valid persistent-file readiness before mutation
- writes a Redmond metadata snapshot under the configured metadata directory
  after a successful backup

Current limits:

- it always requests a full backup
- it does not initialize the pgBackRest repository or stanza for you
- PostgreSQL restore execution, cutover, pruning, and retention automation are
  not shipped yet

The default PostgreSQL backup settings live in
`src/redmond_server/game/server/conf/_backup.py`.

## Run the container entrypoint

Use `container_start.sh` to start the committed game directory inside the
reusable container image.

It is intentionally narrow:

- it starts the normal runtime
- it uses supported Evennia start and stop commands only
- it keeps normal startup separate from migrations, seed steps, reset flows,
  and admin creation

## What still works when the live server is down

Several admin commands are meant to keep working if the live Evennia runtime is
stopped or wedged, as long as the game directory, settings, and database still
load:

- `accounts_list.sh`
- `account_create.sh`
- `account_set_password.sh`
- `account_set_admin.sh`
- `status_local.sh`
- `backup_local.sh`
- `restore_local.sh`

That support does not cover arbitrary database corruption or lower-level
environment repair.

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
- `REDMOND_BACKUP_DIR`, `REDMOND_PGBACKREST_COMMAND`, and
  `REDMOND_PGBACKREST_STANZA` are the PostgreSQL backup overrides supported in
  this phase

Contributor validation harnesses such as `test_fast.sh`, `test_full.sh`, and
`test_compose.sh` are documented in `../CONTRIBUTING.md` and
`CONTRIBUTING.md` in this directory.
