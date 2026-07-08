# CHANGELOG

This file tracks release tags for this repository.

Rules:

- Tag format for new releases: `v<major>.<minor>.<patch>`.
- Add a new top entry when tagging.

## Unreleased

- Add a repo-relative `--config` surface for the bash maintenance wrappers,
  centralize config loading in `scripts/common.sh`, and document the
  conventional `product/config/redmond.env` operator config path.
- Add the first PostgreSQL backup-create operator surface with
  `backup_create.sh`, a `backup-create` bootstrap command, pgBackRest
  preflight guardrails, and Redmond-owned metadata snapshots for successful
  full-backup runs.
- Harden operator-facing account-password flows so bootstrap commands and
  shell wrappers no longer accept account passwords via argv or env vars in
  ordinary use.
- Add an explicit stdin-only `REDMOND_TEST_PASSWORD_INPUT=1` test seam for
  password-bearing bootstrap automation, add a CLI-level non-TTY rejection
  test, and update the product docs and test harness around that contract.
- Add optional `REDMOND_DATABASE_URL`-driven PostgreSQL settings selection
  while keeping explicit SQLite defaults for local bootstrap and tests.
- Extend bootstrap diagnostics to report sanitized active database metadata
  and add Phase 2 parser and doctor coverage without requiring a live
  PostgreSQL container.
- Document the PostgreSQL configuration path and the current SQLite-first
  local workflow in the exported product README.
- Harden the SQLite-local backup, restore, and reset helpers so they refuse
  PostgreSQL-backed runs, reject incomplete archives, preserve live files
  until archive validation succeeds, and tighten secret-bearing artifact
  permissions.
- Tighten the SQLite-local recovery wrappers so backup no longer recreates
  missing secret settings, PostgreSQL-backed restore refuses before runtime
  stop side effects, and restore staging stays on the target filesystem to
  avoid cross-device promotion failures.
- Define the PostgreSQL backup contract in game-dir config, add read-only
  backup status and restore-point listing operator surfaces, and document the
  local-root plus mounted-storage override model without enabling PostgreSQL
  backup or restore execution yet.
- Clarify the OSS product documentation split so `README.md` is operator-
  facing, `CONTRIBUTING.md` is contributor-facing, and `scripts/README.md`
  serves as the operator command reference.
- Complete the OSS doc split by adding `product/scripts/CONTRIBUTING.md`,
  moving script and harness contributor guidance there, and restoring the
  lost Compose validation setup and safety context to `product/CONTRIBUTING.md`.

## v0.0.9 - 2026-06-25

- Move the stylized Redmond banner system to the pre-login connection screen
  and load title cards from a random file-backed pool under the game-dir
  config tree.
- Add a product-facing text-formatting guide plus README and contributing
  pointers for native Evennia markup usage.
- Import the 12 ASCII-safe Redmond title cards, preserve their telnet
  rendering with correct pipe escaping and backslash handling, and add focused
  connection-screen tests plus Layer 2 export metadata for the new public
  docs and assets.

## v0.0.6 - 2026-06-22

- Preserve executable bits on the exported maintenance shell scripts so local
  operator commands and test workflows remain runnable in fresh OSS clones.
- Tighten the OSS export and parity checks so ignored runtime artifacts do not
  pollute the public repo while exported files still match the product tree.

## v0.0.4 - 2026-06-20

- Add the split bootstrap facade package and keep the supported recovery
  surface centered on the bootstrap CLI and thin operator wrappers.
- Tighten the degraded-state account and restore flows so primary recovery
  actions succeed under the `DB-up only` contract and runtime-only follow-up
  work is deferred safely.
- Replace the old inline test fault-injection harness with a narrow test-only
  staff-sync failure seam that still exercises the real bootstrap subprocess
  path.
- Clarify contributor validation around `./scripts/test_fast.sh`,
  `./scripts/test_full.sh`, and the downstream export/release workflow.
