/**
 * ProductGallery — Type A (Presentational)
 *
 * Tests C–F: Gallery rendering, thumbnail interaction, lightbox opening,
 * and empty-state placeholder.
 *
 * Strategy:
 *  - YARL (yet-another-react-lightbox) is mocked to render a lightweight
 *    sentinel `<div data-testid="lightbox-overlay" />` when open=true.
 *  - All DOM assertions are scoped to the desktop section
 *    (data-testid="gallery-desktop") to avoid collisions with the hidden
 *    mobile Embla carousel that also renders in happy-dom.
 */

import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProductGallery } from "@/components/product/ProductGallery";
import type { GallerySlide } from "@/components/product/ProductGallery";
import { makeGallerySlide } from "../helpers/fixtures";

// yet-another-react-lightbox is mocked globally in vitest.setup.ts:
// open=true  → <div data-testid="lightbox-overlay" />
// open=false → null

// ── Fixtures ──────────────────────────────────────────────────────────────────

function twoSlides(): GallerySlide[] {
  return [
    makeGallerySlide({
      id: 1,
      thumb: "https://example.com/1/thumb.jpg",
      main: "https://example.com/1/medium.jpg",
      full: "https://example.com/1/full.jpg",
      alt: "Mouse front view",
    }),
    makeGallerySlide({
      id: 2,
      thumb: "https://example.com/2/thumb.jpg",
      main: "https://example.com/2/medium.jpg",
      full: "https://example.com/2/full.jpg",
      alt: "Mouse side view",
    }),
  ];
}

// ── Test C: Main image + thumbnails rendered ──────────────────────────────────

describe("ProductGallery — C: desktop layout renders main image and thumbnails", () => {
  it("renders the first slide as the main image", () => {
    render(<ProductGallery slides={twoSlides()} productName="Test Mouse" />);

    const desktop = screen.getByTestId("gallery-desktop");
    const mainBtn = within(desktop).getByTestId("gallery-main-image");
    const mainImg = within(mainBtn).getByRole("img");

    expect(mainImg).toHaveAttribute("src", "https://example.com/1/medium.jpg");
    expect(mainImg).toHaveAttribute("alt", "Mouse front view");
  });

  it("renders one thumbnail button per slide", () => {
    render(<ProductGallery slides={twoSlides()} productName="Test Mouse" />);

    const desktop = screen.getByTestId("gallery-desktop");
    const thumbStrip = within(desktop).getByTestId("gallery-thumbnails");

    expect(
      within(thumbStrip).getByRole("button", { name: "View image 1" }),
    ).toBeInTheDocument();
    expect(
      within(thumbStrip).getByRole("button", { name: "View image 2" }),
    ).toBeInTheDocument();
  });

  it("marks the first thumbnail as current on initial render", () => {
    render(<ProductGallery slides={twoSlides()} productName="Test Mouse" />);

    const desktop = screen.getByTestId("gallery-desktop");
    const thumbStrip = within(desktop).getByTestId("gallery-thumbnails");
    const thumb1 = within(thumbStrip).getByRole("button", {
      name: "View image 1",
    });

    expect(thumb1).toHaveAttribute("aria-current", "true");
  });

  it("does not render a thumbnail strip for a single slide", () => {
    render(
      <ProductGallery slides={[twoSlides()[0]]} productName="Test Mouse" />,
    );

    const desktop = screen.getByTestId("gallery-desktop");
    expect(
      within(desktop).queryByTestId("gallery-thumbnails"),
    ).not.toBeInTheDocument();
  });
});

// ── Test D: Clicking a thumbnail changes the main image ──────────────────────

describe("ProductGallery — D: thumbnail interaction changes main image", () => {
  it("clicking thumbnail 2 updates the main image src", async () => {
    const user = userEvent.setup();
    render(<ProductGallery slides={twoSlides()} productName="Test Mouse" />);

    const desktop = screen.getByTestId("gallery-desktop");
    const thumbStrip = within(desktop).getByTestId("gallery-thumbnails");
    const thumb2 = within(thumbStrip).getByRole("button", {
      name: "View image 2",
    });

    await user.click(thumb2);

    const mainBtn = within(desktop).getByTestId("gallery-main-image");
    const mainImg = within(mainBtn).getByRole("img");

    expect(mainImg).toHaveAttribute("src", "https://example.com/2/medium.jpg");
    expect(mainImg).toHaveAttribute("alt", "Mouse side view");
  });

  it("marks the clicked thumbnail as current", async () => {
    const user = userEvent.setup();
    render(<ProductGallery slides={twoSlides()} productName="Test Mouse" />);

    const desktop = screen.getByTestId("gallery-desktop");
    const thumbStrip = within(desktop).getByTestId("gallery-thumbnails");

    await user.click(
      within(thumbStrip).getByRole("button", { name: "View image 2" }),
    );

    expect(
      within(thumbStrip).getByRole("button", { name: "View image 2" }),
    ).toHaveAttribute("aria-current", "true");
    expect(
      within(thumbStrip).getByRole("button", { name: "View image 1" }),
    ).not.toHaveAttribute("aria-current");
  });
});

// ── Test E: Lightbox opens on main image click ────────────────────────────────

describe("ProductGallery — E: lightbox", () => {
  it("lightbox is not shown initially", () => {
    render(<ProductGallery slides={twoSlides()} productName="Test Mouse" />);

    expect(screen.queryByTestId("lightbox-overlay")).not.toBeInTheDocument();
  });

  it("clicking the main image button opens the lightbox", async () => {
    const user = userEvent.setup();
    render(<ProductGallery slides={twoSlides()} productName="Test Mouse" />);

    const desktop = screen.getByTestId("gallery-desktop");
    const mainBtn = within(desktop).getByTestId("gallery-main-image");

    await user.click(mainBtn);

    expect(screen.getByTestId("lightbox-overlay")).toBeInTheDocument();
  });
});

// ── Test F: Empty gallery shows placeholder ───────────────────────────────────

describe("ProductGallery — F: empty state", () => {
  it("shows 'No image available' when slides is empty", () => {
    render(<ProductGallery slides={[]} productName="Test Mouse" />);

    expect(screen.getByText("No image available")).toBeInTheDocument();
  });

  it("does not render desktop or mobile sections when slides is empty", () => {
    render(<ProductGallery slides={[]} productName="Test Mouse" />);

    expect(screen.queryByTestId("gallery-desktop")).not.toBeInTheDocument();
    expect(screen.queryByTestId("gallery-mobile")).not.toBeInTheDocument();
  });
});
