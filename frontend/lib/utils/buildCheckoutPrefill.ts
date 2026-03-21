import type { AddressDto, ProfileDto } from "@/lib/api/profile";
import type { CheckoutValues } from "@/components/checkout/CheckoutForm";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Combine first and last name into the full-name string used by checkout fields.
 */
function fullName(addr: AddressDto): string {
  return `${addr.first_name} ${addr.last_name}`.trim();
}

/**
 * Map a profile address into the shipping-address portion of CheckoutValues.
 */
function toShipping(
  addr: AddressDto,
): Pick<
  CheckoutValues,
  | "shipping_name"
  | "shipping_address_line1"
  | "shipping_address_line2"
  | "shipping_city"
  | "shipping_postal_code"
  | "shipping_country"
  | "shipping_phone"
> {
  return {
    shipping_name: fullName(addr),
    shipping_address_line1: addr.street_line_1,
    shipping_address_line2: addr.street_line_2,
    shipping_city: addr.city,
    shipping_postal_code: addr.postal_code,
    shipping_country: addr.country,
    shipping_phone: addr.phone,
  };
}

/**
 * Map a profile address into the billing-address portion of CheckoutValues.
 */
function toBilling(
  addr: AddressDto,
): Pick<
  CheckoutValues,
  | "billing_name"
  | "billing_address_line1"
  | "billing_address_line2"
  | "billing_city"
  | "billing_postal_code"
  | "billing_country"
  | "billing_phone"
> {
  return {
    billing_name: fullName(addr),
    billing_address_line1: addr.street_line_1,
    billing_address_line2: addr.street_line_2,
    billing_city: addr.city,
    billing_postal_code: addr.postal_code,
    billing_country: addr.country,
    billing_phone: addr.phone,
  };
}

/**
 * Return true when two addresses represent the same physical location and
 * contact info (i.e. the billing address is effectively the same as shipping).
 * Comparison is field-level; the address `id` is intentionally ignored.
 */
function addressesMatch(a: AddressDto, b: AddressDto): boolean {
  return (
    a.first_name === b.first_name &&
    a.last_name === b.last_name &&
    a.street_line_1 === b.street_line_1 &&
    a.street_line_2 === b.street_line_2 &&
    a.city === b.city &&
    a.postal_code === b.postal_code &&
    a.country === b.country &&
    a.phone === b.phone
  );
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Build the checkout form's `initialValues` from the authenticated user's
 * profile defaults and account email.
 *
 * Fallback rules:
 * 1. Both defaults exist → ship from shipping, bill from billing.
 *    `billing_same_as_shipping` is true only when the two addresses match.
 * 2. Only shipping default → ship from shipping, bill fallback = same.
 *    `billing_same_as_shipping = true`.
 * 3. Only billing default → ship fallback = billing, bill from billing.
 *    `billing_same_as_shipping = true`.
 * 4. Neither exists → return email-only prefill (or empty if no email).
 *
 * The caller is responsible for fetching the data; this function is pure and
 * has no side-effects.
 */
export function buildCheckoutPrefill({
  profile,
  addresses,
  email,
}: {
  profile: ProfileDto | null;
  addresses: AddressDto[];
  email?: string;
}): Partial<CheckoutValues> {
  const prefill: Partial<CheckoutValues> = {};

  if (email) {
    prefill.customer_email = email;
  }

  if (!profile) {
    return prefill;
  }

  const byId = (id: number | null): AddressDto | undefined =>
    id != null ? addresses.find((a) => a.id === id) : undefined;

  const shippingAddr = byId(profile.default_shipping_address);
  const billingAddr = byId(profile.default_billing_address);

  if (shippingAddr && billingAddr) {
    // Rule 1: both defaults present
    const same = addressesMatch(shippingAddr, billingAddr);
    return {
      ...prefill,
      ...toShipping(shippingAddr),
      ...toBilling(billingAddr),
      billing_same_as_shipping: same,
    };
  }

  if (shippingAddr) {
    // Rule 2: only shipping → use it for both
    return {
      ...prefill,
      ...toShipping(shippingAddr),
      ...toBilling(shippingAddr),
      billing_same_as_shipping: true,
    };
  }

  if (billingAddr) {
    // Rule 3: only billing → use it for both (low-friction fallback)
    return {
      ...prefill,
      ...toShipping(billingAddr),
      ...toBilling(billingAddr),
      billing_same_as_shipping: true,
    };
  }

  // Rule 4: neither address exists — email-only prefill (may be empty too)
  return prefill;
}
