import { expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

test("App Router: Works with dynamic route segments", async () => {
  const ui = await Page({ params: Promise.resolve({ slug: "Test" }) } as any);
  render(ui as any);
  expect(
    screen.getByRole("heading", { level: 1, name: "Slug: Test" }),
  ).toBeDefined();
});
