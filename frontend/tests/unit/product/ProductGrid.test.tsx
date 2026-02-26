/**
 * ProductGrid — Type A (Presentational)
 *
 * Tests the ProductGrid component in isolation: product cards, stock badges,
 * callbacks, pagination, and empty state. No routing or API calls.
 */

import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProductGrid } from "@/components/product/ProductGrid";
import { makeProduct } from "../helpers/fixtures";
import { productCard, addToCart } from "../helpers/testIds";

// ── Default props ─────────────────────────────────────────────────────────────

function buildProps(
  overrides?: Partial<React.ComponentProps<typeof ProductGrid>>
): React.ComponentProps<typeof ProductGrid> {
  return {
    products: [makeProduct({ id: "1", name: "Test Mouse", price: "29.99" })],
    page: 1,
    pageSize: 10,
    totalItems: 1,
    onPageChange: vi.fn(),
    onAddToCart: vi.fn(),
    onOpenProduct: vi.fn(),
    ...overrides,
  };
}

// ── Rendering ─────────────────────────────────────────────────────────────────

describe("ProductGrid — rendering", () => {
  it("renders a card for each product with the correct testid", () => {
    const products = [
      makeProduct({ id: "1", name: "Mouse" }),
      makeProduct({ id: "2", name: "Keyboard" }),
    ];
    render(<ProductGrid {...buildProps({ products, totalItems: 2 })} />);

    expect(screen.getByTestId(productCard("1"))).toBeInTheDocument();
    expect(screen.getByTestId(productCard("2"))).toBeInTheDocument();
  });

  it("renders product name and price inside the card", () => {
    const product = makeProduct({ id: "42", name: "Fancy Mouse", price: "99.00" });
    render(<ProductGrid {...buildProps({ products: [product], totalItems: 1 })} />);

    const card = screen.getByTestId(productCard("42"));
    expect(within(card).getByText("Fancy Mouse")).toBeInTheDocument();
    expect(within(card).getByText(/99\.00/)).toBeInTheDocument();
  });

  it("shows 'In stock' badge for a product with stockQuantity > 0", () => {
    const product = makeProduct({ id: "1", stockQuantity: 5 });
    render(<ProductGrid {...buildProps({ products: [product] })} />);

    const card = screen.getByTestId(productCard("1"));
    expect(within(card).getByText("In stock")).toBeInTheDocument();
  });

  it("shows 'Out of stock' badge for a product with stockQuantity === 0", () => {
    const product = makeProduct({ id: "1", stockQuantity: 0 });
    render(<ProductGrid {...buildProps({ products: [product] })} />);

    const card = screen.getByTestId(productCard("1"));
    expect(within(card).getByText("Out of stock")).toBeInTheDocument();
  });

  it("renders shortDescription when provided", () => {
    const product = makeProduct({ id: "1", shortDescription: "Great device" });
    render(<ProductGrid {...buildProps({ products: [product] })} />);

    expect(screen.getByText("Great device")).toBeInTheDocument();
  });

  it("renders empty-state message when products array is empty", () => {
    render(<ProductGrid {...buildProps({ products: [], totalItems: 0 })} />);

    expect(screen.getByText(/no products found/i)).toBeInTheDocument();
  });
});

// ── Add-to-cart button ────────────────────────────────────────────────────────

describe("ProductGrid — add-to-cart button", () => {
  it("add-to-cart button is enabled for an in-stock product", () => {
    const product = makeProduct({ id: "1", stockQuantity: 5 });
    render(<ProductGrid {...buildProps({ products: [product] })} />);

    const btn = screen.getByTestId(addToCart("1"));
    expect(btn).not.toBeDisabled();
  });

  it("add-to-cart button is disabled for an out-of-stock product", () => {
    const product = makeProduct({ id: "1", stockQuantity: 0 });
    render(<ProductGrid {...buildProps({ products: [product] })} />);

    const btn = screen.getByTestId(addToCart("1"));
    expect(btn).toBeDisabled();
  });

  it("calls onAddToCart with the product id when clicked", async () => {
    const user = userEvent.setup();
    const onAddToCart = vi.fn();
    const product = makeProduct({ id: "7", stockQuantity: 3 });
    render(<ProductGrid {...buildProps({ products: [product], onAddToCart })} />);

    await user.click(screen.getByTestId(addToCart("7")));

    expect(onAddToCart).toHaveBeenCalledOnce();
    expect(onAddToCart).toHaveBeenCalledWith("7");
  });

  it("does NOT call onOpenProduct when add-to-cart is clicked (stopPropagation)", async () => {
    const user = userEvent.setup();
    const onAddToCart = vi.fn();
    const onOpenProduct = vi.fn();
    const product = makeProduct({ id: "1", stockQuantity: 3 });
    render(
      <ProductGrid
        {...buildProps({ products: [product], onAddToCart, onOpenProduct })}
      />
    );

    await user.click(screen.getByTestId(addToCart("1")));

    expect(onAddToCart).toHaveBeenCalledOnce();
    expect(onOpenProduct).not.toHaveBeenCalled();
  });
});

