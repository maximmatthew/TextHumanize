# Release Checklist

Use this checklist before publishing a TextHumanize release to PyPI and Packagist.

## Version Sync

- [ ] Pick a version that is newer than PyPI and Packagist.
- [ ] Update Python, PHP, TypeScript/JavaScript manifests and version constants.
- [ ] Update README install pins and "What's New" section.
- [ ] Add a top entry in `CHANGELOG.md`.
- [ ] Run `python scripts/check_version_sync.py`.

## Local Verification

- [ ] Run `python scripts/release_smoke_test.py`.
- [ ] Run Python tests: `pytest --tb=short --timeout=120 -q`.
- [ ] Run PHP tests: `cd php && vendor/bin/phpunit`.
- [ ] Run JS tests: `cd js && npm test`.
- [ ] Build Python packages: `python -m build`.
- [ ] Validate packages: `twine check dist/*`.

## Publish Flow

- [ ] Commit release changes.
- [ ] Push `main`.
- [ ] Create and push a matching tag, for example `v0.31.0`.
- [ ] Create a GitHub release from the tag.
- [ ] Confirm the Publish to PyPI workflow succeeds.
- [ ] Confirm Packagist auto-update picked up the new tag.
- [ ] Verify install commands:
  - `pip install texthumanize==0.31.0`
  - `composer require ksanyok/text-humanize:^0.28`

## Post-Release

- [ ] Open PyPI and confirm the latest version, README, metadata, and files.
- [ ] Open Packagist and confirm the latest version, source reference, and README.
- [ ] Run one fresh install smoke test from a clean virtual environment.
- [ ] Record any release issues as follow-up tasks before the next version.
