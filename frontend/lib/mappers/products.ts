// ---------------------------------------------------------------------------
// Image variant types — mirrors the VersatileImageField serializer output.
// FE must never construct media URLs manually; always use these from the API.
// ---------------------------------------------------------------------------

/** URL variants produced by the backend VersatileImageField serializer. */
export type ProductImageVariantsDto = {
  thumb: string;
  medium: string;
  large: string;
  full: string;
};

/** A single gallery image as returned by the backend. */
export type ProductImageDto = {
  id: number;
  image: ProductImageVariantsDto;
  alt_text: string;
  sort_order: number;
};

// ---------------------------------------------------------------------------
// DTOs — shape of raw API responses
// ---------------------------------------------------------------------------

export type ProductListItemDto = {
  id: number;
  name: string;
  price: string;
  stock_quantity: number;
  short_description: string;
  stock_status: "IN_STOCK" | "LOW_STOCK" | "OUT_OF_STOCK";
  /** Hero image for catalogue cards; null when no primary image is set. */
  primary_image: ProductImageDto | null;
};

/** Catalogue list response — wrapped envelope from /api/v1/products/. */
export type CatalogueResponseDto = {
  results: ProductListItemDto[];
  metadata: {
    price_min_available: string | null;
    price_max_available: string | null;
  };
};

export type ProductDetailDto = {
  id: number;
  name: string;
  price: string;
  stock_quantity: number;
  short_description: string;
  full_description: string;
  /** Hero image (same shape as gallery items). */
  primary_image: ProductImageDto | null;
  /** Full gallery ordered by sort_order, id. */
  gallery_images: ProductImageDto[];
};

// ---------------------------------------------------------------------------
// View Model types — shape consumed by React components
// ---------------------------------------------------------------------------

/** Ready-to-render URL variants. All values are absolute URLs from the API. */
export type ProductImageVariantsVm = {
  thumb: string;
  medium: string;
  large: string;
  full: string;
};

/** A single gallery slide as passed to components. */
export type ProductImageVm = {
  id: number;
  variants: ProductImageVariantsVm;
  alt: string;
  sortOrder: number;
};

export type ProductGridItem = {
  id: string;
  name: string;
  shortDescription?: string;
  price: string;
  currency?: string;
  stockQuantity: number;
  imageUrl?: string;
  /** Structured primary image for use with next/image. */
  primaryImage?: ProductImageVm;
};

export type ProductDetailVm = {
  id: string;
  name: string;
  shortDescription: string;
  fullDescription: string;
  description?: string; // kept for backward-compat with existing tests
  price: string;
  currency?: string;
  stockQuantity: number;
  images?: string[];
  /** Structured gallery for the new ProductGallery component. */
  gallery: ProductImageVm[];
  specs?: Array<{ label: string; value: string }>;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mapProductImage(dto: ProductImageDto): ProductImageVm {
  return {
    id: dto.id,
    variants: {
      thumb: dto.image.thumb,
      medium: dto.image.medium,
      large: dto.image.large,
      full: dto.image.full,
    },
    alt: dto.alt_text,
    sortOrder: dto.sort_order,
  };
}

// ---------------------------------------------------------------------------
// Mapper functions
// ---------------------------------------------------------------------------

export function mapProductToGridItem(dto: ProductListItemDto): ProductGridItem {
  return {
    id: String(dto.id),
    name: dto.name,
    price: dto.price,
    currency: "USD",
    stockQuantity: dto.stock_quantity,
    shortDescription: dto.short_description,
    imageUrl: dto.primary_image?.image.thumb ?? "",
    primaryImage: dto.primary_image
      ? mapProductImage(dto.primary_image)
      : undefined,
  };
}

export function mapProductToDetailVm(dto: ProductDetailDto): ProductDetailVm {
  const gallery = dto.gallery_images.map(mapProductImage);
  return {
    id: String(dto.id),
    name: dto.name,
    price: dto.price,
    currency: "USD",
    stockQuantity: dto.stock_quantity,
    shortDescription: dto.short_description,
    fullDescription: dto.full_description,
    gallery,
    // Backward-compat string array for any consumers that still use images[].
    images: gallery.map((img) => img.variants.full),
    // Specs: future extension point.
    specs: [],
  };
}

/** @deprecated Use gallery from mapProductToDetailVm instead. */
function mapProductImages(dto: ProductDetailDto): string[] {
  if (dto.gallery_images.length > 0) {
    return dto.gallery_images.map((img) => img.image.full);
  }

  // No images yet
  return [];
}
