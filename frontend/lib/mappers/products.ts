export type ProductListItemDto = {
  id: number;
  name: string;
  price: string;
  stock_quantity: number;
  short_description: string;
};

export type ProductDetailDto = {
  id: number;
  name: string;
  price: string;
  stock_quantity: number;
  short_description: string;
  full_description: string;
  preview_image_url?: string;
  images?: Array<{
    url: string;
    alt_text?: string;
    sort_order?: number;
  }>;
};

export type ProductGridItem = {
  id: string;
  name: string;
  shortDescription?: string;
  price: string;
  currency?: string;
  stockQuantity: number;
  imageUrl?: string;
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
  specs?: Array<{ label: string; value: string }>;
};

export function mapProductToGridItem(dto: ProductListItemDto): ProductGridItem {
  return {
    id: String(dto.id),
    name: dto.name,
    price: dto.price,
    currency: "USD",
    stockQuantity: dto.stock_quantity,
    shortDescription: dto.short_description,
    imageUrl: "", // TODO: backend preview image URL
  };
}

export function mapProductToDetailVm(dto: ProductDetailDto): ProductDetailVm {
  return {
    id: String(dto.id),
    name: dto.name,
    price: dto.price,
    currency: "USD",
    stockQuantity: dto.stock_quantity,
    shortDescription: dto.short_description,
    fullDescription: dto.full_description,
    // Images:
    // - today: preview image if exists
    // - future: full gallery
    images: mapProductImages(dto),
    // Specs:
    // - future extension point (variants, attributes, etc.)
    specs: [],
  };
}

function mapProductImages(dto: ProductDetailDto): string[] {
  // Future: explicit gallery from backend
  if (dto.images && dto.images.length > 0) {
    return dto.images
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
      .map((img) => img.url);
  }

  // MVP fallback: single preview image
  if (dto.preview_image_url) {
    return [dto.preview_image_url];
  }

  // No images yet
  return [];
}
