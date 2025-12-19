# Performance Testing – Shopwise

The purpose of performance testing in the Shopwise project
is to evaluate system behavior under expected and peak load
conditions and to identify potential bottlenecks.

Performance testing is treated as a non-functional testing layer
complementing functional test coverage.

## Scope

Performance testing focuses on backend API endpoints
that are critical for business operations.

- Product listing
- Product detail retrieval
- Order creation
- Mocked payment processing

## Types of Performance Tests

- Load Testing
- Stress Testing
- Spike Testing

Performance tests are not executed continuously
but as part of scheduled or on-demand validation.

## Tooling – k6

k6 is used for API-level performance testing.

## Alternative Tools

- Locust (Python-based)
- JMeter (GUI-based)

These tools are not part of the initial setup
but may be evaluated in future iterations.

## Test Architecture

Performance tests are implemented as isolated scripts
that interact directly with the backend API.

They do not require frontend components.

/tests/performance/
k6/
product-list.js
order-create.js

## Metrics

- Response time (avg, p95)
- Throughput (requests per second)
- Error rate

Baseline performance metrics are established
and used for regression comparison.

## CI/CD Integration

Performance tests are:

- executed manually
- executed before major releases

They are not blocking the main CI pipeline
to avoid long execution times.

## Risks and Mitigation

Risk:

- Flaky results due to shared environments

Mitigation:

- Run tests against controlled environments
- Use relative comparison instead of absolute thresholds

## Summary

Performance testing increases confidence
in system scalability and robustness
without overloading the CI pipeline.
