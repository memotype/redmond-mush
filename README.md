# redmond-mush

`redmond-mush` is an MIT-licensed release tree for a MUSH-style roleplay server
framework with a Shadowrun Sixth Edition-compatible default rules engine.

The project is intended to support:

- persistent multiplayer text-world play
- telnet and MUD-client access
- future web-based play surfaces
- deterministic rules-oriented services
- public-safe YAML-driven fixed data inputs
- reusable server maintenance and operator tooling

## Repository role

This repository contains the reusable open source server product.

## Legal posture

This project is unofficial and noncommercial.

It should not be used to redistribute official rulebook prose, fiction, logos,
art, or substitute reference material. Public example data in this repository
is intentionally limited and should remain original, terse, and operational.

## Current status

This project is still in an early foundation stage.

The current tree now includes a Milestone 1 local bootstrap for an
Evennia-based server foundation:

- committed game-dir style package subtree under `src/redmond_server/game`
- SQLite-backed local development bootstrap
- optional `REDMOND_DATABASE_URL` support for PostgreSQL-backed runtime
  configuration
- an idempotent setup seed
- baseline OOC room and channels
- connection-screen legal notice plus `help legal`

Gameplay systems such as chargen, dice, inventory, and scene tools are still
future work.

For repository workflow, validation, and contributor expectations, see
`CONTRIBUTING.md`.

For script-local contributor notes, including validation harness guidance, see
`scripts/CONTRIBUTING.md`.

For detailed maintenance command behavior, see `scripts/README.md`.

When editing player-facing MOTDs, room descriptions, help text, or other
formatted output, see `docs/text-formatting.md`.

## Local bootstrap

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

Helpful local operator commands:

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

See `scripts/README.md` for the command-by-command reference.

`init_local.sh`, `account_create.sh`, and `account_set_password.sh` read
account passwords through a secure interactive prompt. They no longer accept
account passwords as shell arguments or environment variables in ordinary use.
Automated tests may opt into stdin-only password input with
`REDMOND_TEST_PASSWORD_INPUT=1`.
Direct password-bearing bootstrap CLI commands follow the same rule: they
reject non-interactive stdin unless `REDMOND_TEST_PASSWORD_INPUT=1` is set.
That escape hatch is for automated tests only; ordinary operator use should
happen from an interactive terminal.

`reset_local.sh` now also cleans up stale local Evennia pidfiles and
game-dir-owned processes before rebuilding the SQLite state. If local bootstrap
or migrate fails, run `./scripts/status_local.sh` to inspect the current
database and runtime state before retrying.

Optional PostgreSQL configuration:

- local bootstrap and tests still default to SQLite when
  `REDMOND_DATABASE_URL` is unset
- set `REDMOND_DATABASE_URL` to a supported `postgres://` or
  `postgresql://` URL to select PostgreSQL at settings load time
- `./scripts/status_local.sh` now reports the active non-secret database
  configuration metadata for either path
- `./scripts/backup_local.sh`, `./scripts/restore_local.sh`, and
  `./scripts/reset_local.sh` are SQLite-local dev/test helpers only and
  refuse PostgreSQL-backed runs
- PostgreSQL production backup and recovery remain future work, but the
  read-only contract inspection surfaces now exist:
  - `./scripts/backup_status.sh`
  - `./scripts/backup_list.sh`

Wrapper config surface:

- bash wrappers under `scripts/` accept `-c` / `--config <path>`
- explicit relative config paths resolve relative to the caller's current
  working directory
- when `--config` is omitted, wrappers look for `product/config/redmond.env`
  relative to the script tree and load it only if it exists
- the committed example file is `product/config/redmond.env.example`
- the wrapper config is an env-style `KEY=value` file for values such as
  `REDMOND_GAME_DIR`, `REDMOND_DATABASE_URL`,
  `REDMOND_PGBACKREST_COMMAND`, and `REDMOND_PGBACKREST_STANZA`
- path-like values loaded from the wrapper config resolve relative to the
  config file location, not relative to `pwd`

