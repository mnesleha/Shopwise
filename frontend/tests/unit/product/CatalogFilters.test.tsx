/**
 * CatalogFilters — SortDropdown, ActiveFilterChips, CatalogFilterPanel
 *
 * Tests URL-param reading and writing behavior of the three catalogue
 * filter components. Mocks next/navigation throughout.
 *
 * NOTE: shadcn <Select> uses Radix UI which relies on pointer-capture events
 * not provided by jsdom. We stub the UI select primitives with a plain
 * <select> so we can test our own onValueChange logic without fighting the
 * environment.
 */

import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createRouterMock } from "../helpers/nextNavigation";

// ── Mock shadcn Select with a plain <select> ──────────────────────────────────
vi.mock("@/components/ui/select", () => {
  const Select = ({
    value,
    onValueChange,
    children,
  }: {
    value?: string;
    onValueChange?: (v: string) => void;
    children?: React.ReactNode;
  }) => (
    <select
      data-testid="sort-select"
      value={value}
      onChange={(e) => onValueChange?.(e.target.value)}
    >
      {children}
    </select>
  );

  const SelectTrigger = ({ children }: { children?: React.ReactNode }) => (
    <>{children}</>
  );
  const SelectValue = ({ placeholder }: { placeholder?: string }) => (
    <option value="">{placeholder}</option>
  );
  const SelectContent = ({ children }: { children?: React.ReactNode }) => (
    <>{children}</>
  );
  const SelectItem = ({
    value,
    children,
  }: {
    value: string;
    children?: React.ReactNode;
  }) => <option value={value}>{children}</option>;

  return { Select, SelectTrigger, SelectValue, SelectContent, SelectItem };
});

// ── Shared mock state ─────────────────────────────────────────────────────────

const mockRouter = createRouterMock();
let mockParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => mockParams,
  usePathname: () => "/products",
}));

// ── Import components after mocks ─────────────────────────────────────────────

import SortDropdown from "@/components/product/SortDropdown";
import ActiveFilterChips from "@/components/product/ActiveFilterChips";
import CatalogFilterPanel from "@/components/product/CatalogFilterPanel";

// ── Helpers ───────────────────────────────────────────────────────────────────

const CATEGORIES = [
  { id: 1, name: "Electronics" },
  { id: 2, name: "Clothing" },
  { id: 3, name: "Books" },
];

function setParams(init: string | Record<string, string> | [string, string][]) {
  mockParams = new URLSearchParams(
    init as ConstructorParameters<typeof URLSearchParams>[0],
  );
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  setParams("");
});

// ── SortDropdown ──────────────────────────────────────────────────────────────

describe("SortDropdown", () => {
  it("renders the sort select with correct options", () => {
    render(<SortDropdown />);
    const select = screen.getByTestId("sort-select") as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    // All option labels present
    expect(screen.getByText("Price: Low to High")).toBeInTheDocument();
    expect(screen.getByText("Price: High to Low")).toBeInTheDocument();
    expect(screen.getByText("Name: A to Z")).toBeInTheDocument();
    expect(screen.getByText("Name: Z to A")).toBeInTheDocument();
  });

  it("calls router.replace with sort param when an option is selected", () => {
    render(<SortDropdown />);
    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "price_asc" } });

    expect(mockRouter.replace).toHaveBeenCalledOnce();
    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).toContain("sort=price_asc");
  });

  it("removes sort param and resets page when Default (__none__) is selected", () => {
    setParams("sort=price_desc&page=3");
    render(<SortDropdown />);
    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "__none__" } });

    expect(mockRouter.replace).toHaveBeenCalledOnce();
    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).not.toContain("sort=");
    expect(url).not.toContain("page=");
  });

  it("resets page param when sort changes", () => {
    setParams("sort=price_asc&page=2");
    render(<SortDropdown />);
    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "price_desc" } });

    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).toContain("sort=price_desc");
    expect(url).not.toContain("page=");
  });
});

// ── ActiveFilterChips ─────────────────────────────────────────────────────────

describe("ActiveFilterChips", () => {
  it("renders nothing when no filters are active", () => {
    const { container } = render(<ActiveFilterChips categories={CATEGORIES} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a chip per active category", () => {
    setParams("category=1&category=2");
    render(<ActiveFilterChips categories={CATEGORIES} />);

    expect(screen.getByTestId("chip-category-1")).toBeInTheDocument();
    expect(screen.getByTestId("chip-category-2")).toBeInTheDocument();
    expect(screen.queryByTestId("chip-category-3")).not.toBeInTheDocument();
  });

  it("shows category name in the chip", () => {
    setParams("category=1");
    render(<ActiveFilterChips categories={CATEGORIES} />);
    expect(screen.getByTestId("chip-category-1")).toHaveTextContent(
      "Electronics",
    );
  });

  it("renders price chips when min/max are set", () => {
    setParams("min_price=10&max_price=99");
    render(<ActiveFilterChips categories={CATEGORIES} />);
    expect(screen.getByTestId("chip-min-price")).toBeInTheDocument();
    expect(screen.getByTestId("chip-max-price")).toBeInTheDocument();
  });

  it("renders in-stock chip when in_stock_only=true", () => {
    setParams("in_stock_only=true");
    render(<ActiveFilterChips categories={CATEGORIES} />);
    expect(screen.getByTestId("chip-in-stock")).toBeInTheDocument();
  });

  it("removes only the clicked category chip", async () => {
    setParams("category=1&category=2");
    const user = userEvent.setup();
    render(<ActiveFilterChips categories={CATEGORIES} />);

    // Click ×  on category-1 chip
    const chip1 = screen.getByTestId("chip-category-1");
    const removeBtn = chip1.querySelector("button")!;
    await user.click(removeBtn);

    expect(mockRouter.replace).toHaveBeenCalledOnce();
    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).not.toContain("category=1");
    expect(url).toContain("category=2");
  });

  it("clears all filters when 'Clear all' is clicked", async () => {
    setParams("category=1&min_price=10&max_price=99&in_stock_only=true&page=3");
    const user = userEvent.setup();
    render(<ActiveFilterChips categories={CATEGORIES} />);

    await user.click(screen.getByTestId("clear-all-filters"));

    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).toBe("/products");
  });

  it("removes min_price chip without affecting other params", async () => {
    setParams("min_price=10&sort=price_asc");
    const user = userEvent.setup();
    render(<ActiveFilterChips categories={CATEGORIES} />);

    const chip = screen.getByTestId("chip-min-price");
    await user.click(chip.querySelector("button")!);

    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).not.toContain("min_price");
    expect(url).toContain("sort=price_asc");
  });
});

