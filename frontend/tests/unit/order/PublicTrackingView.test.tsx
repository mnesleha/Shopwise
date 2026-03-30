import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";

import PublicTrackingView from "@/components/order/PublicTrackingView";
import { renderWithProviders } from "../helpers/render";

describe("PublicTrackingView", () => {
  it("renders shipment summary and timeline", () => {
    renderWithProviders(
      <PublicTrackingView
        tracking={{
          trackingNumber: "MOCK-TRACK-123",
          status: "IN_TRANSIT",
          carrierName: "Mock Shipping",
          serviceName: "Express",
          shipmentTimeline: [
            {
              status: "LABEL_CREATED",
              label: "Label created",
              occurredAt: "2026-03-28T16:00:00Z",
              isCurrent: false,
            },
            {
              status: "IN_TRANSIT",
              label: "In transit",
              occurredAt: "2026-03-29T08:15:00Z",
              isCurrent: true,
            },
            {
              status: "DELIVERED",
              label: "Delivered",
              occurredAt: null,
              isCurrent: false,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("MOCK-TRACK-123")).toBeInTheDocument();
    expect(screen.getByText("Mock Shipping")).toBeInTheDocument();
    expect(screen.getByText("Express")).toBeInTheDocument();
    expect(screen.getByText("Label created")).toBeInTheDocument();
    expect(screen.getAllByText("In transit")).toHaveLength(2);
    expect(screen.getByText("Delivered")).toBeInTheDocument();
    expect(screen.getByText("2026-03-29 08:15 UTC")).toBeInTheDocument();
  });

  it("renders delayed customer-facing copy for failed delivery", () => {
    renderWithProviders(
      <PublicTrackingView
        tracking={{
          trackingNumber: "MOCK-TRACK-FAILED",
          status: "FAILED_DELIVERY",
          carrierName: "Mock Shipping",
          serviceName: "Express",
          shipmentTimeline: [
            {
              status: "LABEL_CREATED",
              label: "Label created",
              occurredAt: "2026-03-28T16:00:00Z",
              isCurrent: false,
            },
            {
              status: "IN_TRANSIT",
              label: "In transit",
              occurredAt: "2026-03-29T08:15:00Z",
              isCurrent: true,
            },
            {
              status: "DELIVERED",
              label: "Delivered",
              occurredAt: null,
              isCurrent: false,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Delayed")).toBeInTheDocument();
    expect(screen.getByText("Delayed (In transit)")).toBeInTheDocument();
    expect(
      screen.getByText("We're arranging a new delivery attempt."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Failed delivery")).toBeNull();
    expect(screen.getByText("Label created")).toBeInTheDocument();
    expect(screen.queryByText("In transit")).toBeNull();
    expect(screen.getByText("Delivered")).toBeInTheDocument();
    expect(screen.queryByText("Current")).toBeNull();
  });
});
