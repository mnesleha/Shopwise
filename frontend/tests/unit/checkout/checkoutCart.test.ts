import { describe, it, expect, vi, beforeEach } from "vitest";
import { checkoutCart } from "@/lib/api/checkout";
import type { CheckoutOrderDto, PaymentFlow } from "@/lib/api/checkout";
import type { CheckoutValues } from "@/components/checkout/CheckoutForm";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

const mockApiPost = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    post: (...args: unknown[]) => mockApiPost(...args),
    get: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const BASE_VALUES: CheckoutValues = {
  shipping_method: "STANDARD",
  payment_method: "CARD",
  customer_email: "buyer@example.com",
  shipping_first_name: "Jane",
  shipping_last_name: "Doe",
  shipping_company: "",
  shipping_company_id: "",
  shipping_vat_id: "",
  shipping_address_line1: "Street 1",
  shipping_address_line2: "",
  shipping_city: "Prague",
  shipping_postal_code: "11000",
  shipping_country: "CZ",
  shipping_phone: "+420123456789",
  billing_same_as_shipping: true,
  billing_first_name: "",
  billing_last_name: "",
  billing_company: "",
  billing_company_id: "",
  billing_vat_id: "",
  billing_address_line1: "",
  billing_address_line2: "",
  billing_city: "",
  billing_postal_code: "",
  billing_country: "",
  billing_phone: "",
  save_to_profile: false,
};

function makeResponse(paymentFlow: PaymentFlow = "DIRECT"): CheckoutOrderDto {
  return {
    id: 42,
    status: "CREATED",
    customer_email: "buyer@example.com",
    price_change: {
      has_changes: false,
      severity: "NONE",
      affected_items: 0,
      items: [],
    },
    payment_initiation: {
      payment_id: 1,
      payment_flow: paymentFlow,
      redirect_url:
        paymentFlow === "REDIRECT"
          ? "https://pay.example.test/session/abc"
          : null,
    },
  } as unknown as CheckoutOrderDto;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("checkoutCart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("request payload", () => {
    it("maps STANDARD shipping to backend shipping codes", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse("DIRECT") });

      await checkoutCart({ ...BASE_VALUES, shipping_method: "STANDARD" });

      const [, payload] = mockApiPost.mock.calls[0] as [
        string,
        Record<string, unknown>,
      ];
      expect(payload.shipping_provider_code).toBe("MOCK");
      expect(payload.shipping_service_code).toBe("standard");
    });

    it("maps EXPRESS shipping to backend shipping codes", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse("DIRECT") });

      await checkoutCart({ ...BASE_VALUES, shipping_method: "EXPRESS" });

      const [, payload] = mockApiPost.mock.calls[0] as [
        string,
        Record<string, unknown>,
      ];
      expect(payload.shipping_provider_code).toBe("MOCK");
      expect(payload.shipping_service_code).toBe("express");
    });

    it("includes payment_method CARD in the POST body", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse("DIRECT") });

      await checkoutCart({ ...BASE_VALUES, payment_method: "CARD" });

      const [, payload] = mockApiPost.mock.calls[0] as [
        string,
        Record<string, unknown>,
      ];
      expect(payload.payment_method).toBe("CARD");
    });

    it("includes payment_method COD in the POST body", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse("DIRECT") });

      await checkoutCart({ ...BASE_VALUES, payment_method: "COD" });

      const [, payload] = mockApiPost.mock.calls[0] as [
        string,
        Record<string, unknown>,
      ];
      expect(payload.payment_method).toBe("COD");
    });

    it("posts to /cart/checkout/", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse() });

      await checkoutCart(BASE_VALUES);

      const [url] = mockApiPost.mock.calls[0] as [string, unknown];
      expect(url).toBe("/cart/checkout/");
    });

    it("omits billing fields when billing_same_as_shipping is true", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse() });

      await checkoutCart({ ...BASE_VALUES, billing_same_as_shipping: true });

      const [, payload] = mockApiPost.mock.calls[0] as [
        string,
        Record<string, unknown>,
      ];
      expect(payload).not.toHaveProperty("billing_first_name");
      expect(payload).not.toHaveProperty("billing_address_line1");
    });

    it("includes billing fields when billing_same_as_shipping is false", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse() });

      await checkoutCart({
        ...BASE_VALUES,
        billing_same_as_shipping: false,
        billing_first_name: "John",
        billing_last_name: "Smith",
        billing_address_line1: "Other St 2",
        billing_city: "Brno",
        billing_postal_code: "60200",
        billing_country: "CZ",
        billing_phone: "+420987654321",
      });

      const [, payload] = mockApiPost.mock.calls[0] as [
        string,
        Record<string, unknown>,
      ];
      expect(payload.billing_first_name).toBe("John");
      expect(payload.billing_address_line1).toBe("Other St 2");
    });
  });

  describe("response — payment_initiation", () => {
    it("returns the payment_initiation from the response for DIRECT flow", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse("DIRECT") });

      const order = await checkoutCart(BASE_VALUES);

      expect(order.payment_initiation).toEqual({
        payment_id: 1,
        payment_flow: "DIRECT",
        redirect_url: null,
      });
    });

    it("returns payment_flow DIRECT with null redirect_url for COD", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse("DIRECT") });

      const order = await checkoutCart({
        ...BASE_VALUES,
        payment_method: "COD",
      });

      expect(order.payment_initiation.payment_flow).toBe("DIRECT");
      expect(order.payment_initiation.redirect_url).toBeNull();
    });

    it("returns the payment_initiation from the response for REDIRECT flow", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse("REDIRECT") });

      const order = await checkoutCart({
        ...BASE_VALUES,
        payment_method: "CARD",
      });

      expect(order.payment_initiation).toEqual({
        payment_id: 1,
        payment_flow: "REDIRECT",
        redirect_url: "https://pay.example.test/session/abc",
      });
    });

    it("returns payment_flow REDIRECT with non-null redirect_url for card gateway", async () => {
      mockApiPost.mockResolvedValue({ data: makeResponse("REDIRECT") });

      const order = await checkoutCart(BASE_VALUES);

      expect(order.payment_initiation.payment_flow).toBe("REDIRECT");
      expect(order.payment_initiation.redirect_url).not.toBeNull();
    });
  });
});
