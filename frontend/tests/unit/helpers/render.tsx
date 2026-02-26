import * as React from "react";
import { render, type RenderOptions, type RenderResult } from "@testing-library/react";

/**
 * renderWithProviders
 *
 * App Router-friendly render wrapper. Currently no global providers are needed
 * (no TanStack Query, no Zustand). AuthProvider is mocked at the module level
 * in tests that need it. Add providers here only when they are introduced in
 * the real application.
 */
export function renderWithProviders(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
): RenderResult {
  return render(ui, options);
}
