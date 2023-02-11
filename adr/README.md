# ADRs

For core decisions we use `Architecture Decision Records`. They are a type of RFC but smaller in scope and more
exact in the decision. The goal of adding an ADR is to summarize a discussion or fact-gathering effort. An RFC is the
start of a discussion and may occur before in-depth fact-finding occurs.

On the other hand, not every decision is an ADR. ADRs have to be significant. Things like naming, local APIs, or code
structure rarely match this criteria. These may be better as open discussions or RFCs, which may not lead to an easily
summarized conclusion. Instead, reach for an ADR when you can summarize the decision in a few sentences, at most. A good
ADR should fit on the format "When doing ..., we do ... because of ...".

```{admonition} [Significance criteria](https://engineering.atspotify.com/2020/04/when-should-i-write-an-architecture-decision-record/)
An ADR should be written whenever a decision of significant impact is made; it is up to each team to align on what defines a significant impact.
```

## ADR Process

The ADR process is meant to be very fast, with few fixed steps.

1. Identify need for a decision
2. Write an ADR using the below template
3. Open a PR
4. Once PR is accepted and merged, implement the decision.

### Template

```
# SEQUENCE_NUMBER. TITLE

Date: DATE WHEN PROPOSED

## Status

<!-- all ADRs start their life as accepted - we don't merge ADRs without accepting them. -->
Accepted

## Context

Describe when this decision would be relevant and why.

## Decision

An exact decision of what we will do when the context applies..

## Consequences

The end result of applying the decision.
```

## Accepted ADRs
```{toctree}
---
glob: true
maxdepth: 1
---
*
```
