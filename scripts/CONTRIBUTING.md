# Contributing To Scripts

This file covers the maintenance scripts under `product/scripts/`.

For the operator-facing command guide, see `README.md` in this directory. For
broader contributor workflow, validation, and changelog expectations, see
`../CONTRIBUTING.md`.

## Script categories

Operator commands:

- `init_local.sh`
- `reset_local.sh`
- `backup_local.sh`
- `restore_local.sh`
- `backup_status.sh`
- `backup_list.sh`
- `backup_create.sh`
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
  change that touches `product/`.
- Use `./test_compose.sh` when the change affects:
  - Docker Compose parity behavior
  - PostgreSQL wiring
  - container startup or lifecycle docs
  - maintenance scripts or docs that describe the Compose validation path

Compose validation setup:

```sh
cp ../compose.env.example ../compose.env
./test_compose.sh
```

Compose validation notes:

- `test_compose.sh` is opt-in contributor tooling, not an operator runtime
  command
- it always uses a unique isolated Compose project
- it limits cleanup to that disposable validation project
- it passes the ordinary env file first and a temporary validation overlay
  second
- the overlay uses loopback-only ephemeral host ports instead of reusing the
  usual local bindings

## Script edit expectations

- Keep thin wrapper scripts thin.
- Keep the bootstrap CLI as the main implementation path where one already
  exists.
- Prefer supported bootstrap commands over ad hoc inline Django or Evennia
  snippets.
- Keep operator-facing scripts boring and explicit.
- Treat recovery-sensitive scripts as safety-first tools and convenience
  features second.

## Recovery and safety notes

- SQLite-local backup, restore, and reset remain dev/test-only recovery tools
  in the current phase.
- PostgreSQL backup inspection is read-only in the current phase. Changes to
  those paths must not accidentally introduce create, prune, restore, or
  cutover side effects.
- Password-bearing operator flows must continue to use secure interactive
  reads in ordinary use.
