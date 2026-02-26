/**
 * ProductDetail — Type A (Presentational)
 *
 * Tests the ProductDetail component in isolation: product information display,
 * stock status, callbacks, description, specs, and image gallery.
 * No routing or API calls.
 */

import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProductDetail } from "@/components/product/ProductDetail";
import { makeProduct } from "../helpers/fixtures";

// ── Default props ─────────────────────────────────────────────────────────────

function buildProps(
  overrides?: Partial<React.ComponentProps<typeof ProductDetail>>
): React.ComponentProps<typeof ProductDetail> {
  return {
    product: makeProduct(),
    onAddToCart: vi.fn(),
    onBack: vi.fn(),
    ...overrides,
  };
}

// ── Product information ───────────────────────────────────────────────────────

describe("ProductDetail — product information", () => {
  it("renders the product name in a heading", () => {
    render(<ProductDetail {...buildProps({ product: makeProduct({ name: "Fancy Keyboard" }) })} />);

    expect(screen.getByRole("heading", { name: "Fancy Keyboard" })).toBeInTheDocument();
  });

  it("renders the product price", () => {
    render(<ProductDetail {...buildProps({ product: makeProduct({ price: "49.99" }) })} />);

    expect(screen.getByText(/49\.99/)).toBeInTheDocument();
  });

  it("shows 'In stock' badge when stockQuantity > 0", () => {
    render(<ProductDetail {...buildProps({ product: makeProduct({ stockQuantity: 5 }) })} />);

    expect(screen.getByText("In stock")).toBeInTheDocument();
  });

  it("shows 'Out of stock' badge when stockQuantity === 0", () => {
    render(<ProductDetail {...buildProps({ product: makeProduct({ stockQuantity: 0 }) })} />);

    expect(screen.getByText("Out of stock")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(
      <ProductDetail
        {...buildProps({
          product: makeProduct({ description: "A great mechanical keyboard." }),
        })}
      />
    );

    expect(screen.getByText("A great mechanical keyboard.")).toBeInTheDocument();
  });

  it("does not render description section when description is absent", () => {
    render(
      <ProductDetail
        {...buildProps({ product: makeProduct({ description: undefined }) })}
      />
    );

    expect(screen.queryByText(/description/i)).not.toBeInTheDocument();
  });

  it("renders spec labels and values when specs are provided", () => {
    render(
      <ProductDetail
        {...buildProps({
          product: makeProduct({
            specs: [
              { label: "Weight", value: "120g" },
              { label: "Connectivity", value: "Bluetooth" },
            ],
          }),
        })}
      />
    );

    expect(screen.getByText("Weight")).toBeInTheDocument();
    expect(screen.getByText("120g")).toBeInTheDocument();
    expect(screen.getByText("Connectivity")).toBeInTheDocument();
    expect(screen.getByText("Bluetooth")).toBeInTheDocument();
  });

  it("does not render specs section when specs array is empty", () => {
    render(
      <ProductDetail
        {...buildProps({ product: makeProduct({ specs: [] }) })}
      />
    );

    expect(screen.queryByText(/specifications/i)).not.toBeInTheDocument();
  });
});

// ── Add-to-cart button ────────────────────────────────────────────────────────

describe("ProductDetail — add-to-cart button", () => {
  it("add-to-cart button is enabled when in stock", () => {
    render(<ProductDetail {...buildProps({ product: makeProduct({ stockQuantity: 3 }) })} />);

    expect(
      screen.getByRole("button", { name: /add to cart/i })
    ).not.toBeDisabled();
  });

  it("add-to-cart button is disabled when out of stock", () => {
    render(<ProductDetail {...buildProps({ product: makeProduct({ stockQuantity: 0 }) })} />);

    expect(
      screen.getByRole("button", { name: /add to cart/i })
    ).toBeDisabled();
  });

  it("calls onAddToCart with the product id when clicked", async () => {
    const user = userEvent.setup();
    const onAddToCart = vi.fn();
    const product = makeProduct({ id: "99", stockQuantity: 10 });
    render(<ProductDetail {...buildProps({ product, onAddToCart })} />);

    await user.click(screen.getByRole("button", { name: /add to cart/i }));

    expect(onAddToCart).toHaveBeenCalledOnce();
    expect(onAddToCart).toHaveBeenCalledWith("99");
  });

  it("does not call onAddToCart when out of stock (button disabled)", async () => {
    const user = userEvent.setup();
    const onAddToCart = vi.fn();
    render(
      <ProductDetail
        {...buildProps({
          product: makeProduct({ stockQuantity: 0 }),
          onAddToCart,
        })}
      />
    );

    // Clicking a disabled button should not fire the handler
    const btn = screen.getByRole("button", { name: /add to cart/i });
    await user.click(btn);

    expect(onAddToCart).not.toHaveBeenCalled();
  });
});

// ── Back button ───────────────────────────────────────────────────────────────

describe("ProductDetail — back button", () => {
  it("renders at least one back button", () => {
    render(<ProductDetail {...buildProps()} />);

    const backButtons = screen.getAllByRole("button", { name: /back/i });
    expect(backButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("calls onBack when the top back button is clicked", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<ProductDetail {...buildProps({ onBack })} />);

    const backButtons = screen.getAllByRole("button", { name: /back/i });
    await user.click(backButtons[0]);

    expect(onBack).toHaveBeenCalledOnce();
  });

  it("calls onBack when the bottom back button is clicked", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<ProductDetail {...buildProps({ onBack })} />);

    const backButtons = screen.getAllByRole("button", { name: /back/i });
    // Bottom "Back" button is the last one
    await user.click(backButtons[backButtons.length - 1]);

    expect(onBack).toHaveBeenCalledOnce();
  });
});

