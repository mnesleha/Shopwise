/**
 * ProductCard — image rendering (Type A, tests A–B)
 *
 * Tests A: Catalogue card renders the primary_image thumbnail.
 * Tests B: Catalogue card renders the "No image" placeholder when no image.
 *
 * Rendered through ProductGrid (ProductCard is a private sub-component).
 */

import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { ProductGrid } from "@/components/product/ProductGrid";
import { makeProduct, makeProductImage } from "../helpers/fixtures";
import { productCard } from "../helpers/testIds";

// ── Shared test props builder ─────────────────────────────────────────────────

function buildProps(
  overrides?: Partial<React.ComponentProps<typeof ProductGrid>>,
): React.ComponentProps<typeof ProductGrid> {
  return {
    products: [makeProduct({ id: "1" })],
    page: 1,
    pageSize: 10,
    totalItems: 1,
    onPageChange: vi.fn(),
    onAddToCart: vi.fn(),
    onOpenProduct: vi.fn(),
    ...overrides,
  };
}

// ── Test A: Card renders primary image ────────────────────────────────────────

describe("ProductCard — A: renders primary image thumbnail", () => {
  it("renders an <img> with the thumb URL when primaryImage is provided", () => {
    const primaryImage = makeProductImage({
      id: 1,
      variants: {
        thumb: "https://example.com/products/1/thumb.jpg",
        medium: "https://example.com/products/1/medium.jpg",
        large: "https://example.com/products/1/large.jpg",
        full: "https://example.com/products/1/full.jpg",
      },
      alt: "Ergonomic Mouse",
    });

    const product = makeProduct({
      id: "1",
      name: "Ergonomic Mouse",
      primaryImage,
    });
    render(
      <ProductGrid {...buildProps({ products: [product], totalItems: 1 })} />,
    );

    const card = screen.getByTestId(productCard("1"));
    const img = within(card).getByRole("img");

    expect(img).toHaveAttribute(
      "src",
      "https://example.com/products/1/thumb.jpg",
    );
    expect(img).toHaveAttribute("alt", "Ergonomic Mouse");
  });

  it("uses primaryImage alt when it differs from product name", () => {
    const primaryImage = makeProductImage({
      alt: "Ergonomic Mouse - front angle view",
    });

    const product = makeProduct({
      id: "1",
      name: "Ergonomic Mouse",
      primaryImage,
    });
    render(
      <ProductGrid {...buildProps({ products: [product], totalItems: 1 })} />,
    );

    const card = screen.getByTestId(productCard("1"));
    const img = within(card).getByRole("img");

    expect(img).toHaveAttribute("alt", "Ergonomic Mouse - front angle view");
  });
});

// ── Test B: Card renders placeholder when no image ────────────────────────────

describe("ProductCard — B: renders placeholder when no image data", () => {
  it("shows 'No image' text when neither primaryImage nor imageUrl is set", () => {
    const product = makeProduct({
      id: "1",
      primaryImage: undefined,
      imageUrl: undefined,
    });
    render(
      <ProductGrid {...buildProps({ products: [product], totalItems: 1 })} />,
    );

    const card = screen.getByTestId(productCard("1"));
    expect(within(card).getByText("No image")).toBeInTheDocument();
    expect(within(card).queryByRole("img")).not.toBeInTheDocument();
  });

  it("falls back to imageUrl when primaryImage is absent but imageUrl is set", () => {
    const product = makeProduct({
      id: "1",
      primaryImage: undefined,
      imageUrl: "https://example.com/legacy.jpg",
    });
    render(
      <ProductGrid {...buildProps({ products: [product], totalItems: 1 })} />,
    );

    const card = screen.getByTestId(productCard("1"));
    const img = within(card).getByRole("img");

    expect(img).toHaveAttribute("src", "https://example.com/legacy.jpg");
  });
});
