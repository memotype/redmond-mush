# Contributing

Thanks for your interest in contributing to `redmond-mush`.

Useful contributions include bug fixes, tests, setup improvements, admin
tooling, docs, and carefully scoped gameplay foundations that match the
project's current direction.

Good places to start:

- `README.md` for the current project shape and local operator workflow
- `scripts/README.md` for the admin command guide
- `docs/text-formatting.md` for player-facing text conventions

## Basic workflow

- Open issues and pull requests against this repo as usual.
- Keep changes focused and easy to review.
- Include tests when behavior changes.
- Keep public-facing wording clear, welcoming, and consistent with the
  standalone `redmond-mush` repo experience.

For player-facing output, prefer native Evennia text markup and follow
`docs/text-formatting.md`.

## Local setup

Create a virtual environment and install the project in editable mode:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Validation

### Basic checks

Run these for ordinary project changes:

```sh
ruff check .
mypy src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

### Full checks

Use the split harnesses this way:

- `./scripts/test_fast.sh` for edit-time feedback during ordinary work
- `./scripts/test_full.sh` before opening a PR or finalizing a
  release-visible change

### Compose-only checks

`./scripts/test_compose.sh` is opt-in. Use it when the change affects:

- the optional local Docker Compose PostgreSQL workflow
- PostgreSQL wiring
- container startup or lifecycle docs
- maintenance scripts or docs that describe the Compose validation path

Before running it, prepare the local env file:

```sh
cp compose.env.example compose.env
```

`test_compose.sh`:

- always uses a unique isolated Compose project
- does not tear down an ordinary local Redmond Compose stack
- passes the ordinary env file first and a temporary validation overlay second
- uses loopback-only ephemeral host ports instead of reusing the default
  `4000`/`4001`/`4002` bindings
- validates static Compose config, image build, live PostgreSQL wiring,
  explicit bootstrap steps, service startup, clean shutdown, preserved-volume
  restart behavior, and disposable cleanup

Ordinary `unittest` runs do not require Docker.

For script-specific contributor expectations, including wrapper and harness
guidance, see `scripts/CONTRIBUTING.md`.

## Release-visible changes

If your change materially affects behavior, public docs, packaging metadata,
tests, maintenance scripts, or tracked public assets in this repository,
update `CHANGELOG.md` in the same changeset when the change is meant to be
visible in a release.

Before opening a PR for that kind of work:

- review `CHANGELOG.md`
- make sure the matching entry is in the same changeset
- make sure behavior-changing edits include matching validation coverage or a
  clear justification