// ── Image gallery ─────────────────────────────────────────────────────────────

describe("ProductDetail — image gallery", () => {
  it("renders main image when images array has one entry", () => {
    const product = makeProduct({
      name: "Mouse",
      images: ["https://example.com/mouse.jpg"],
    });
    render(<ProductDetail {...buildProps({ product })} />);

    const img = screen.getByAltText("Mouse - Image 1");
    expect(img).toBeInTheDocument();
  });

  it("does not render thumbnail strip when there is only one image", () => {
    const product = makeProduct({
      name: "Mouse",
      images: ["https://example.com/mouse.jpg"],
    });
    render(<ProductDetail {...buildProps({ product })} />);

    // Only one image → no thumbnail buttons
    expect(screen.queryByLabelText(/view image 2/i)).not.toBeInTheDocument();
  });

  it("renders thumbnail buttons when there are multiple images", () => {
    const product = makeProduct({
      name: "Mouse",
      images: [
        "https://example.com/mouse1.jpg",
        "https://example.com/mouse2.jpg",
        "https://example.com/mouse3.jpg",
      ],
    });
    render(<ProductDetail {...buildProps({ product })} />);

    expect(screen.getByLabelText("View image 1")).toBeInTheDocument();
    expect(screen.getByLabelText("View image 2")).toBeInTheDocument();
    expect(screen.getByLabelText("View image 3")).toBeInTheDocument();
  });

  it("clicking a thumbnail changes the main image", async () => {
    const user = userEvent.setup();
    const product = makeProduct({
      name: "Mouse",
      images: [
        "https://example.com/mouse1.jpg",
        "https://example.com/mouse2.jpg",
      ],
    });
    render(<ProductDetail {...buildProps({ product })} />);

    // Initially shows image 1
    expect(screen.getByAltText("Mouse - Image 1")).toBeInTheDocument();

    // Click thumbnail 2
    await user.click(screen.getByLabelText("View image 2"));

    // Main image should now be image 2
    expect(screen.getByAltText("Mouse - Image 2")).toBeInTheDocument();
  });

  it("shows placeholder when no images are provided", () => {
    const product = makeProduct({ images: undefined });
    render(<ProductDetail {...buildProps({ product })} />);

    expect(screen.getByText(/no image available/i)).toBeInTheDocument();
  });
});
