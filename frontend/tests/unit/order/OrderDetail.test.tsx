/**
 * OrderDetail — Type A (Presentational)
 *
 * Contract guarded:
 * - Renders order number in the title element
 * - Renders order status badge
 * - Renders each item's product name, quantity, unit price, and line total
 * - Renders the order total (currency €)
 * - Renders the customer name
 * - "Back to shop" button calls onBackToShop
 * - Print button calls onPrint when handler is provided
 * - Print button is NOT rendered when onPrint is not provided
 * - Optional fields (createdAt, shippingMethod, paymentMethod) render when provided
 * - Invoice items table: Qty | Product | Unit excl. VAT | VAT rate | VAT | Total incl. VAT
 * - Neutral line discount note below product name ("Line discount: N%")
 * - VAT breakdown section renders when vatBreakdown data provided
 * - Order summary: Tax base / VAT / Total incl. VAT
 * - Order summary: explicit order-discount row when orderDiscountGross > 0
 * - VAT breakdown: explanatory note when order-level discount exists (note moved from summary)
 * - Summary does NOT render any "additional discount" note (removed in Phase 4 polish)
 */
import { describe, it, expect, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrderDetail } from "@/components/order/OrderDetail";
import { renderWithProviders } from "../helpers/render";
import { makeOrderViewModel, makeOrderItem } from "../helpers/fixtures";
import {
  ORDER_TITLE,
  ORDER_STATUS,
  ORDER_ITEMS_TABLE,
  VAT_BREAKDOWN,
  ORDER_SUMMARY,
  ITEM_DISCOUNT_NOTE,
  ORDER_DISCOUNT_ROW,
  VAT_BREAKDOWN_ORDER_DISCOUNT_NOTE,
  vatBreakdownRow,
} from "../helpers/testIds";

