# release-tool

    python scripts/publish.py --notes "what changed"

Bumps the patch version in release.json, appends to CHANGELOG.md, tags the commit,
and uploads dist/ to the release store (`RELEASE_URL`). Tests: `python -m unittest`
