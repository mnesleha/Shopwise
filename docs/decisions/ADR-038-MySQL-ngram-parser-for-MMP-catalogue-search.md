# ADR-038: MySQL ngram parser for MMP catalogue search

**Status**: Accepted

**Decision type**: Architecture

**Date**: Sprint 12

## Context

Shopwise requires catalogue search that behaves closer to modern user expectations, including partial-word matching. Standard MySQL full-text search tokenizes by words and does not provide intuitive substring behavior for queries such as matching past against pasta, pastička, or propast.

The project remains on MySQL for MMP and CV showcase purposes, but does not want to lock the application into MySQL-specific search behavior at the API and business-logic level. Search implementation must remain replaceable in the future, especially if the project migrates to PostgreSQL.

## Decision

Shopwise uses the MySQL `ngram` full-text parser with:

- `ngram_token_size = 2`
- `innodb_ft_enable_stopword = OFF`

for catalogue search indexes.

This behavior is isolated strictly inside the MySQL-specific search implementation (`MySQLCatalogSearchBackend`). All catalogue/business filtering, serializer behavior, and API contracts remain outside the database-specific backend.

## Architectural rules

- Database-specific search logic may only exist in `MySQLCatalogSearchBackend`.
- Search hit retrieval and relevance calculation belong to the backend.
- Catalogue filtering, availability policy, admin-only visibility rules, and final queryset construction belong to CatalogSearchService.
- Public API contracts must not expose MySQL-specific implementation details.

## Consequences

**Positive**:

- Improves substring-like matching for MMP search.
- Keeps MySQL as the current database without introducing an external search engine.
- Preserves a future migration path to PostgreSQL by isolating search implementation.

**Trade-offs**:

- Search semantics become MySQL-specific in the backend implementation.
- MySQL server configuration is required (`ngram_token_size`, stopword behavior).
- FULLTEXT indexes must be rebuilt after related configuration changes.
- The MySQL ngram parser is primarily documented for CJK tokenization, so this is an intentional pragmatic use for MMP rather than a long-term ideal search engine strategy.

## Alternatives Considered

1. Standard MySQL full-text search without ngram

   Rejected because token-based whole-word matching is too strict for expected catalogue UX.

2. Full-text plus ORM substring fallback

   Rejected for now because it mixes two search semantics and complicates ranking.

3. Immediate migration to PostgreSQL

   Rejected for MMP timing and scope reasons.

4. External search engine

   Rejected as unnecessary complexity for current MMP scope.

## Notes

If Shopwise later migrates to PostgreSQL, the public catalogue API and service layer should remain stable, and only the search backend implementation should be replaced.
