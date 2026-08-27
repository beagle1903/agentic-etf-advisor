# ADR 0001: Separate vector and graph responsibilities

- Status: Accepted
- Date: 2026-08-27

## Context

The project is intended to teach and exercise both vector retrieval and graph-aware
retrieval. Chroma and Neo4j both support vector search, so using both without a boundary
would duplicate data and complicate consistency.

## Decision

Use Chroma as the initial store for unstructured source chunks and Neo4j as the store for
normalized ETF entities and relationships. Join the two through stable source IDs.

Neo4j graph traversal enriches vector candidates with relationships such as issuer,
category, benchmark, holding, sector, geography, and overlapping exposure. We will measure
whether graph enrichment improves retrieval before expanding the graph schema.

## Consequences

- Each database has a distinct responsibility.
- Ingestion must preserve stable IDs and provenance across both stores.
- Consistency checks become part of the ingestion pipeline.
- If evaluations show no useful graph lift, the architecture can simplify to one store.
