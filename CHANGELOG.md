# CHANGELOG

This file tracks release tags for this repository.

Rules:

- Tag format for new releases: `v<major>.<minor>.<patch>`.
- Add a new top entry when tagging.

## Unreleased

- Add optional `REDMOND_DATABASE_URL`-driven PostgreSQL settings selection
  while keeping explicit SQLite defaults for local bootstrap and tests.
- Extend bootstrap diagnostics to report sanitized active database metadata
  and add Phase 2 parser and doctor coverage without requiring a live
  PostgreSQL container.
- Document the PostgreSQL configuration path and the current SQLite-first
  local workflow in the exported product README.

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
