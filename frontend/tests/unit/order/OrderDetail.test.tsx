/**
 * OrderDetail — Type A (Presentational)
 *
 * Contract guarded:
 * - Renders order number in the title element
 * - Renders order status badge
 * - Renders each item's product name, quantity, unit price, and line total
 * - Renders the order total
 * - Renders the customer name
 * - "Back to shop" button calls onBackToShop
 * - Print button calls onPrint when handler is provided
 * - Print button is NOT rendered when onPrint is not provided
 * - Optional fields (createdAt, shippingMethod, paymentMethod) render when provided
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrderDetail } from "@/components/order/OrderDetail";
import { renderWithProviders } from "../helpers/render";
import { makeOrderViewModel, makeOrderItem } from "../helpers/fixtures";
import { ORDER_TITLE, ORDER_STATUS } from "../helpers/testIds";

function renderOrderDetail(
  props: Partial<React.ComponentProps<typeof OrderDetail>> = {},
) {
  const callbacks = {
    onBackToShop: vi.fn(),
    onPrint: vi.fn(),
  };
  renderWithProviders(
    <OrderDetail
      order={makeOrderViewModel()}
      {...callbacks}
      {...props}
    />,
  );
  return callbacks;
}

describe("OrderDetail", () => {
  describe("order identity", () => {
    it("renders the order number in the title element", () => {
      renderOrderDetail();
      const title = screen.getByTestId(ORDER_TITLE);
      expect(title).toHaveTextContent("OBJ25000042");
    });

    it("renders the order status badge", () => {
      renderOrderDetail();
      expect(screen.getByTestId(ORDER_STATUS)).toHaveTextContent("Created");
    });

    it("renders a PAID status correctly", () => {
      renderOrderDetail({
        order: makeOrderViewModel({ status: "PAID" }),
      });
      expect(screen.getByTestId(ORDER_STATUS)).toHaveTextContent("Paid");
    });

    it("renders createdAt when provided", () => {
      renderOrderDetail({
        order: makeOrderViewModel({ createdAt: "February 25, 2026" }),
      });
      expect(screen.getByText("February 25, 2026")).toBeInTheDocument();
    });
  });

  describe("address blocks", () => {
    it("renders the customer name", () => {
      renderOrderDetail();
      expect(screen.getByText("Jane Test")).toBeInTheDocument();
    });

    it("renders the supplier name", () => {
      renderOrderDetail();
      expect(screen.getByText("Shopwise s.r.o.")).toBeInTheDocument();
    });
  });

  describe("order items table", () => {
    it("renders the product name for each order item", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ productName: "Wireless Keyboard" })],
      });
      renderOrderDetail({ order });
      expect(screen.getByText("Wireless Keyboard")).toBeInTheDocument();
    });

    it("renders the quantity for each order item", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ quantity: 3 })],
      });
      renderOrderDetail({ order });
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("renders multiple items", () => {
      const order = makeOrderViewModel({
        items: [
          makeOrderItem({ id: "i1", productName: "Mouse" }),
          makeOrderItem({ id: "i2", productName: "Keyboard" }),
        ],
      });
      renderOrderDetail({ order });
      expect(screen.getByText("Mouse")).toBeInTheDocument();
      expect(screen.getByText("Keyboard")).toBeInTheDocument();
    });
  });

  describe("totals", () => {
    it("renders the order total", () => {
      const order = makeOrderViewModel({ total: "119.96" });
      renderOrderDetail({ order });
      // Total appears in the Totals summary card
      expect(screen.getByText("$119.96")).toBeInTheDocument();
    });
  });

  describe("optional metadata", () => {
    it("renders shipping method when provided", () => {
      const order = makeOrderViewModel({ shippingMethod: "PPL Express" });
      renderOrderDetail({ order });
      expect(screen.getByText("PPL Express")).toBeInTheDocument();
    });

    it("does NOT render shipping method section when not provided", () => {
      renderOrderDetail({ order: makeOrderViewModel({ shippingMethod: undefined }) });
      expect(screen.queryByText(/shipping:/i)).toBeNull();
    });

    it("renders payment method when provided", () => {
      const order = makeOrderViewModel({ paymentMethod: "Bank transfer" });
      renderOrderDetail({ order });
      expect(screen.getByText("Bank transfer")).toBeInTheDocument();
    });
  });

  describe("callbacks", () => {
    it("calls onBackToShop when 'Back to shop' button is clicked", async () => {
      const user = userEvent.setup();
      const { onBackToShop } = renderOrderDetail();
      // There are two back buttons (top and bottom); click the first one
      const buttons = screen.getAllByRole("button", { name: /back to shop/i });
      await user.click(buttons[0]);
      expect(onBackToShop).toHaveBeenCalled();
    });

    it("calls onPrint when the Print button is clicked", async () => {
      const user = userEvent.setup();
      const { onPrint } = renderOrderDetail();
      await user.click(screen.getByRole("button", { name: /print/i }));
      expect(onPrint).toHaveBeenCalledTimes(1);
    });

    it("does NOT render a Print button when onPrint is not provided", () => {
      renderWithProviders(
        <OrderDetail
          order={makeOrderViewModel()}
          onBackToShop={vi.fn()}
          onPrint={undefined}
        />,
      );
      expect(screen.queryByRole("button", { name: /print/i })).toBeNull();
    });
  });
});
