"use client";

/**
 * ProductGallery
 *
 * Renders a product image gallery with:
 *  - Desktop: static main image + clickable thumbnail strip
 *  - Mobile:  Embla swipe carousel + dot indicators
 *  - Lightbox (yet-another-react-lightbox) opens when the main image is clicked
 *
 * Accepts a pre-mapped `slides` array so it has no knowledge of backend DTOs.
 */

import * as React from "react";
import useEmblaCarousel from "embla-carousel-react";
import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type GallerySlide = {
  id: number;
  /** Used for the thumbnail strip and mobile carousel. */
  thumb: string;
  /** Shown as the active main image on desktop. */
  main: string;
  /** Full-size URL passed to the lightbox. */
  full: string;
  alt: string;
};

interface ProductGalleryProps {
  slides: GallerySlide[];
  productName: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map GallerySlide[] → the format YARL expects. */
function toYarlSlides(slides: GallerySlide[]) {
  return slides.map((s) => ({ src: s.full, alt: s.alt }));
}

// ---------------------------------------------------------------------------
// Mobile carousel sub-component (Embla)
// ---------------------------------------------------------------------------

function MobileCarousel({
  slides,
  activeIndex,
  onChange,
}: {
  slides: GallerySlide[];
  activeIndex: number;
  onChange: (index: number) => void;
}) {
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: false });

  // Keep Embla in sync when parent changes activeIndex (e.g. lightbox navigation)
  React.useEffect(() => {
    if (emblaApi) emblaApi.scrollTo(activeIndex, true);
  }, [emblaApi, activeIndex]);

  // Notify parent when user swipes
  React.useEffect(() => {
    if (!emblaApi) return;
    const onSelect = () => onChange(emblaApi.selectedScrollSnap());
    emblaApi.on("select", onSelect);
    return () => {
      emblaApi.off("select", onSelect);
    };
  }, [emblaApi, onChange]);

  return (
    <div className="flex flex-col gap-3">
      {/* Embla viewport */}
      <div className="overflow-hidden rounded-lg border bg-muted" ref={emblaRef}>
        <div className="flex" data-testid="mobile-carousel-track">
          {slides.map((slide, index) => (
            <div
              key={slide.id}
              className="relative aspect-square min-w-full"
              data-testid={`mobile-slide-${index}`}
            >
              <img
                src={slide.main}
                alt={slide.alt}
                className="h-full w-full object-contain"
              />
            </div>
          ))}
        </div>
      </div>

      {/* Dot indicators */}
      {slides.length > 1 && (
        <div className="flex justify-center gap-1.5" role="tablist">
          {slides.map((slide, index) => (
            <button
              key={slide.id}
              type="button"
              role="tab"
              aria-selected={index === activeIndex}
              aria-label={`Go to image ${index + 1}`}
              onClick={() => {
                emblaApi?.scrollTo(index);
                onChange(index);
              }}
              className={cn(
                "h-2 w-2 rounded-full transition-colors",
                index === activeIndex
                  ? "bg-primary"
                  : "bg-muted-foreground/30 hover:bg-muted-foreground/60",
              )}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ProductGallery({ slides, productName }: ProductGalleryProps) {
  const [activeIndex, setActiveIndex] = React.useState(0);
  const [lightboxOpen, setLightboxOpen] = React.useState(false);

  // Thumbnail carousel — scrolls to keep the active thumb visible.
  const [thumbRef, thumbApi] = useEmblaCarousel({
    containScroll: "keepSnaps",
    dragFree: true,
    align: "start",
  });
  const [canScrollPrev, setCanScrollPrev] = React.useState(false);
  const [canScrollNext, setCanScrollNext] = React.useState(false);

  const updateThumbNavState = React.useCallback(() => {
    if (!thumbApi) return;
    setCanScrollPrev(thumbApi.canScrollPrev());
    setCanScrollNext(thumbApi.canScrollNext());
  }, [thumbApi]);

  React.useEffect(() => {
    if (!thumbApi) return;
    updateThumbNavState();
    thumbApi.on("select", updateThumbNavState);
    thumbApi.on("reInit", updateThumbNavState);
    return () => {
      thumbApi.off("select", updateThumbNavState);
      thumbApi.off("reInit", updateThumbNavState);
    };
  }, [thumbApi, updateThumbNavState]);

  // Sync thumbnail carousel whenever activeIndex changes.
  React.useEffect(() => {
    if (thumbApi) thumbApi.scrollTo(activeIndex, true);
  }, [thumbApi, activeIndex]);

  // ── Empty state ────────────────────────────────────────────────────────────
  if (slides.length === 0) {
    return (
      <div
        data-testid="gallery-empty"
        className="flex aspect-square w-full items-center justify-center rounded-lg border bg-muted"
      >
        <span className="text-muted-foreground text-sm">No image available</span>
      </div>
    );
  }

  const activeSlide = slides[activeIndex];

  // ── Desktop layout ─────────────────────────────────────────────────────────
  const desktopSection = (
    <div data-testid="gallery-desktop" className="hidden flex-col gap-4 md:flex">
      {/* Main image — click to open lightbox */}
      <button
        type="button"
        data-testid="gallery-main-image"
        onClick={() => setLightboxOpen(true)}
        className="relative aspect-square w-full overflow-hidden rounded-lg border bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        aria-label={`View full size: ${activeSlide.alt || productName}`}
      >
        <img
          src={activeSlide.main}
          alt={activeSlide.alt || productName}
          className="h-full w-full object-contain"
        />
      </button>

      {/* Thumbnail carousel — only shown when there are ≥2 slides */}
      {slides.length > 1 && (
        <div className="flex items-center gap-1" data-testid="gallery-thumbnails">
          {/* Prev arrow */}
          <button
            type="button"
            onClick={() => thumbApi?.scrollPrev()}
            disabled={!canScrollPrev}
            aria-label="Scroll thumbnails left"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-background shadow-sm transition-opacity disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          {/* Embla viewport */}
          <div className="min-w-0 flex-1 overflow-hidden" ref={thumbRef}>
            <div className="flex gap-2">
              {slides.map((slide, index) => (
                /* Embla slide — flex: 0 0 auto keeps fixed size */
                <div key={slide.id} className="flex-[0_0_auto]">
                  <button
                    type="button"
                    onClick={() => setActiveIndex(index)}
                    aria-label={`View image ${index + 1}`}
                    aria-current={index === activeIndex ? "true" : undefined}
                    className={cn(
                      "relative h-16 w-16 overflow-hidden rounded-md border-2 transition-all",
                      index === activeIndex
                        ? "border-primary ring-2 ring-primary/20"
                        : "border-transparent hover:border-muted-foreground/30",
                    )}
                  >
                    <img
                      src={slide.thumb}
                      alt={slide.alt || `${productName} thumbnail ${index + 1}`}
                      className="h-full w-full object-cover"
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Next arrow */}
          <button
            type="button"
            onClick={() => thumbApi?.scrollNext()}
            disabled={!canScrollNext}
            aria-label="Scroll thumbnails right"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-background shadow-sm transition-opacity disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );

  // ── Mobile layout ──────────────────────────────────────────────────────────
  const mobileSection = (
    <div data-testid="gallery-mobile" className="flex flex-col gap-4 md:hidden">
      <MobileCarousel
        slides={slides}
        activeIndex={activeIndex}
        onChange={setActiveIndex}
      />
    </div>
  );

  // ── Lightbox ───────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-0">
      {desktopSection}
      {mobileSection}

      <Lightbox
        open={lightboxOpen}
        close={() => setLightboxOpen(false)}
        slides={toYarlSlides(slides)}
        index={activeIndex}
        on={{ view: ({ index }) => setActiveIndex(index) }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mapper helper (co-located, exported for page use)
// ---------------------------------------------------------------------------

import type { ProductImageVm } from "@/lib/mappers/products";

/**
 * Convert the view-model gallery array (from mapProductToDetailVm) into the
 * GallerySlide shape consumed by this component.
 */
export function galleryToSlides(gallery: ProductImageVm[]): GallerySlide[] {
  return gallery.map((img) => ({
    id: img.id,
    thumb: img.variants.thumb,
    main: img.variants.medium,
    full: img.variants.full,
    alt: img.alt,
  }));
}
