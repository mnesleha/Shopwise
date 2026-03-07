# ADR-037: Product Media Storage Strategy

**Status**: Accepted

**Decision type**: Architecture

**Date**: Sprint 12

## Context

Shopwise is moving from MVP toward an MMP/1.0-ready product catalogue. Product content now requires:

- structured product gallery images,
- markdown-based long descriptions with embedded images,
- local development support,
- a clean migration path to S3-compatible object storage later,
- a single storage abstraction that does not require code refactoring when deployment storage changes.

The product catalogue must support two different classes of media:

1. **Product gallery images** — managed as structured product assets.
2. **Markdown/editorial images** — uploaded from the admin markdown editor and embedded inside long-form product descriptions.

These two media types should share the same storage backend, but they must remain logically separated.

## Decision

Shopwise adopts Django’s `STORAGES` configuration as the single abstraction point for all product-related media.

### Storage abstraction

`STORAGES["default"]` is the canonical storage backend for all media uploads.

- In local development, `STORAGES["default"]` uses `FileSystemStorage`.
- In production, the backend can be switched to S3-compatible storage by configuration only, without changing application code.

### Media classes

Two separate media paths are defined within the same storage backend:

- **Product gallery images**
  - stored under a dedicated gallery path such as `products/gallery/`
  - backed by the `ProductImage` model
- **Markdown/editorial description images**
  - stored under a dedicated editorial path such as `products/descriptions/`
  - uploaded directly to storage through a dedicated upload view
  - not represented by `ProductImage` database rows

### Product image rules

- `ProductImage` is the only database-backed image carrier for catalogue/gallery media.
- `Product.primary_image` references a `ProductImage`.
- Gallery images and primary image are managed as structured product assets.
- API serializers expose ready-to-use image URLs for frontend consumption.
- The frontend uses only URLs returned by the API and does not construct media paths itself.

### Markdown upload rules

Markdown description images are uploaded through a dedicated Martor upload endpoint.

That upload endpoint:

- writes directly to `storages["default"]`,
- stores files under the editorial descriptions path,
- returns storage-generated URLs,
- does not create `ProductImage` records.

This keeps product gallery assets separate from editorial markdown assets while still using a common storage backend.

### Image processing

For product gallery images, Shopwise uses:

- `ImageField` / Pillow
- `django-versatileimagefield`
- PPOI support
- multiple API-ready variants (for example: thumb, medium, large, full)

The catalogue serializer returns only the primary image.
The product detail serializer returns the full gallery.

### Frontend contract

The frontend uses `next/image` and consumes image URLs directly from the backend API.
Frontend configuration must allow local media URLs and future remote/CDN URLs via `remotePatterns`.

## Consequences

**Positive**

- Storage backend can later be switched from local filesystem to S3 by configuration.
- Product gallery images and markdown/editorial images remain clearly separated.
- The frontend remains storage-agnostic and only consumes backend-provided URLs.
- The architecture is ready for future CDN usage without changing API contracts.

**Trade-offs**

- Requires an explicit custom upload view for markdown editor uploads.
- Requires path conventions and security checks for admin/editorial uploads.
- Introduces a bit more upfront structure than a purely ad-hoc local media setup.

## Alternatives Considered

1. Use local filesystem now and refactor to S3 later

   Rejected because it would create unnecessary refactoring risk in upload logic and media URL handling.

2. Store markdown images in ProductImage

   Rejected because markdown/editorial assets are not the same domain concept as structured product gallery assets.

3. Use separate storage backends for gallery and markdown from the start

   Rejected because a single storage abstraction with separate paths is simpler and sufficient at this stage.

## Notes

The markdown upload endpoint must be protected appropriately for admin/editorial use and should validate file type and size.

Suggested path conventions:

- `products/gallery/`
- `products/descriptions/`

This ADR covers storage architecture only. Product descriptions, gallery data model, and API/serializer behavior are addressed in subsequent implementation work.