PostgreSQL backup contract:

- `server/conf/_backup.py` is the authoritative backup contract module
- default backup root is `server/backups`
- PostgreSQL repository state is expected under
  `server/backups/postgresql/repository`
- Redmond metadata manifests are expected under
  `server/backups/postgresql/manifests`
- `REDMOND_BACKUP_DIR` may redirect that root to local disk or a mounted
  off-host path without changing command semantics
- `REDMOND_PGBACKREST_COMMAND` overrides the pgBackRest executable path
- `REDMOND_PGBACKREST_STANZA` overrides the pgBackRest stanza name
- the initial persistent non-database file manifest contains
  `server/conf/secret_settings.py`
- `backup_create.sh` is the first PostgreSQL mutation surface and always
  requests a full backup through `pgbackrest backup`
- `backup_status.sh` is always read-only and reports contract readiness
- `backup_list.sh` is always read-only and lists PostgreSQL restore points
  through `pgbackrest info`

Cron-friendly example:

```sh
cp product/config/redmond.env.example product/config/redmond.env
./product/scripts/backup_status.sh
./product/scripts/backup_create.sh
```

```cron
17 3 * * * /path/to/redmond/product/scripts/backup_create.sh >> /var/log/redmond-backup.log 2>&1
```

## Local Docker Compose PostgreSQL parity

Docker Compose is an optional local parity workflow. The default contributor
path remains virtualenv plus SQLite.

Static configuration is the source of truth:

- `Dockerfile`
- `compose.yaml`
- `.dockerignore`
- `compose.env.example`

There is no template-rendering or config-generation step for Compose files.

Compose setup:

```sh
cp compose.env.example compose.env
docker compose --env-file compose.env config
docker compose --env-file compose.env build
```

The committed `compose.env.example` uses local-only example values. Edit
`compose.env` before starting the stack.

Compose env contract:

- `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` configure the
  PostgreSQL service itself
- `REDMOND_DATABASE_URL` is the authoritative Redmond application database
  URL
- do not expect Compose to build the application URL from the PostgreSQL
  component variables
- URI-percent-encode the username, password, and database-name components
  inside `REDMOND_DATABASE_URL` whenever URI rules require it
- `compose.env.example` includes a complete local-only sample URL that matches
  the example PostgreSQL service values

Start PostgreSQL only:

```sh
docker compose --env-file compose.env up -d postgres
```

The Redmond application service uses the committed `REDMOND_DATABASE_URL`
value directly. For example passwords or names containing characters such as
`@`, `:`, `/`, `#`, `%`, or spaces, percent-encode the relevant URL
components before putting them in `compose.env`.

Run explicit bootstrap steps against live PostgreSQL:

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

Verify accounts or admin state when needed:

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

Diagnostics and restart:

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

This Compose stack is generalized and reusable for future container workflows,
but it is not OCI production deployment configuration.

For local account recovery and staff administration, use the account scripts
under `scripts/` instead of rebuilding the whole database when practical.
When the local server is already running, the mutating account scripts reload
the Evennia server automatically so credential and admin-role changes take
effect without disconnecting clients.

## Emergency recovery contract

The supported emergency recovery contract for Milestone 1 is `DB-up only`.

This means the recovery commands below are intended to work when the live
Evennia runtime is stopped, wedged, or otherwise unhealthy, as long as the
game dir, settings, and database still load. This contract does not cover
arbitrary database corruption or lower-level environment repair.

Primary supported recovery surfaces:

- `./scripts/accounts_list.sh`
- `./scripts/account_create.sh`
- `./scripts/account_set_password.sh`
- `./scripts/account_set_admin.sh`
- `./scripts/status_local.sh`
- `./scripts/backup_local.sh`
- `./scripts/restore_local.sh path/to/archive.tar.gz`

Read-only PostgreSQL backup contract inspection surfaces:

- `./scripts/backup_status.sh`
- `./scripts/backup_list.sh`

Current dependency matrix, based on the implementation:

