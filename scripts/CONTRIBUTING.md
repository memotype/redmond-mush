# Contributing To Scripts

This file is the contributor guide for the maintenance scripts under
`product/scripts/`.

For operator-facing command behavior, see `README.md` in this directory.
For broader product contribution workflow, validation, and release-note
expectations, see `../CONTRIBUTING.md`.

## Script categories

Operator-facing runtime and recovery surfaces:

- `init_local.sh`
- `reset_local.sh`
- `backup_local.sh`
- `restore_local.sh`
- `backup_status.sh`
- `backup_list.sh`
- `status_local.sh`
- `accounts_list.sh`
- `account_create.sh`
- `account_set_password.sh`
- `account_set_admin.sh`
- `container_start.sh`

Contributor validation harnesses:

- `test_fast.sh`
- `test_full.sh`
- `test_compose.sh`

## Choosing a validation harness

- Use `./test_fast.sh` for ordinary edit-time feedback.
- Use `./test_full.sh` before opening a PR or finalizing a release-visible
  changeset that touches `product/`.
- Use `./test_compose.sh` when the change affects:
  - Docker Compose parity behavior
  - PostgreSQL wiring
  - container startup or lifecycle docs
  - maintenance scripts or docs that change the Compose validation contract

Compose validation setup:

```sh
cp ../compose.env.example ../compose.env
./test_compose.sh
```

Compose validation safety notes:

- `test_compose.sh` is opt-in contributor tooling, not an operator runtime
  command
- it always uses a unique isolated Compose project
- it limits cleanup to that disposable validation project
- it passes the ordinary env file first and a temporary validation overlay
  second
- the overlay uses loopback-only ephemeral host ports instead of reusing the
  operator's normal bindings

## Script edit expectations

- Keep thin wrapper scripts thin.
- Preserve the bootstrap CLI as the authoritative implementation surface where
  one already exists.
- Prefer calling supported bootstrap commands over replacing them with ad hoc
  inline Django or Evennia snippets.
- Keep operator-facing scripts boring and explicit.
- Treat recovery-sensitive scripts as safety surfaces first and convenience
  surfaces second.

## Recovery and safety framing

- SQLite-local backup, restore, and reset remain dev/test-only recovery tools
  in the current product phase.
- PostgreSQL backup inspection is read-only in the current phase; contributor
  changes must not accidentally introduce create, prune, restore, or cutover
  side effects through the inspection surfaces.
- Password-bearing operator flows must continue to use secure interactive
  reads in ordinary use.