// ── openProduct callbacks ─────────────────────────────────────────────────────

describe("ProductGrid — openProduct callbacks", () => {
  it("calls onOpenProduct when the card body is clicked", async () => {
    const user = userEvent.setup();
    const onOpenProduct = vi.fn();
    const product = makeProduct({ id: "3", name: "Click Me" });
    render(<ProductGrid {...buildProps({ products: [product], onOpenProduct })} />);

    // Click the product name text (inside the card, but not the button)
    await user.click(screen.getByText("Click Me"));

    expect(onOpenProduct).toHaveBeenCalledOnce();
    expect(onOpenProduct).toHaveBeenCalledWith("3");
  });

  it("calls onOpenProduct when 'View details' is clicked", async () => {
    const user = userEvent.setup();
    const onOpenProduct = vi.fn();
    const product = makeProduct({ id: "5" });
    render(<ProductGrid {...buildProps({ products: [product], onOpenProduct })} />);

    await user.click(screen.getByRole("button", { name: /view details/i }));

    expect(onOpenProduct).toHaveBeenCalledOnce();
    expect(onOpenProduct).toHaveBeenCalledWith("5");
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────

describe("ProductGrid — pagination", () => {
  it("shows 'Page 1 of 1' when there is one page", () => {
    render(<ProductGrid {...buildProps({ page: 1, pageSize: 10, totalItems: 5 })} />);

    expect(screen.getByText(/page 1 of 1/i)).toBeInTheDocument();
  });

  it("Previous button is disabled on page 1", () => {
    render(<ProductGrid {...buildProps({ page: 1 })} />);

    expect(
      screen.getByRole("button", { name: /go to previous page/i })
    ).toBeDisabled();
  });

  it("Next button is disabled when on the last page", () => {
    render(
      <ProductGrid {...buildProps({ page: 2, pageSize: 10, totalItems: 15 })} />
    );

    expect(
      screen.getByRole("button", { name: /go to next page/i })
    ).toBeDisabled();
  });

  it("Next button is enabled when more pages exist", () => {
    render(
      <ProductGrid {...buildProps({ page: 1, pageSize: 10, totalItems: 25 })} />
    );

    expect(
      screen.getByRole("button", { name: /go to next page/i })
    ).not.toBeDisabled();
  });

  it("clicking Next calls onPageChange with page + 1", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(
      <ProductGrid
        {...buildProps({ page: 1, pageSize: 10, totalItems: 25, onPageChange })}
      />
    );

    await user.click(screen.getByRole("button", { name: /go to next page/i }));

    expect(onPageChange).toHaveBeenCalledOnce();
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("clicking Previous calls onPageChange with page - 1", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(
      <ProductGrid
        {...buildProps({ page: 3, pageSize: 10, totalItems: 50, onPageChange })}
      />
    );

    await user.click(screen.getByRole("button", { name: /go to previous page/i }));

    expect(onPageChange).toHaveBeenCalledOnce();
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("displays total items count", () => {
    render(<ProductGrid {...buildProps({ totalItems: 42 })} />);

    expect(screen.getByText(/42 items total/i)).toBeInTheDocument();
  });

  it("displays singular 'item' when totalItems is 1", () => {
    render(
      <ProductGrid
        {...buildProps({ totalItems: 1, products: [makeProduct({ id: "1" })] })}
      />
    );

    expect(screen.getByText(/1 item total/i)).toBeInTheDocument();
  });
});
