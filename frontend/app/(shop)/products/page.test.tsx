import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ProductsPage from "./page";
import { api } from "@/lib/api";

vi.mock("@/lib/api");

describe("ProductsPage", () => {
  it("renders product list after successful fetch", async () => {
    // ARRANGE – prepare mock API response
    (api.get as any).mockResolvedValueOnce({
      data: [
        { id: 1, name: "Test Product A", price: "10.00" },
        { id: 2, name: "Test Product B", price: "20.00" },
      ],
    });

    // ACT – render page
    render(<ProductsPage />);

    // ASSERT – loading state
    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    // ASSERT – data appears
    await waitFor(() => {
      expect(screen.getByText("Test Product A – 10.00")).toBeInTheDocument();
      expect(screen.getByText("Test Product B – 20.00")).toBeInTheDocument();
    });
  });

  it("renders error when api call fails", async () => {
    (api.get as any).mockRejectedValueOnce(new Error("Network error"));

    render(<ProductsPage />);

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
