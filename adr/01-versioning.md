# 1. Versioning

Date: 2023-02-11

## Status

Accepted

## Context

We need to follow a [PEP440](https://peps.python.org/pep-0440/) compatible versioning scheme. This is required to allow
other tools to resolve versions and compatibility properly.

## Decision

We will follow a versioning on the pattern `YY.compatibility.patch`.

## Consequences

* The YY is always set to the last two digits of the current year. When increasing this field the other two fields are
  reset to 0.
* The compatibility field is increased whenever we make API-incompatible changes.
* Otherwise, the patch field is increased.