function renderOrderDetail(
  props: Partial<React.ComponentProps<typeof OrderDetail>> = {},
) {
  const callbacks = {
    onBackToShop: vi.fn(),
    onPrint: vi.fn(),
  };
  renderWithProviders(
    <OrderDetail order={makeOrderViewModel()} {...callbacks} {...props} />,
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
      // Total appears in the order summary section (currency is €)
      expect(screen.getByText("€119.96")).toBeInTheDocument();
    });
  });

  describe("optional metadata", () => {
    it("renders shipping method when provided", () => {
      const order = makeOrderViewModel({ shippingMethod: "PPL Express" });
      renderOrderDetail({ order });
      expect(screen.getByText("PPL Express")).toBeInTheDocument();
    });

    it("does NOT render shipping method section when not provided", () => {
      renderOrderDetail({
        order: makeOrderViewModel({ shippingMethod: undefined }),
      });
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

  // ── Invoice items table (Phase 3) ─────────────────────────────────────────

  describe("invoice items table", () => {
    it("renders the items table container", () => {
      renderOrderDetail();
      expect(screen.getByTestId(ORDER_ITEMS_TABLE)).toBeInTheDocument();
    });

    it("renders 'Unit excl. VAT' column header", () => {
      renderOrderDetail();
      expect(screen.getByText("Unit excl. VAT")).toBeInTheDocument();
    });

    it("renders 'VAT rate' column header", () => {
      renderOrderDetail();
      expect(screen.getByText("VAT rate")).toBeInTheDocument();
    });

    it("renders 'VAT' column header", () => {
      renderOrderDetail();
      expect(screen.getByText("VAT")).toBeInTheDocument();
    });

    it("renders 'Total incl. VAT' column header", () => {
      renderOrderDetail();
      const table = screen.getByTestId(ORDER_ITEMS_TABLE);
      expect(
        within(table).getAllByText("Total incl. VAT").length,
      ).toBeGreaterThanOrEqual(1);
    });

    it("does NOT render a 'Discount' column header", () => {
      renderOrderDetail();
      const table = screen.getByTestId(ORDER_ITEMS_TABLE);
      expect(table.querySelectorAll("th")).not.toMatchObject(
        expect.arrayContaining([
          expect.objectContaining({ textContent: "Discount" }),
        ]),
      );
      // no th with text "Discount"
      const ths = Array.from(table.querySelectorAll("th")).map(
        (th) => th.textContent,
      );
      expect(ths).not.toContain("Discount");
    });

    it("shows unitPriceNet for the Unit excl. VAT cell when provided", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ unitPriceNet: "27.02" })],
      });
      renderOrderDetail({ order });
      expect(screen.getByText("€27.02")).toBeInTheDocument();
    });

    it("falls back to unitPrice for Unit excl. VAT when unitPriceNet is null", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ unitPrice: "29.99", unitPriceNet: null })],
      });
      renderOrderDetail({ order });
      // unitPrice is rendered in the Unit excl. VAT column
      expect(screen.getAllByText("€29.99").length).toBeGreaterThanOrEqual(1);
    });

    it("shows lineTotalGross for the Total incl. VAT cell when provided", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ lineTotalGross: "59.98" })],
      });
      renderOrderDetail({ order });
      // Scope to items table to avoid ambiguity with the summary total
      const table = screen.getByTestId(ORDER_ITEMS_TABLE);
      expect(within(table).getByText("€59.98")).toBeInTheDocument();
    });

    it("shows taxRate with % suffix when provided", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ taxRate: "10.00" })],
      });
      renderOrderDetail({ order });
      expect(screen.getByText("10.00%")).toBeInTheDocument();
    });

    it("renders \u2014 for null taxRate — no fake '0.00%'", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ taxRate: null })],
      });
      renderOrderDetail({ order });
      expect(screen.queryByText("0.00%")).not.toBeInTheDocument();
      const table = screen.getByTestId(ORDER_ITEMS_TABLE);
      expect(table.textContent).toContain("\u2014");
    });

    it("renders \u2014 for null taxAmount — no fake zero money value", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ taxAmount: null, taxRate: "10.00" })],
      });
      renderOrderDetail({ order });
      const table = screen.getByTestId(ORDER_ITEMS_TABLE);
      // tax rate renders normally; tax amount renders as em-dash
      expect(table.textContent).toContain("10.00%");
      expect(table.textContent).toContain("\u2014");
    });
  });

  // ── Currency rendering ────────────────────────────────────────────────────

  describe("currency rendering", () => {
    it("uses EUR symbol (\u20ac) by default when currency is undefined", () => {
      const order = makeOrderViewModel({ currency: undefined, total: "59.98" });
      renderOrderDetail({ order });
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(within(summary).getByText("\u20ac59.98")).toBeInTheDocument();
    });

    it("uses USD symbol ($) when currency is 'USD'", () => {
      const order = makeOrderViewModel({
        currency: "USD",
        total: "59.98",
        items: [makeOrderItem({ unitPriceNet: "27.02" })],
      });
      renderOrderDetail({ order });
      expect(screen.queryByText("\u20ac27.02")).not.toBeInTheDocument();
      expect(screen.getByText("$27.02")).toBeInTheDocument();
    });

    it("uses GBP symbol (\u00a3) when currency is 'GBP'", () => {
      const order = makeOrderViewModel({ currency: "GBP", total: "50.00" });
      renderOrderDetail({ order });
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(within(summary).getByText("\u00a350.00")).toBeInTheDocument();
    });
  });

  // ── Discount note (Phase 3, neutral inline text) ─────────────────────────

  describe("discount note", () => {
    it("renders the discount note element when discountNote is provided", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ discountNote: "Line discount: 10%" })],
      });
      renderOrderDetail({ order });
      const note = screen.getByTestId(ITEM_DISCOUNT_NOTE);
      expect(note).toHaveTextContent("Line discount: 10%");
    });

    it("does NOT render the discount note element when discountNote is absent", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ discountNote: null })],
      });
      renderOrderDetail({ order });
      expect(screen.queryByTestId(ITEM_DISCOUNT_NOTE)).toBeNull();
    });

    it("does NOT render a marketing-style discount badge", () => {
      const order = makeOrderViewModel({
        items: [
          makeOrderItem({
            discountNote: "Line discount: 10%",
            discount: { type: "PERCENT", value: "10" },
          }),
        ],
      });
      renderOrderDetail({ order });
      // No badge element with discount text should be present
      expect(screen.queryByText(/–10%/)).toBeNull();
    });

    it("percent-discounted item shows 'Line discount: N%' note", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ discountNote: "Line discount: 30%" })],
      });
      renderOrderDetail({ order });
      const note = screen.getByTestId(ITEM_DISCOUNT_NOTE);
      expect(note).toHaveTextContent("Line discount: 30%");
      // No raw fixed-amount text, no promotion code
      expect(note.textContent).not.toMatch(/\d+\.\d{2}(?!%)/);
    });

    it("fixed-discounted item shows 'Line discount: N%' note", () => {
      // FIXED discount derived to 20% → "Line discount: 20%"
      const order = makeOrderViewModel({
        items: [makeOrderItem({ discountNote: "Line discount: 20%" })],
      });
      renderOrderDetail({ order });
      const note = screen.getByTestId(ITEM_DISCOUNT_NOTE);
      expect(note).toHaveTextContent("Line discount: 20%");
      // No raw fixed-amount text
      expect(note.textContent).not.toMatch(/\d+\.\d{2}(?!%)/);
    });

    it("non-discounted item shows no note", () => {
      const order = makeOrderViewModel({
        items: [makeOrderItem({ discountNote: null, discount: null })],
      });
      renderOrderDetail({ order });
      expect(screen.queryByTestId(ITEM_DISCOUNT_NOTE)).toBeNull();
    });
  });

  // ── VAT breakdown section (Phase 3) ──────────────────────────────────────

  describe("VAT breakdown section", () => {
    it("renders the VAT breakdown card when vatBreakdown is provided", () => {
      const order = makeOrderViewModel({
        vatBreakdown: [
          {
            taxRate: "10.00",
            taxBase: "100.00",
            vatAmount: "10.00",
            totalInclVat: "110.00",
          },
        ],
      });
      renderOrderDetail({ order });
      expect(screen.getByTestId(VAT_BREAKDOWN)).toBeInTheDocument();
    });

    it("does NOT render the VAT breakdown card when vatBreakdown is null", () => {
      const order = makeOrderViewModel({ vatBreakdown: null });
      renderOrderDetail({ order });
      expect(screen.queryByTestId(VAT_BREAKDOWN)).toBeNull();
    });

    it("does NOT render the VAT breakdown card when vatBreakdown is empty", () => {
      const order = makeOrderViewModel({ vatBreakdown: [] });
      renderOrderDetail({ order });
      expect(screen.queryByTestId(VAT_BREAKDOWN)).toBeNull();
    });

    it("renders a row for each VAT rate with the correct testid", () => {
      const order = makeOrderViewModel({
        vatBreakdown: [
          {
            taxRate: "10.00",
            taxBase: "100.00",
            vatAmount: "10.00",
            totalInclVat: "110.00",
          },
          {
            taxRate: "21.00",
            taxBase: "50.00",
            vatAmount: "10.50",
            totalInclVat: "60.50",
          },
        ],
      });
      renderOrderDetail({ order });
      expect(screen.getByTestId(vatBreakdownRow("10.00"))).toBeInTheDocument();
      expect(screen.getByTestId(vatBreakdownRow("21.00"))).toBeInTheDocument();
    });

    it("renders the tax rate with % suffix in the row", () => {
      const order = makeOrderViewModel({
        vatBreakdown: [
          {
            taxRate: "10.00",
            taxBase: "100.00",
            vatAmount: "10.00",
            totalInclVat: "110.00",
          },
        ],
      });
      renderOrderDetail({ order });
      const row = screen.getByTestId(vatBreakdownRow("10.00"));
      expect(row).toHaveTextContent("10.00%");
    });

    it("renders tax base, VAT amount, and gross total in the row", () => {
      const order = makeOrderViewModel({
        vatBreakdown: [
          {
            taxRate: "10.00",
            taxBase: "100.00",
            vatAmount: "10.00",
            totalInclVat: "110.00",
          },
        ],
      });
      renderOrderDetail({ order });
      const row = screen.getByTestId(vatBreakdownRow("10.00"));
      expect(row).toHaveTextContent("€100.00");
      expect(row).toHaveTextContent("€10.00");
      expect(row).toHaveTextContent("€110.00");
    });

    it("renders a footer total row in the breakdown table", () => {
      const order = makeOrderViewModel({
        vatBreakdown: [
          {
            taxRate: "10.00",
            taxBase: "100.00",
            vatAmount: "10.00",
            totalInclVat: "110.00",
          },
        ],
      });
      renderOrderDetail({ order });
      const breakdown = screen.getByTestId(VAT_BREAKDOWN);
      const tfoot = breakdown.querySelector("tfoot");
      expect(tfoot).not.toBeNull();
      expect(tfoot!.textContent).toContain("Total");
    });
  });

  // ── Order summary (Phase 3) ───────────────────────────────────────────────

  describe("order summary section", () => {
    it("renders the order summary card", () => {
      renderOrderDetail();
      expect(screen.getByTestId(ORDER_SUMMARY)).toBeInTheDocument();
    });

    it("renders 'Total incl. VAT' label", () => {
      renderOrderDetail();
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(within(summary).getByText("Total incl. VAT")).toBeInTheDocument();
    });

    it("renders tax base row when subtotalNet is provided", () => {
      const order = makeOrderViewModel({
        subtotalNet: "54.53",
        totalTax: "5.45",
        subtotalGross: "59.98",
      });
      renderOrderDetail({ order });
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(summary).toHaveTextContent("Tax base");
      expect(summary).toHaveTextContent("€54.53");
    });

    it("renders VAT row when totalTax is provided", () => {
      const order = makeOrderViewModel({
        subtotalNet: "54.53",
        totalTax: "5.45",
        subtotalGross: "59.98",
      });
      renderOrderDetail({ order });
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(summary).toHaveTextContent("VAT");
      expect(summary).toHaveTextContent("€5.45");
    });

    it("shows 'VAT included in price' note when subtotalNet and totalTax are both null", () => {
      const order = makeOrderViewModel({
        subtotalNet: null,
        totalTax: null,
      });
      renderOrderDetail({ order });
      expect(screen.getByText("VAT included in price")).toBeInTheDocument();
    });

    it("does NOT show 'VAT included in price' note when subtotalNet is provided", () => {
      const order = makeOrderViewModel({
        subtotalNet: "54.53",
        totalTax: "5.45",
      });
      renderOrderDetail({ order });
      expect(screen.queryByText("VAT included in price")).toBeNull();
    });

    it("renders order discount row when orderDiscountGross is > 0", () => {
      const order = makeOrderViewModel({
        subtotalNet: "49.53",
        totalTax: "4.95",
        subtotalGross: "59.98",
        orderDiscountGross: "5.00",
        total: "54.98",
      });
      renderOrderDetail({ order });
      const row = screen.getByTestId(ORDER_DISCOUNT_ROW);
      expect(row).toBeInTheDocument();
      // Must show the discount amount (negative sense)
      expect(row).toHaveTextContent("€5.00");
    });

    it("renders 'Subtotal incl. VAT (after line discounts)' row when order discount present", () => {
      const order = makeOrderViewModel({
        subtotalGross: "59.98",
        orderDiscountGross: "5.00",
        total: "54.98",
      });
      renderOrderDetail({ order });
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(summary).toHaveTextContent("Subtotal incl. VAT (after line discounts)");
      expect(within(summary).getByText("€59.98")).toBeInTheDocument();
    });

    it("does NOT render order discount row when orderDiscountGross is null", () => {
      const order = makeOrderViewModel({ orderDiscountGross: null });
      renderOrderDetail({ order });
      expect(screen.queryByTestId(ORDER_DISCOUNT_ROW)).toBeNull();
    });

    it("does NOT render order discount row when orderDiscountGross is '0.00'", () => {
      const order = makeOrderViewModel({ orderDiscountGross: "0.00" });
      renderOrderDetail({ order });
      expect(screen.queryByTestId(ORDER_DISCOUNT_ROW)).toBeNull();
    });

    it("does NOT render 'Subtotal incl. VAT (after line discounts)' when no order discount", () => {
      const order = makeOrderViewModel({ orderDiscountGross: null });
      renderOrderDetail({ order });
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(summary.textContent).not.toContain("after line discounts");
    });

    it("total incl. VAT uses order.total (after all discounts)", () => {
      const order = makeOrderViewModel({
        subtotalGross: "99.99",
        orderDiscountGross: "11.11",
        total: "88.88",
      });
      renderOrderDetail({ order });
      const summary = screen.getByTestId(ORDER_SUMMARY);
      // Total incl. VAT = order.total (final after order discount)
      expect(within(summary).getByText("€88.88")).toBeInTheDocument();
      // subtotalGross is shown as the pre-discount subtotal row
      expect(within(summary).getByText("€99.99")).toBeInTheDocument();
    });

    it("falls back to total when subtotalGross is absent", () => {
      const order = makeOrderViewModel({
        subtotalGross: null,
        total: "59.98",
      });
      renderOrderDetail({ order });
      // Scope to summary to avoid matching the items table line total
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(within(summary).getByText("€59.98")).toBeInTheDocument();
    });
  });

  // ── VAT breakdown — order-level discount explanatory note ────────────────

  describe("VAT breakdown — order-level discount note", () => {
    const vatBreakdownWithDiscount = [
      {
        taxRate: "10.00",
        taxBase: "90.00",
        vatAmount: "9.00",
        totalInclVat: "99.00",
      },
    ];

    it("renders the note inside the VAT breakdown card when orderDiscountGross > 0", () => {
      const order = makeOrderViewModel({
        orderDiscountGross: "5.00",
        vatBreakdown: vatBreakdownWithDiscount,
      });
      renderOrderDetail({ order });
      const breakdown = screen.getByTestId(VAT_BREAKDOWN);
      expect(
        within(breakdown).getByTestId(VAT_BREAKDOWN_ORDER_DISCOUNT_NOTE),
      ).toBeInTheDocument();
    });

    it("note explains proportional allocation across VAT rates", () => {
      const order = makeOrderViewModel({
        orderDiscountGross: "5.00",
        vatBreakdown: vatBreakdownWithDiscount,
      });
      renderOrderDetail({ order });
      const note = screen.getByTestId(VAT_BREAKDOWN_ORDER_DISCOUNT_NOTE);
      expect(note.textContent).toMatch(/proportionally allocated/i);
      expect(note.textContent).toMatch(/VAT rates/i);
    });

    it("note text is accounting-neutral — no marketing language", () => {
      const order = makeOrderViewModel({
        orderDiscountGross: "3.00",
        vatBreakdown: vatBreakdownWithDiscount,
      });
      renderOrderDetail({ order });
      const note = screen.getByTestId(VAT_BREAKDOWN_ORDER_DISCOUNT_NOTE);
      expect(note.textContent).not.toMatch(/sale|promo|coupon|congrats|qualified/i);
      expect(note.textContent).not.toContain("!");
    });

    it("does NOT render the note when orderDiscountGross is null", () => {
      const order = makeOrderViewModel({
        orderDiscountGross: null,
        vatBreakdown: vatBreakdownWithDiscount,
      });
      renderOrderDetail({ order });
      expect(
        screen.queryByTestId(VAT_BREAKDOWN_ORDER_DISCOUNT_NOTE),
      ).toBeNull();
    });

    it("does NOT render the note when orderDiscountGross is '0.00'", () => {
      const order = makeOrderViewModel({
        orderDiscountGross: "0.00",
        vatBreakdown: vatBreakdownWithDiscount,
      });
      renderOrderDetail({ order });
      expect(
        screen.queryByTestId(VAT_BREAKDOWN_ORDER_DISCOUNT_NOTE),
      ).toBeNull();
    });

    it("does NOT render the note when orderDiscountGross is absent (default)", () => {
      const order = makeOrderViewModel({
        vatBreakdown: vatBreakdownWithDiscount,
      });
      renderOrderDetail({ order });
      expect(
        screen.queryByTestId(VAT_BREAKDOWN_ORDER_DISCOUNT_NOTE),
      ).toBeNull();
    });

    it("does NOT render the order-summary-level 'additional discount' note", () => {
      // The old order-discount-note inside order summary must no longer exist.
      const order = makeOrderViewModel({
        orderDiscountGross: "5.00",
        vatBreakdown: vatBreakdownWithDiscount,
      });
      renderOrderDetail({ order });
      const summary = screen.getByTestId(ORDER_SUMMARY);
      expect(
        within(summary).queryByTestId("order-discount-note"),
      ).toBeNull();
    });
  });
});
