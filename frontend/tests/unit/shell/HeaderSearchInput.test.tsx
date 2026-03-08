/**
 * HeaderSearchInput — URL-driven global search input in the header.
 *
 * Covers:
 *  - renders input with correct placeholder
 *  - Enter key submits and navigates to /products?search=...
 *  - filter/sort params are stripped on submit
 *  - clearing the input and submitting removes the search param
 *  - existing search param from URL is pre-populated in the input
 *  - icon button click also submits
 */

import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createRouterMock } from "../helpers/nextNavigation";

// ── Router + navigation mock ──────────────────────────────────────────────────

const mockRouter = createRouterMock();
let mockParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => mockParams,
  usePathname: () => "/",
}));

// ── Import after mocks ────────────────────────────────────────────────────────

import HeaderSearchInput from "@/components/shell/HeaderSearchInput";

// ── Helpers ───────────────────────────────────────────────────────────────────

function setParams(init: string) {
  mockParams = new URLSearchParams(init);
}

function renderInput() {
  return render(<HeaderSearchInput />);
}

function getInput(): HTMLInputElement {
  return screen.getByTestId("header-search-input") as HTMLInputElement;
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  setParams("");
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("HeaderSearchInput", () => {
  it("renders input with the correct placeholder", () => {
    renderInput();
    expect(getInput()).toHaveAttribute(
      "placeholder",
      "Search products and descriptions...",
    );
  });

  it("pre-fills input from the URL search param", () => {
    setParams("search=keyboard");
    renderInput();
    expect(getInput().value).toBe("keyboard");
  });

  it("navigates to /products?search=... when Enter is pressed", async () => {
    const user = userEvent.setup();
    renderInput();
    await user.type(getInput(), "mechanical keyboard{Enter}");

    expect(mockRouter.push).toHaveBeenCalledOnce();
    const url: string = mockRouter.push.mock.calls[0][0];
    // URLSearchParams serialises spaces as '+' (application/x-www-form-urlencoded)
    expect(url).toMatch(/search=mechanical(\+|%20)keyboard/);
    expect(url).toMatch(/^\/products/);
  });

  it("strips category, min_price, max_price, in_stock_only and sort on submit", async () => {
    setParams(
      "search=old&category=1&min_price=10&max_price=99&in_stock_only=true&sort=price_asc&page=3",
    );
    const user = userEvent.setup();
    renderInput();

    await user.clear(getInput());
    await user.type(getInput(), "headphones{Enter}");

    const url: string = mockRouter.push.mock.calls[0][0];
    expect(url).toContain("search=headphones");
    expect(url).not.toContain("category=");
    expect(url).not.toContain("min_price=");
    expect(url).not.toContain("max_price=");
    expect(url).not.toContain("in_stock_only=");
    expect(url).not.toContain("sort=");
    expect(url).not.toContain("page=");
  });

  it("navigates to /products (no search param) when input is cleared and Enter pressed", async () => {
    setParams("search=keyboard");
    const user = userEvent.setup();
    renderInput();

    await user.clear(getInput());
    fireEvent.keyDown(getInput(), { key: "Enter" });

    expect(mockRouter.push).toHaveBeenCalledOnce();
    expect(mockRouter.push.mock.calls[0][0]).toBe("/products");
  });

  it("submits when the search icon button is clicked", async () => {
    const user = userEvent.setup();
    renderInput();

    await user.type(getInput(), "mouse");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(mockRouter.push).toHaveBeenCalledOnce();
    const url: string = mockRouter.push.mock.calls[0][0];
    expect(url).toContain("search=mouse");
  });

  it("navigates from any page to /products on submit", async () => {
    const user = userEvent.setup();
    renderInput();
    await user.type(getInput(), "desk{Enter}");

    expect(mockRouter.push.mock.calls[0][0]).toMatch(/^\/products/);
  });

  it("navigates to /products when the native clear button fires the search event", () => {
    // The browser's native × button on <input type="search"> fires a 'search'
    // DOM event (not a React synthetic event).  jsdom doesn't render the clear
    // button, so we dispatch the event manually to test the listener.
    setParams("search=keyboard");
    renderInput();

    const input = getInput();
    // Simulate the browser clearing the value and firing 'search'
    Object.defineProperty(input, "value", {
      value: "",
      writable: true,
      configurable: true,
    });
    input.dispatchEvent(new Event("search", { bubbles: true }));

    expect(mockRouter.push).toHaveBeenCalledOnce();
    expect(mockRouter.push.mock.calls[0][0]).toBe("/products");
  });
});
