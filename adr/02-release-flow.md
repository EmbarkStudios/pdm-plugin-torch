# 2. Releases flow

Date: 2023-02-11

## Status

Accepted

## Context

In order to publish packages with high quality to PyPi and as tagged releases we need to have a consistent workflow that
is easy to follow and reproducible for all users.

## Decision

We will use tagged releases on GitHub to publish to PyPi. These releases will follow the versioning scheme described in
[01-versioning.md](01-versioning.md).

## Consequences

The flow will be as follows:

* Upon needing a release, create a PR:
  * Update `CHANGELOG.md` to ensure it contains all relevant changes. You can base this off of the nightly changelog.
  * Based on the above changes, set a new version in `pyproject.toml`.
  * Replace the heading in the changelog
  * Add diff labels at the bottom.

* Pull the new main, and tag it with `git tag -a vNEW_VERSION COMMIT_HASH`.
* Push the tag with `git push vNEW_VERSION`
* Make a new PR that adds back the "Unreleased" heading in the changelog.
