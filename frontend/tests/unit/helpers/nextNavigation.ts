import { vi } from "vitest";

/**
 * createRouterMock
 *
 * Returns a shared mock object compatible with next/navigation's useRouter.
 * Use this in a vi.mock("next/navigation", ...) factory.
 *
 * Usage in test file:
 *
 *   import { createRouterMock } from "../helpers/nextNavigation";
 *
 *   const mockRouter = createRouterMock();
 *
 *   vi.mock("next/navigation", () => ({
 *     useRouter: () => mockRouter,
 *     useSearchParams: () => new URLSearchParams(),
 *     usePathname: () => "/",
 *   }));
 *
 *   // In tests:
 *   expect(mockRouter.push).toHaveBeenCalledWith("/products");
 */
export function createRouterMock() {
  return {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  };
}
