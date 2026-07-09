# redmond-mush

`redmond-mush` is an MIT-licensed MUSH-style roleplay server built on Evennia
with a Shadowrun Sixth Edition-compatible default rules approach.

It is meant to grow into a persistent multiplayer text world with:

- telnet and MUD-client access
- future web-based play options
- deterministic game and rules services
- original, redistributable example data
- practical server administration tooling

## Project boundaries

This project is unofficial and noncommercial.

It is not a place to redistribute official rulebook prose, fiction, logos,
art, or substitute reference material. Example data in this repository should
stay original, compact, and useful for running the server.

## Current status

Redmond is still in an early foundation stage, but a local Milestone 1 server
workflow is already in place.

What works today:

- an Evennia game directory under `src/redmond_server/game`
- SQLite-backed local setup by default
- optional `REDMOND_DATABASE_URL` support for PostgreSQL-backed runtime
  configuration
- an idempotent initial seed
- baseline OOC room and channels
- connection-screen legal notice plus `help legal`

Still ahead:

- chargen
- dice and wider rules systems
- inventory
- scene tools
- PostgreSQL restore and cutover workflows

If you want to contribute, start with `CONTRIBUTING.md`. If you want the
script-by-script admin reference, see `scripts/README.md`.

## Quick local setup

From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
./scripts/init_local.sh
cd src/redmond_server/game
evennia start
```

Default local connection targets after `evennia start`:

- telnet: `localhost:4000`
- webclient: `http://localhost:4001`

`init_local.sh`, `account_create.sh`, and `account_set_password.sh` ask for
passwords interactively. In normal use, they do not accept passwords through
shell arguments or environment variables. Automated tests may opt into
stdin-fed password input with `REDMOND_TEST_PASSWORD_INPUT=1`, but that escape
hatch is for test automation only.

If setup or migration fails, run `./scripts/status_local.sh` before retrying
so you can see the current database and runtime state.

## Common admin commands

These are the main day-to-day commands for a local server:

```sh
./scripts/reset_local.sh
./scripts/backup_local.sh
./scripts/restore_local.sh path/to/archive.tar.gz
./scripts/status_local.sh
./scripts/accounts_list.sh
./scripts/account_create.sh username user@example.com
./scripts/account_set_password.sh username
./scripts/account_set_admin.sh username true
```

Use them this way:

- `reset_local.sh` rebuilds a local SQLite-backed instance from scratch and
  also cleans up stale pidfiles or restart files left by a bad local shutdown.
- `backup_local.sh` and `restore_local.sh` handle SQLite-local backup and
  restore for ordinary dev/test use.
- `status_local.sh` reports local bootstrap and runtime diagnostics.
- the account scripts handle account creation, password resets, and local
  admin-role changes without rebuilding the whole database

When the server is already running, the mutating account scripts reload the
local Evennia process automatically so credential and admin-role changes take
effect right away.

For a detailed command guide, see `scripts/README.md`.

## SQLite and PostgreSQL

SQLite is still the default local workflow.

- if `REDMOND_DATABASE_URL` is unset, local setup and tests stay on SQLite
- set `REDMOND_DATABASE_URL` to a supported `postgres://` or
  `postgresql://` URL to run against PostgreSQL
- `./scripts/status_local.sh` reports the active non-secret database
  configuration for either path

The local reset and SQLite-local backup helpers are intentionally limited:

- `./scripts/reset_local.sh`
- `./scripts/backup_local.sh`
- `./scripts/restore_local.sh`

Those commands are dev/test helpers for SQLite-backed runs only. They refuse
PostgreSQL-backed configurations.

For PostgreSQL-backed setups, the currently shipped backup commands are:

- `./scripts/backup_status.sh`
- `./scripts/backup_list.sh`
- `./scripts/backup_create.sh`

What that means today:

- backup status and restore-point listing are available now
- full backup creation is available now
- PostgreSQL restore execution, cutover, pruning, and retention automation are
  not implemented yet

## Wrapper config

The shell wrappers under `scripts/` accept `-c` / `--config <path>`.

- explicit relative config paths resolve from the caller's current working
  directory
- when `--config` is omitted, wrappers look for
  `product/config/redmond.env` relative to the script tree and load it only if
  that file exists
- the committed example file is `product/config/redmond.env.example`
- wrapper config files use env-style `KEY=value` assignments
- path-like values loaded from the config file resolve relative to the config
  file location, not relative to `pwd`

Typical values include:

- `REDMOND_GAME_DIR`
- `REDMOND_DATABASE_URL`
- `REDMOND_BACKUP_DIR`
- `REDMOND_PGBACKREST_COMMAND`
- `REDMOND_PGBACKREST_STANZA`

Cron-friendly example:

```sh
cp product/config/redmond.env.example product/config/redmond.env
./product/scripts/backup_status.sh
./product/scripts/backup_create.sh
```

```cron
17 3 * * * /path/to/redmond/product/scripts/backup_create.sh \
  >> /var/log/redmond-backup.log 2>&1
```

## Docker Compose local parity

Docker Compose is an optional local PostgreSQL parity workflow. The default
contributor path is still virtualenv plus SQLite.

Static configuration lives in:

- `Dockerfile`
- `compose.yaml`
- `.dockerignore`
- `compose.env.example`

There is no template-rendering or config-generation step for these files.

Set up the local Compose env file:

