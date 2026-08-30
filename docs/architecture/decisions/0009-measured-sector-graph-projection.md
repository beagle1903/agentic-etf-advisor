# ADR 0009: Retain only measured sector exposure relationships

- Status: Accepted
- Date: 2026-08-30

## Context

The versioned research contract contains holdings, sectors, geography, benchmark, and
concentration data, but ADR 0001 and ADR 0007 require graph expansion to demonstrate value rather
than duplicate Chroma content. Candidate screening needs structured sector evidence, while the
current provider does not supply geography and no implemented consumer yet measures holdings,
overlap, or benchmark relationships.

## Decision

Project source-reported sector weights into normalized `Sector` nodes. Each versioned
`SourceDocument` reports weighted sector relationships, preserving snapshot attribution. The
active ETF node also carries weighted sector relationships that are replaced inside the snapshot
activation transaction.

Read the sector projection only from canonical field provenance and require its scalar status to
agree with the structured value or missing reason. Retrieval returns both the status and the
source-linked weights. The offline evaluator compares semantic-only and graph-enriched strategies
on identical candidates and retains the projection only when structured context coverage and an
exact threshold judgment improve without degrading ranking.

Do not add holdings, geography, benchmark, or overlap relationships in this iteration. Keep those
facts in the source contract until a versioned evaluation demonstrates ranking, constraint, or
explanation value.

## Consequences

- Sector evidence becomes directly usable by later deterministic candidate screening without
  asking an LLM to parse source prose.
- Missing sector evidence remains distinguishable from a reported zero weight.
- Semantic ranking remains Chroma-authoritative; sector relationships do not rerank candidates.
- Explanation providers receive bounded structured sector evidence but may not claim that user
  exclusions were applied or verified.
- Snapshot publication becomes stricter because inconsistent sector provenance blocks graph
  writes before activation.
- The graph avoids four unmeasured relationship families and their publication, migration, and
  consistency costs.
