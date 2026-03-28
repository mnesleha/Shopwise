import { api } from "@/lib/api";
import type { CheckoutValues } from "@/components/checkout/CheckoutForm";
import type { BaseOrderDto } from "@/lib/api/orders";

// ---------------------------------------------------------------------------
// Price-change payload types (mirrors backend carts/services/price_change.py)
// ---------------------------------------------------------------------------

export type PriceChangeSeverity = "NONE" | "INFO" | "WARNING";
export type PriceChangeDirection = "UP" | "DOWN";

export type PriceChangeItem = {
  product_id: number;
  product_name: string;
  old_unit_gross: string;
  new_unit_gross: string;
  /**
   * Unsigned magnitude of the price change; always a positive decimal string, e.g. "2.50".
   * Use `direction` to determine whether this represents an increase or decrease.
   */
  absolute_change: string;
  /** Percentage change as a decimal string, e.g. "12.50". */
  percent_change: string;
  direction: PriceChangeDirection;
  severity: PriceChangeSeverity;
};

export type PriceChangePayload = {
  has_changes: boolean;
  severity: PriceChangeSeverity;
  affected_items: number;
  items: PriceChangeItem[];
};

// ---------------------------------------------------------------------------
// Payment initiation types (mirrors backend payment_orchestration / checkout)
// ---------------------------------------------------------------------------

/** Payment methods supported in the checkout request. */
export type PaymentMethod = "CARD" | "COD";

/**
 * Normalized payment flow classification returned by the backend after
 * provider-agnostic payment initiation:
 *
 * - "REDIRECT" — hosted/redirect provider (e.g. card gateway).
 *   The customer must be sent to `redirect_url` to complete payment.
 *   The backend will confirm success via webhook; frontend must not assume PAID.
 *
 * - "DIRECT" — synchronous provider (e.g. COD).
 *   Payment is applied immediately; order is PAID after checkout.
 */
export type PaymentFlow = "REDIRECT" | "DIRECT";

/**
 * Provider-agnostic payment initiation result attached to the checkout
 * response.  Mirrors `PaymentInitiationSerializer` on the backend.
 */
export type PaymentInitiation = {
  /** Database PK of the created Payment record. */
  payment_id: number;
  /** Normalized flow type — drives post-checkout navigation. */
  payment_flow: PaymentFlow;
  /**
   * Hosted gateway redirect URL.  Non-null only for REDIRECT flow;
   * null for DIRECT flow.
   */
  redirect_url: string | null;
};

/**
 * Checkout-specific order response.  Extends the base order DTO with the
 * price-change summary and payment initiation info returned by
 * POST /cart/checkout/.
 */
export type CheckoutOrderDto = BaseOrderDto & {
  price_change: PriceChangePayload;
  payment_initiation: PaymentInitiation;
};

export async function checkoutCart(
  values: CheckoutValues,
): Promise<CheckoutOrderDto> {
  const payload = {
    customer_email: values.customer_email,

    shipping_first_name: values.shipping_first_name,
    shipping_last_name: values.shipping_last_name,
    shipping_company: values.shipping_company,
    shipping_company_id: values.shipping_company_id,
    shipping_vat_id: values.shipping_vat_id,
    shipping_address_line1: values.shipping_address_line1,
    shipping_address_line2: values.shipping_address_line2,
    shipping_city: values.shipping_city,
    shipping_postal_code: values.shipping_postal_code,
    shipping_country: values.shipping_country,
    shipping_phone: values.shipping_phone,

    billing_same_as_shipping: values.billing_same_as_shipping,

    ...(values.billing_same_as_shipping
      ? {}
      : {
          billing_first_name: values.billing_first_name,
          billing_last_name: values.billing_last_name,
          billing_company: values.billing_company,
          billing_company_id: values.billing_company_id,
          billing_vat_id: values.billing_vat_id,
          billing_address_line1: values.billing_address_line1,
          billing_address_line2: values.billing_address_line2,
          billing_city: values.billing_city,
          billing_postal_code: values.billing_postal_code,
          billing_country: values.billing_country,
          billing_phone: values.billing_phone,
        }),

    save_to_profile: values.save_to_profile,
    // Forward the payment method selected by the user to the backend.
    // The backend resolver maps this to the appropriate payment provider.
    payment_method: values.payment_method,
  };

  const res = await api.post<CheckoutOrderDto>("/cart/checkout/", payload);
  return res.data;
}

/**
 * GET /cart/checkout/preflight/
 *
 * Resolves the current cart pricing and compares each item's gross
 * price_at_add_time against the current pipeline price.  Returns a
 * price_change payload without creating an order.
 *
 * Throws AxiosError (status 404) when no active cart exists.
 */
export async function getCheckoutPreflight(): Promise<PriceChangePayload> {
  const res = await api.get<{ price_change: PriceChangePayload }>(
    "/cart/checkout/preflight/",
  );
  return res.data.price_change;
}