// ── CatalogFilterPanel ────────────────────────────────────────────────────────

describe("CatalogFilterPanel", () => {
  const defaultProps = {
    categories: CATEGORIES,
    priceBoundsMin: "10.00",
    priceBoundsMax: "500.00",
  };

  it("renders all category checkboxes", () => {
    render(<CatalogFilterPanel {...defaultProps} />);
    CATEGORIES.forEach((cat) => {
      expect(
        screen.getByTestId(`category-checkbox-${cat.id}`),
      ).toBeInTheDocument();
      expect(screen.getByText(cat.name)).toBeInTheDocument();
    });
  });

  it("renders price inputs", () => {
    render(<CatalogFilterPanel {...defaultProps} />);
    expect(screen.getByTestId("price-min-input")).toBeInTheDocument();
    expect(screen.getByTestId("price-max-input")).toBeInTheDocument();
  });

  it("renders in-stock checkbox", () => {
    render(<CatalogFilterPanel {...defaultProps} />);
    expect(screen.getByTestId("in-stock-checkbox")).toBeInTheDocument();
  });

  it("uses higher-contrast control styling inside the sidebar panel", () => {
    render(<CatalogFilterPanel {...defaultProps} />);

    expect(screen.getByTestId("category-checkbox-1")).toHaveClass(
      "border-foreground/20",
      "bg-background",
    );
    expect(screen.getByTestId("price-min-input")).toHaveClass(
      "border-foreground/20",
      "bg-background",
    );
    expect(screen.getByTestId("in-stock-checkbox")).toHaveClass(
      "border-foreground/20",
      "bg-background",
    );
  });

  it("shows checked state for already-selected category", () => {
    setParams("category=2");
    render(<CatalogFilterPanel {...defaultProps} />);
    const clothingCheckbox = screen.getByTestId("category-checkbox-2");
    expect(clothingCheckbox).toHaveAttribute("data-state", "checked");
  });

  it("selecting a category calls router.replace with category param", async () => {
    const user = userEvent.setup();
    render(<CatalogFilterPanel {...defaultProps} />);

    await user.click(screen.getByTestId("category-checkbox-1"));

    expect(mockRouter.replace).toHaveBeenCalledOnce();
    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).toContain("category=1");
  });

  it("selecting multiple categories appends them all to URL", async () => {
    // Start with category=1 already in URL
    setParams("category=1");
    const user = userEvent.setup();
    render(<CatalogFilterPanel {...defaultProps} />);

    // Click category-2; with category=1 already in params it should add category=2
    await user.click(screen.getByTestId("category-checkbox-2"));

    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).toContain("category=1");
    expect(url).toContain("category=2");
  });

  it("deselecting a category removes it from URL", async () => {
    setParams("category=1&category=2");
    const user = userEvent.setup();
    render(<CatalogFilterPanel {...defaultProps} />);

    await user.click(screen.getByTestId("category-checkbox-1"));

    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).not.toContain("category=1");
    expect(url).toContain("category=2");
  });

  it("toggling in-stock adds in_stock_only=true param", async () => {
    const user = userEvent.setup();
    render(<CatalogFilterPanel {...defaultProps} />);

    await user.click(screen.getByTestId("in-stock-checkbox"));

    expect(mockRouter.replace).toHaveBeenCalledOnce();
    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).toContain("in_stock_only=true");
  });

  it("toggling in-stock off removes the param", async () => {
    setParams("in_stock_only=true");
    const user = userEvent.setup();
    render(<CatalogFilterPanel {...defaultProps} />);

    await user.click(screen.getByTestId("in-stock-checkbox"));

    const url: string = mockRouter.replace.mock.calls[0][0];
    expect(url).not.toContain("in_stock_only");
  });

  it("renders 'No categories available' when list is empty", () => {
    render(
      <CatalogFilterPanel
        categories={[]}
        priceBoundsMin={null}
        priceBoundsMax={null}
      />,
    );
    expect(screen.getByText("No categories available.")).toBeInTheDocument();
  });

  it("renders without layout errors when many categories are provided", () => {
    const manyCategories = Array.from({ length: 30 }, (_, i) => ({
      id: i + 1,
      name: `Category ${i + 1}`,
    }));
    const { container } = render(
      <CatalogFilterPanel
        categories={manyCategories}
        priceBoundsMin="0.00"
        priceBoundsMax="1000.00"
      />,
    );
    // All checkboxes rendered inside scrollable container
    expect(
      container.querySelectorAll('[data-testid^="category-checkbox-"]'),
    ).toHaveLength(30);
  });
});
