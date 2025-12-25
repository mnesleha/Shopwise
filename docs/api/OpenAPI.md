# OpenAPI / Swagger in Shopwise

## Purpose

OpenAPI is used in the Shopwise project as a **core documentation and quality tool**,
not merely as an automatically generated API reference.

Its primary purpose is to:

- provide a single, consistent view of the API surface
- make API behavior explicit and inspectable
- support testing, onboarding, and cross-role communication

## Why OpenAPI

The decision to use OpenAPI (Swagger) in Shopwise is driven by several goals:

- API-first development  
  The backend exposes business workflows through an API that must be clearly defined
  before frontend and further integrations are developed.

- Documentation as part of quality assurance  
  OpenAPI allows us to inspect what the system _actually exposes_, not what we believe it exposes.
  This helps identify inconsistencies, missing edge cases, and undocumented behavior.

- Shared language across roles  
  OpenAPI provides a common reference point for:

  - developers
  - QA engineers
  - test managers
  - project managers

- Reduction of tribal knowledge  
  By generating documentation directly from the codebase,
  API knowledge does not rely on memory or historical discussions.

## Role of OpenAPI in Shopwise

In Shopwise, OpenAPI serves multiple roles:

- Canonical API reference  
  OpenAPI is treated as the authoritative description of available endpoints,
  request/response structures, and error scenarios.

- Diagnostic tool  
  Generated documentation is reviewed to detect:

  - missing validation rules
  - unclear or inconsistent responses
  - undocumented status codes

- Input for testing strategy  
  Gaps identified in OpenAPI documentation are used as input for:

  - new automated tests
  - refinement of existing test cases

- Onboarding support  
  New team members can explore the API behavior without reading implementation code.

## OpenAPI and Testing

OpenAPI documentation is intentionally used to support and improve testing.

The workflow is:

1. Generate OpenAPI documentation from the current codebase
2. Review the documentation from a consumer perspective
3. Identify unclear, missing, or ambiguous behavior
4. Verify whether such cases are covered by automated tests
5. Create new tests where coverage is missing

This approach aligns with the project's **documentation-driven development** mindset.

## Integration with Other Tools

OpenAPI documentation in Shopwise is designed to integrate with:

- SwaggerUI

  Interactive exploration of endpoints and schemas

- Redoc

  Readable, structured API reference for documentation purposes.

- Postman

  OpenAPI definitions can be imported to Postman to:

  - generate requests collections
  - support E2E testing
  - reduce manual setup effort

## Expected Outputs

The use of OpenAPI in Shopwise is expected to produce:

- A complete, auto-generated API specification
- Interactive API documentation (Swagger UI, Redoc)
- A clear overview of API workflows and constraints
- A list of documentation and testing gaps
- Improved alignment between implementation, tests, and documentation

## Scope and Non-Goals

OpenAPI documentation in this project aims to describe:

- public API endpoints
- request and response formats
- authentication requirements
- validation and error scenarios

It does not aim to:

- replace detailed architectural documentation
- describe internal implementation details
- serve as a frontend design specification

## Summary

In Shopwise, OpenAPI is treated as an active part of the development and QA process.

It helps ensure that:

- the API is understandable and consistent
- behavior is explicitly documented
- quality issues are discovered early
- documentation evolves together with the codebase