```sh
cp compose.env.example compose.env
docker compose --env-file compose.env config
docker compose --env-file compose.env build
```

The committed `compose.env.example` uses local-only example values. Edit
`compose.env` before starting the stack.

Compose env rules:

- `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` configure the
  PostgreSQL service itself
- `REDMOND_DATABASE_URL` is the authoritative database URL used by Redmond
- Compose does not build the application URL from the PostgreSQL component
  variables
- percent-encode username, password, and database-name components inside
  `REDMOND_DATABASE_URL` whenever URI rules require it

Start PostgreSQL only:

```sh
docker compose --env-file compose.env up -d postgres
```

Run the explicit bootstrap steps against live PostgreSQL:

```sh
docker compose --env-file compose.env run --rm redmond \
  python -m redmond_server.bootstrap migrate \
  --game-dir /opt/redmond/src/redmond_server/game

docker compose --env-file compose.env run --rm redmond \
  sh -lc "printf 'change-me-admin-password\\n' | \
  REDMOND_TEST_PASSWORD_INPUT=1 \
  python -m redmond_server.bootstrap ensure-superuser \
  --username admin \
  --email admin@example.com \
  --game-dir /opt/redmond/src/redmond_server/game"

docker compose --env-file compose.env run --rm redmond \
  python -m redmond_server.bootstrap initial-setup \
  --game-dir /opt/redmond/src/redmond_server/game

docker compose --env-file compose.env run --rm redmond \
  python -m redmond_server.bootstrap seed \
  --game-dir /opt/redmond/src/redmond_server/game
```

Check account or admin state when needed:

```sh
docker compose --env-file compose.env run --rm redmond \
  python -m redmond_server.bootstrap has-superuser \
  --game-dir /opt/redmond/src/redmond_server/game

docker compose --env-file compose.env run --rm redmond \
  python -m redmond_server.bootstrap account-list \
  --game-dir /opt/redmond/src/redmond_server/game
```

Start the normal service:

```sh
docker compose --env-file compose.env up -d redmond
```

Default local connection targets for the Compose stack:

- telnet: `localhost:4000`
- webclient: `http://localhost:4001`

Useful diagnostics and restart commands:

```sh
docker compose --env-file compose.env logs -f postgres redmond
docker compose --env-file compose.env exec redmond evennia status
docker compose --env-file compose.env exec redmond \
  python -m redmond_server.bootstrap doctor \
  --game-dir /opt/redmond/src/redmond_server/game
docker compose --env-file compose.env restart redmond
```

Stop while preserving PostgreSQL data:

```sh
docker compose --env-file compose.env down
```

Reset a disposable Compose environment and remove the named PostgreSQL volume:

```sh
docker compose --env-file compose.env down -v --remove-orphans
```

This stack is useful for local parity testing and future container work, but
it is not production OCI deployment configuration.

## What backup and recovery are supported right now

For Milestone 1, a number of admin commands are meant to keep working even if
the live Evennia runtime is down, as long as the game directory, settings, and
database still load.

That includes:

- `./scripts/accounts_list.sh`
- `./scripts/account_create.sh`
- `./scripts/account_set_password.sh`
- `./scripts/account_set_admin.sh`
- `./scripts/status_local.sh`
- `./scripts/backup_local.sh`
- `./scripts/restore_local.sh path/to/archive.tar.gz`

What to expect from those commands:

- account creation, password resets, and admin-role changes work through the
  bootstrap CLI without requiring a healthy live server
- automatic runtime reload after account changes is a convenience when the
  server is already up, not part of the degraded-state guarantee
- admin/staff channel sync after account changes is follow-up work and may be
  deferred if runtime-only world access is unavailable
- `status_local.sh` is meant to stay useful whenever bootstrap diagnostics can
  still inspect the local tree
- `restore_local.sh` restores the archive first, then attempts the Redmond
  seed step as best-effort follow-up work

SQLite-local backup and restore details:

- backup creation requires both `server/evennia.db3` and
  `server/conf/secret_settings.py`
- restore validates the full archive before replacing live files
- backup archives, backup directories, and restored `secret_settings.py`
  return to owner-only permissions
- these SQLite-local helpers remain dev/test tools, not the final production
  recovery story

PostgreSQL backup support today:

- `backup_status.sh` checks readiness and stays read-only
- `backup_list.sh` lists PostgreSQL restore points through read-only
  `pgbackrest info`
- `backup_create.sh` creates a full PostgreSQL backup and writes a Redmond
  metadata snapshot after success

Still not shipped:

- PostgreSQL restore execution
- PostgreSQL cutover
- repository pruning
- retention automation

The PostgreSQL backup defaults come from
`src/redmond_server/game/server/conf/_backup.py`. The main deployment-specific
overrides in this phase are `REDMOND_BACKUP_DIR`,
`REDMOND_PGBACKREST_COMMAND`, and `REDMOND_PGBACKREST_STANZA`.

## Data policy

The `data/` tree is reserved for redistributable example YAML, schemas, and
future generator inputs. Full instance-specific rules inventories do not ship
here by default.

## Where to go next

- `CONTRIBUTING.md` for contributor setup and validation
- `scripts/README.md` for the detailed admin command guide
- `scripts/CONTRIBUTING.md` for script and validation-harness contribution
  notes
- `docs/text-formatting.md` for player-facing text formatting guidance
