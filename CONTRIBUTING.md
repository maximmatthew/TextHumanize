# Contributing to TextHumanize

Thank you for considering a contribution! This guide covers the process.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
# Full test suite
pytest tests/ -q

# Single file
pytest tests/test_core.py -q

# With coverage
pytest tests/ --cov=texthumanize --cov-report=term-missing
```

## Linting

We use **ruff** for linting and formatting:

```bash
ruff check texthumanize/ tests/
ruff format --check texthumanize/ tests/
```

## Type Checking

```bash
mypy texthumanize/ --ignore-missing-imports
```

## Fast Pre-Release Check

Some sandboxes hang the PHP/JS/`mypy`/full-`pytest` runners (process spawn or
esbuild platform-binary issues — not your change). When local runners stall,
run the dependency-free guard for a quick sanity pass in a couple of seconds:

```bash
python scripts/dev_check.py        # version sync, version-assert scan, quality rounding, fixtures
python scripts/check_version_sync.py
```

The authoritative gate is always GitHub CI (Python 3.9–3.13, PHP 8.1–8.3,
Node 20). `check_version_sync.py` also fails if a test file hardcodes a version
that no longer matches the package, so a release bump can no longer break CI on
a stale `assertSame`/`toBe` assertion.

## Project Structure

```
texthumanize/          # Main package
├── __init__.py        # Public API (PEP 562 lazy loading)
├── core.py            # humanize(), detect_ai(), and other top-level functions
├── pipeline.py        # 38-stage processing pipeline
├── exceptions.py      # Exception hierarchy
├── lang/              # Language-specific dictionaries (RU, EN, DE, FR, ES, …)
├── detectors.py       # AI detection heuristics
└── ...                # 120+ specialized modules
tests/                 # pytest test suite (2100+ tests)
php/                   # PHP port
examples/              # Usage examples
docs-src/              # MkDocs documentation source
```

## Pull Request Guidelines

1. **Create a branch** from `main`.
2. **Write tests** for any new functionality.
3. **Run the full test suite** before submitting.
4. **Keep PRs focused** — one feature or fix per PR.
5. **Update CHANGELOG.md** if your change is user-facing.
6. **Follow existing code style** — English docstrings, type hints for public APIs.

## Adding a New Language

1. Create `texthumanize/lang/<code>.py` with synonyms, collocations, and fillers.
2. Register the language in `texthumanize/lang/__init__.py`.
3. Add tests in `tests/test_multilang.py`.

## Good First Issues

See the public [Good First Issues guide](https://ksanyok.github.io/TextHumanize/contributing/good-first-issues/)
for scoped starter tasks covering language packs, AI marker packs, fixtures,
watermark samples, documentation examples, and bad-output regression tests.

## Reporting Bugs

Open an issue with:
- Python version
- `texthumanize` version (`python -c "import texthumanize; print(texthumanize.__version__)"`)
- Minimal reproducible example
- Expected vs actual behavior

## Code of Conduct

Be respectful and constructive. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
for project expectations and reporting paths.

## Security Reporting

Please do not open public issues for security vulnerabilities. Follow the
private reporting process in [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
