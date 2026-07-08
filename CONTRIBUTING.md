# Contributing

Thanks for your interest in contributing to `redmond-mush`.

## Docs map

- `README.md` is the operator and product entrypoint.
- `CONTRIBUTING.md` is the contributor workflow guide.
- `scripts/README.md` is the operator-facing command reference.
- `scripts/CONTRIBUTING.md` is the contributor guide for script and harness
  work under `product/scripts/`.

## Workflow

- Open issues and pull requests against this public repo as usual.
- Keep changes focused and easy to review.
- Include tests when behavior changes.
- Keep public-facing wording aligned with the OSS product surface.

For player-facing output, prefer native Evennia text markup and follow
`docs/text-formatting.md`.

## Validation

Create a local virtual environment and install the product in editable mode:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Baseline validation for ordinary product changes:

```sh
ruff check .
mypy src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

For product-only work, use the split harness:

```sh
./scripts/test_fast.sh
./scripts/test_full.sh
```

Use the harnesses this way:

- `./scripts/test_fast.sh` for edit-time feedback during ordinary work
- `./scripts/test_full.sh` before opening a PR or creating a release-visible
  changeset that touches `product/`
- `./scripts/test_compose.sh` only when the change affects the optional local
  Docker Compose PostgreSQL parity workflow or related docs and scripts

`test_compose.sh` is opt-in. It validates static Compose configuration, image
build, live PostgreSQL wiring, explicit bootstrap steps, service startup, safe
shutdown, preserved-volume restart behavior, and disposable cleanup.
Before running it, prepare the local env file:

```sh
cp compose.env.example compose.env
```

Compose validation safety notes:

- `test_compose.sh` always uses a unique isolated Compose project
- it does not tear down an ordinary local Redmond Compose stack
- it passes the ordinary env file first and a temporary validation overlay
  second
- the validation overlay uses loopback-only ephemeral host ports instead of
  reusing the operator's normal `4000`/`4001`/`4002` bindings
- ordinary `unittest` runs do not require Docker

For script-specific contributor expectations, including harness ownership and
wrapper design rules, see `scripts/CONTRIBUTING.md`.

## Release-visible changes

When a changeset materially changes exported product behavior, public docs,
packaging metadata, exported tests, maintenance scripts, or exported assets
under `product/`, update `product/CHANGELOG.md` in that same changeset when
the change is intended to be release-visible.

Before opening a pull request for release-visible work:

- review `product/CHANGELOG.md`
- ensure the matching entry is included in the same changeset
- ensure behavior-changing edits have matching validation coverage or an
  explicit justification

## Upstream maintenance note

Maintainers may reconcile accepted public changes through a private upstream
workflow before they appear in later public releases.