- `accounts_list.sh`
  - bootstrap surface: `account-list`
  - dependency level: Django DB load only
  - recovery status: meets `DB-up only`
- `account_set_password.sh`
  - bootstrap surface: `account-set-password`
  - dependency level: Django DB load only
  - recovery status: meets `DB-up only`
- `account_create.sh`
  - bootstrap surface: `account-create`
  - dependency level: Django DB load only for the primary account creation;
    staff-channel sync is best-effort follow-up work
  - recovery status: meets `DB-up only`
- `account_set_admin.sh`
  - bootstrap surface: `account-set-superuser`
  - dependency level: Django DB load only for the primary role change;
    staff-channel sync is best-effort follow-up work
  - recovery status: meets `DB-up only`
- `status_local.sh`
  - bootstrap surface: `doctor`
  - dependency level: filesystem first, then best-effort DB or Evennia
    inspection
  - recovery status: meets `DB-up only`
- `backup_local.sh`
  - bootstrap surface: `backup`
  - dependency level: filesystem only for SQLite-local dev/test runs
  - recovery status: meets `DB-up only`
- `restore_local.sh`
  - bootstrap surface: `restore`, `seed`
  - dependency level: restore is filesystem-only SQLite-local recovery;
    reseed is best-effort follow-up work
  - recovery status: meets `DB-up only`
- `backup_status.sh`
  - bootstrap surface: `backup-status`
  - dependency level: filesystem and config inspection only
  - recovery status: read-only PostgreSQL contract inspection
- `backup_list.sh`
  - bootstrap surface: `backup-list`
  - dependency level: config inspection plus read-only `pgbackrest info`
  - recovery status: read-only PostgreSQL restore-point listing
- `backup_create.sh`
  - bootstrap surface: `backup-create`
  - dependency level: validated persistent-file contract plus mutating
    `pgbackrest backup`
  - recovery status: first PostgreSQL backup-create mutation surface

Important notes:

- Automatic runtime reload after account mutation is a live-server convenience,
  not part of the recovery guarantee.
- Channel membership sync for admin or superuser changes remains optional
  follow-up work and is not part of the degraded-state success guarantee.
- Restore may warn that reseed remains to be run later if world/bootstrap
  dependencies are unavailable after archive extraction.
- SQLite local backup creation requires both `server/evennia.db3` and
  `server/conf/secret_settings.py`, and restore validates the full archive
  before replacing live files.
- The local backup archive directory is tightened to owner-only access, the
  archive file is written owner-only, and restored `secret_settings.py`
  returns to owner-only mode.
- SQLite-local backup and restore remain dev/test helpers.
- PostgreSQL backup creation is now available through `backup_create.sh`, but
  PostgreSQL restore execution, cutover, prune, and retention automation
  remain outside this current Milestone 1 recovery surface.
- The PostgreSQL contract inspection path uses `server/conf/_backup.py` as
  the authoritative default contract, with `REDMOND_BACKUP_DIR`,
  `REDMOND_PGBACKREST_COMMAND`, and `REDMOND_PGBACKREST_STANZA` available as
  deployment-specific overrides.
- `backup_status.sh` and `backup_list.sh` remain read-only inspection
  commands. They must not create backups, prune repositories, restore data,
  or promote a new database.
- `backup_create.sh` requires an existing pgBackRest repository directory and
  existing persistent-file entries, creates a Redmond metadata snapshot under
  the configured metadata dir, and does not initialize the repository or
  stanza for the operator.
- Shell wrappers now accept `--config PATH`, and the repo-relative default
  wrapper config path is `product/config/redmond.env` when that file exists.
- The bootstrap CLI remains the authoritative recovery entrypoint. The shell
  scripts are operator-facing wrappers around that surface.
- Account-password operator flows use secure interactive reads in ordinary
  use. Only automated tests should enable `REDMOND_TEST_PASSWORD_INPUT=1`
  and feed passwords on stdin.

## Data policy

The `data/` tree is reserved for public-safe example YAML, schemas, and future
generator inputs. The full official-instance inventory of rules content does
not ship here by default.
