# Test Strategy

The project follows the test pyramid approach:

- Unit tests
- Integration tests
- End-to-end tests

Testing is automated and part of CI/CD pipeline.

- Performance tests (on-demand, outside of the CI/CD pipeline)

## Database Strategy for Testing

Different database engines are used depending on test level:

- Unit tests use SQLite (in-memory)
- Integration tests use MySQL
- Production uses MySQL

This approach provides fast feedback while still validating
production-like database behavior.
