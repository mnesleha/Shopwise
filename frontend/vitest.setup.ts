import '@testing-library/jest-dom/vitest';

// ---------------------------------------------------------------------------
// Global module mocks
//
// Because vitest.config.ts uses `isolate: false`, all test files share a single
// module registry. Per-file vi.mock() calls arrive too late to intercept modules
// that were already loaded by earlier test files.
//
// Mocks that must be consistent across the entire test run go here:
// ---------------------------------------------------------------------------

import { vi } from 'vitest';
import * as React from 'react';

/**
 * yet-another-react-lightbox
 *
 * Replaces the real Lightbox with a sentinel <div data-testid="lightbox-overlay"
 * /> when open=true, and nothing otherwise.  This avoids the library's
 * dependency on real browser APIs (ResizeObserver, focus traps, CSS) that are
 * not available in happy-dom, and keeps the tests fast and deterministic.
 */
vi.mock('yet-another-react-lightbox', () => ({
  default: ({ open }: { open: boolean }) =>
    open
      ? React.createElement('div', { 'data-testid': 'lightbox-overlay' })
      : null,
}));