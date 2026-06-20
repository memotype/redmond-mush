# Contributing

Thanks for your interest in contributing to `redmond-mush`.

## Workflow

- Open issues and pull requests against this public repo as usual.
- Keep changes focused and easy to review.
- Include tests when behavior changes.

## Validation

Before opening a pull request, run:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
ruff check .
mypy src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Upstream maintenance note

Maintainers may reconcile accepted public changes through a private upstream
workflow before they appear in later public releases.
