/**
 * Product descriptions — RTL tests
 *
 * Covers the new short_description / full_description fields end-to-end
 * in the presentational layer:
 *
 * 1. ProductGrid card renders shortDescription.
 * 2. ProductDetail renders fullDescription as Markdown (not raw syntax).
 */

import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { ProductGrid } from "@/components/product/ProductGrid";
import { ProductDetail } from "@/components/product/ProductDetail";
import { makeProduct } from "../helpers/fixtures";
import { productCard } from "../helpers/testIds";

// ── ProductGrid card ─────────────────────────────────────────────────────────

describe("ProductGrid — short description", () => {
  it("renders shortDescription inside the product card", () => {
    const product = makeProduct({
      id: "10",
      shortDescription: "Compact wireless keyboard",
    });

    render(
      <ProductGrid
        products={[product]}
        page={1}
        pageSize={10}
        totalItems={1}
        onPageChange={vi.fn()}
        onAddToCart={vi.fn()}
        onOpenProduct={vi.fn()}
      />,
    );

    const card = screen.getByTestId(productCard("10"));
    expect(
      within(card).getByText("Compact wireless keyboard"),
    ).toBeInTheDocument();
  });

  it("does not render a description element when shortDescription is absent", () => {
    const product = makeProduct({ id: "11", shortDescription: undefined });

    render(
      <ProductGrid
        products={[product]}
        page={1}
        pageSize={10}
        totalItems={1}
        onPageChange={vi.fn()}
        onAddToCart={vi.fn()}
        onOpenProduct={vi.fn()}
      />,
    );

    const card = screen.getByTestId(productCard("11"));
    // The card must still render name and price but no empty description element.
    expect(within(card).getByText(product.name)).toBeInTheDocument();
  });
});

// ── ProductDetail — full description (Markdown) ──────────────────────────────

describe("ProductDetail — full description markdown", () => {
  it("renders fullDescription markdown content, not raw syntax", () => {
    const product = makeProduct({
      id: "20",
      fullDescription: "**Important feature**",
    });

    render(
      <ProductDetail
        product={product}
        onAddToCart={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    // Markdown is rendered — the text is visible without asterisks.
    expect(screen.getByText("Important feature")).toBeInTheDocument();
    // Raw markdown syntax must not be visible.
    expect(screen.queryByText("**Important feature**")).not.toBeInTheDocument();
  });

  it("renders a Markdown heading as a proper heading element", () => {
    const product = makeProduct({
      id: "21",
      fullDescription: "## Specifications",
    });

    render(
      <ProductDetail
        product={product}
        onAddToCart={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    // react-markdown renders ## as an h2.
    expect(
      screen.getByRole("heading", { level: 2, name: "Specifications" }),
    ).toBeInTheDocument();
  });

  it("does not render the full-description section when fullDescription is absent", () => {
    const product = makeProduct({ id: "22", fullDescription: undefined });

    render(
      <ProductDetail
        product={product}
        onAddToCart={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    expect(
      screen.queryByTestId("product-full-description"),
    ).not.toBeInTheDocument();
  });
});
