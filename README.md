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
- an idempotent setup seed
- baseline OOC room and channels
- connection-screen legal notice plus `help legal`

Gameplay systems such as chargen, dice, inventory, and scene tools are still
future work.

When editing player-facing MOTDs, room descriptions, help text, or other
formatted output, see `docs/text-formatting.md`.

## Validation

Create a local virtual environment and run the baseline checks:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
ruff check .
mypy src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

For product-only work, use the split test harness:

```sh
./scripts/test_fast.sh
./scripts/test_full.sh
```

`test_fast.sh` is intended for edit-time feedback. `test_full.sh` includes the
slower local bootstrap/reset/backup integration coverage and should be run
before creating a commit that includes `product/` changes, and again before
release.

For ordinary `product/` changes in this private control repo, also run
`node scripts/check-oss-export.cjs` so the downstream OSS export contract is
checked alongside the product test suite.

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
./scripts/account_create.sh username password user@example.com
./scripts/account_set_password.sh username new-password
./scripts/account_set_admin.sh username true
```

`reset_local.sh` now also cleans up stale local Evennia pidfiles and
game-dir-owned processes before rebuilding the SQLite state. If local bootstrap
or migrate fails, run `./scripts/status_local.sh` to inspect the current
database and runtime state before retrying.

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
  - bootstrap surface: `ensure-secret-settings`, `backup`
  - dependency level: filesystem only
  - recovery status: meets `DB-up only`
- `restore_local.sh`
  - bootstrap surface: `restore`, `seed`
  - dependency level: restore is filesystem only; reseed is best-effort
    follow-up work
  - recovery status: meets `DB-up only`

Important notes:

- Automatic runtime reload after account mutation is a live-server convenience,
  not part of the recovery guarantee.
- Channel membership sync for admin or superuser changes remains optional
  follow-up work and is not part of the degraded-state success guarantee.
- Restore may warn that reseed remains to be run later if world/bootstrap
  dependencies are unavailable after archive extraction.
- The bootstrap CLI remains the authoritative recovery entrypoint. The shell
  scripts are operator-facing wrappers around that surface.

## Data policy

The `data/` tree is reserved for public-safe example YAML, schemas, and future
generator inputs. The full official-instance inventory of rules content does
not ship here by default.
