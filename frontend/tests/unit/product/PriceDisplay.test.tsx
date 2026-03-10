/**
 * PriceDisplay — unit tests
 *
 * Covers:
 * - formatCurrency: symbol/code + non-breaking space + amount
 * - DiscountBadge: renders label with correct testid
 * - PriceDisplay (no discount): only discounted-price rendered, foreground colour
 * - PriceDisplay (with discount): original struck-through, emerald discounted, badge
 */

import * as React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  formatCurrency,
  DiscountBadge,
  PriceDisplay,
} from "@/components/ui/PriceDisplay";

// ---------------------------------------------------------------------------
// formatCurrency
// ---------------------------------------------------------------------------

describe("formatCurrency", () => {
  it("renders USD as '$\u00a0amount'", () => {
    expect(formatCurrency("USD", "12.50")).toBe("$\u00a012.50");
  });

  it("renders EUR as 'EUR\u00a0amount'", () => {
    expect(formatCurrency("EUR", "9.99")).toBe("EUR\u00a09.99");
  });

  it("renders unknown currency code verbatim", () => {
    expect(formatCurrency("PLN", "50.00")).toBe("PLN\u00a050.00");
  });

  it("uses a non-breaking space (U+00A0), not a regular space", () => {
    const result = formatCurrency("EUR", "1.00");
    expect(result.includes("\u00a0")).toBe(true);
    expect(result.includes(" ")).toBe(false); // no ordinary space
  });
});

// ---------------------------------------------------------------------------
// DiscountBadge
// ---------------------------------------------------------------------------

describe("DiscountBadge", () => {
  it("renders the discount label", () => {
    render(<DiscountBadge label="–10%" />);
    expect(screen.getByTestId("discount-badge")).toHaveTextContent("–10%");
  });

  it("renders a fixed-amount label", () => {
    render(<DiscountBadge label="–EUR\u00a05.00" />);
    expect(screen.getByTestId("discount-badge")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PriceDisplay — no discount
// ---------------------------------------------------------------------------

describe("PriceDisplay — no discount", () => {
  it("renders the formatted price in the discounted-price slot", () => {
    render(<PriceDisplay currency="EUR" price="49.99" />);
    const el = screen.getByTestId("discounted-price");
    expect(el).toHaveTextContent("49.99");
    expect(el).toHaveTextContent("EUR");
  });

  it("does not render an original-price element", () => {
    render(<PriceDisplay currency="EUR" price="49.99" />);
    expect(screen.queryByTestId("original-price")).not.toBeInTheDocument();
  });

  it("does not render a discount-badge element", () => {
    render(<PriceDisplay currency="EUR" price="49.99" />);
    expect(screen.queryByTestId("discount-badge")).not.toBeInTheDocument();
  });

  it("renders the price-display container", () => {
    render(<PriceDisplay currency="EUR" price="49.99" />);
    expect(screen.getByTestId("price-display")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PriceDisplay — with discount
// ---------------------------------------------------------------------------

describe("PriceDisplay — with discount", () => {
  function renderWithDiscount() {
    render(
      <PriceDisplay
        currency="EUR"
        price="44.99"
        originalPrice="49.99"
        discountLabel="–10%"
      />,
    );
  }

  it("renders the original price struck-through", () => {
    renderWithDiscount();
    const orig = screen.getByTestId("original-price");
    expect(orig).toHaveTextContent("49.99");
    expect(orig.className).toContain("line-through");
  });

  it("renders the discounted price", () => {
    renderWithDiscount();
    const discounted = screen.getByTestId("discounted-price");
    expect(discounted).toHaveTextContent("44.99");
  });

  it("gives the discounted price an emerald colour class", () => {
    renderWithDiscount();
    const discounted = screen.getByTestId("discounted-price");
    expect(discounted.className).toContain("emerald");
  });

  it("renders the discount badge with the label", () => {
    renderWithDiscount();
    expect(screen.getByTestId("discount-badge")).toHaveTextContent("–10%");
  });

  it("does not trigger discount display when price equals originalPrice", () => {
    render(
      <PriceDisplay
        currency="EUR"
        price="49.99"
        originalPrice="49.99"
        discountLabel="–10%"
      />,
    );
    expect(screen.queryByTestId("original-price")).not.toBeInTheDocument();
  });

  it("does not trigger discount display when discountLabel is absent", () => {
    render(
      <PriceDisplay
        currency="EUR"
        price="44.99"
        originalPrice="49.99"
        // no discountLabel
      />,
    );
    expect(screen.queryByTestId("original-price")).not.toBeInTheDocument();
    expect(screen.queryByTestId("discount-badge")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PriceDisplay — size variants
// ---------------------------------------------------------------------------

describe("PriceDisplay — size variants", () => {
  it("applies text-xl for size='md' (default)", () => {
    render(<PriceDisplay currency="USD" price="10.00" />);
    expect(screen.getByTestId("discounted-price").className).toContain(
      "text-xl",
    );
  });

  it("applies text-3xl for size='lg'", () => {
    render(<PriceDisplay currency="USD" price="10.00" size="lg" />);
    expect(screen.getByTestId("discounted-price").className).toContain(
      "text-3xl",
    );
  });

  it("applies text-sm for size='sm'", () => {
    render(<PriceDisplay currency="USD" price="10.00" size="sm" />);
    expect(screen.getByTestId("discounted-price").className).toContain(
      "text-sm",
    );
  });
});
