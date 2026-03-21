/**
 * Unit tests for buildCheckoutPrefill — pure mapping helper.
 *
 * Spec coverage:
 * 1. Both default_shipping and default_billing exist (different) →
 *    shipping from shipping, billing from billing, billing_same_as_shipping = false
 * 2. Both defaults exist but point to the same address fields →
 *    billing_same_as_shipping = true
 * 3. Only shipping default →
 *    both sides filled from shipping, billing_same_as_shipping = true
 * 4. Only billing default →
 *    both sides filled from billing (low-friction fallback), billing_same_as_shipping = true
 * 5. Neither default →
 *    no address fields, only email if provided
 * 6. Email prefill from account
 * 7. Phone prefill from profile address
 * 8. null / missing profile → only email
 */
import { describe, it, expect } from "vitest";
import { buildCheckoutPrefill } from "@/lib/utils/buildCheckoutPrefill";
import type { AddressDto, ProfileDto } from "@/lib/api/profile";

// ---------------------------------------------------------------------------
// Fixture factories
// ---------------------------------------------------------------------------

function makeAddress(overrides: Partial<AddressDto> = {}): AddressDto {
  return {
    id: 1,
    first_name: "John",
    last_name: "Doe",
    street_line_1: "Main Street 1",
    street_line_2: "",
    city: "Prague",
    postal_code: "11000",
    country: "CZ",
    company: "",
    vat_id: "",
    phone: "+420123456789",
    ...overrides,
  };
}

function makeProfile(overrides: Partial<ProfileDto> = {}): ProfileDto {
  return {
    id: 1,
    default_shipping_address: null,
    default_billing_address: null,
    ...overrides,
  };
}

/** Expected shipping fields derived from a given address fixture. */
function expectedShipping(addr: AddressDto) {
  return {
    shipping_name: `${addr.first_name} ${addr.last_name}`.trim(),
    shipping_address_line1: addr.street_line_1,
    shipping_address_line2: addr.street_line_2,
    shipping_city: addr.city,
    shipping_postal_code: addr.postal_code,
    shipping_country: addr.country,
    shipping_phone: addr.phone,
  };
}

/** Expected billing fields derived from a given address fixture. */
function expectedBilling(addr: AddressDto) {
  return {
    billing_name: `${addr.first_name} ${addr.last_name}`.trim(),
    billing_address_line1: addr.street_line_1,
    billing_address_line2: addr.street_line_2,
    billing_city: addr.city,
    billing_postal_code: addr.postal_code,
    billing_country: addr.country,
    billing_phone: addr.phone,
  };
}

// ---------------------------------------------------------------------------
// Test suites
// ---------------------------------------------------------------------------

describe("buildCheckoutPrefill", () => {
  // ── Rule 1: both defaults, different addresses ────────────────────────────
  describe("both default_shipping and default_billing exist (different)", () => {
    const shipping = makeAddress({
      id: 1,
      first_name: "Alice",
      last_name: "Shipping",
      street_line_1: "Ship Lane 1",
      city: "Prague",
      phone: "+420111000000",
    });
    const billing = makeAddress({
      id: 2,
      first_name: "Bob",
      last_name: "Billing",
      street_line_1: "Bill Road 2",
      city: "Brno",
      phone: "+420222000000",
    });
    const profile = makeProfile({
      default_shipping_address: 1,
      default_billing_address: 2,
    });

    const result = buildCheckoutPrefill({
      profile,
      addresses: [shipping, billing],
      email: "user@example.com",
    });

    it("prefills shipping from default_shipping_address", () => {
      expect(result).toMatchObject(expectedShipping(shipping));
    });

    it("prefills billing from default_billing_address", () => {
      expect(result).toMatchObject(expectedBilling(billing));
    });

    it("sets billing_same_as_shipping = false when addresses differ", () => {
      expect(result.billing_same_as_shipping).toBe(false);
    });

    it("includes email in the prefill", () => {
      expect(result.customer_email).toBe("user@example.com");
    });
  });

  // ── Rule 1 variant: both defaults but same address content ────────────────
  describe("both defaults exist and point to identical address fields", () => {
    const sharedAddr = makeAddress({ id: 1 });
    const duplicateContent = makeAddress({ id: 2 }); // same fields, different id
    const profile = makeProfile({
      default_shipping_address: 1,
      default_billing_address: 2,
    });

    const result = buildCheckoutPrefill({
      profile,
      addresses: [sharedAddr, duplicateContent],
    });

    it("sets billing_same_as_shipping = true when addresses match", () => {
      expect(result.billing_same_as_shipping).toBe(true);
    });
  });

  // ── Rule 2: only shipping ─────────────────────────────────────────────────
  describe("only default_shipping_address exists", () => {
    const shipping = makeAddress({
      id: 5,
      city: "Ostrava",
      phone: "+420333000000",
    });
    const profile = makeProfile({ default_shipping_address: 5 });

    const result = buildCheckoutPrefill({
      profile,
      addresses: [shipping],
      email: "ship@example.com",
    });

    it("prefills shipping from default_shipping_address", () => {
      expect(result).toMatchObject(expectedShipping(shipping));
    });

    it("prefills billing from default_shipping_address (fallback)", () => {
      expect(result).toMatchObject(expectedBilling(shipping));
    });

    it("sets billing_same_as_shipping = true", () => {
      expect(result.billing_same_as_shipping).toBe(true);
    });

    it("includes email", () => {
      expect(result.customer_email).toBe("ship@example.com");
    });
  });

  // ── Rule 3: only billing ──────────────────────────────────────────────────
  describe("only default_billing_address exists", () => {
    const billing = makeAddress({
      id: 7,
      city: "Liberec",
      phone: "+420444000000",
    });
    const profile = makeProfile({ default_billing_address: 7 });

    const result = buildCheckoutPrefill({
      profile,
      addresses: [billing],
      email: "bill@example.com",
    });

    it("prefills shipping from default_billing_address (low-friction fallback)", () => {
      expect(result).toMatchObject(expectedShipping(billing));
    });

    it("prefills billing from default_billing_address", () => {
      expect(result).toMatchObject(expectedBilling(billing));
    });

    it("sets billing_same_as_shipping = true", () => {
      expect(result.billing_same_as_shipping).toBe(true);
    });

    it("includes email", () => {
      expect(result.customer_email).toBe("bill@example.com");
    });
  });

  // ── Rule 4: neither address ───────────────────────────────────────────────
  describe("no default addresses", () => {
    const profile = makeProfile();

    const result = buildCheckoutPrefill({
      profile,
      addresses: [],
      email: "empty@example.com",
    });

    it("does not include any shipping address fields", () => {
      expect(result.shipping_name).toBeUndefined();
      expect(result.shipping_city).toBeUndefined();
      expect(result.shipping_phone).toBeUndefined();
    });

    it("does not include any billing address fields", () => {
      expect(result.billing_name).toBeUndefined();
      expect(result.billing_city).toBeUndefined();
      expect(result.billing_phone).toBeUndefined();
    });

    it("does not set billing_same_as_shipping", () => {
      expect(result.billing_same_as_shipping).toBeUndefined();
    });

    it("still includes email when provided", () => {
      expect(result.customer_email).toBe("empty@example.com");
    });
  });

  // ── Null profile ──────────────────────────────────────────────────────────
  describe("null profile (unauthenticated or fetch failed)", () => {
    const result = buildCheckoutPrefill({
      profile: null,
      addresses: [],
      email: "guest@example.com",
    });

    it("returns only email prefill", () => {
      expect(result.customer_email).toBe("guest@example.com");
      expect(result.shipping_name).toBeUndefined();
    });
  });

  describe("null profile with no email", () => {
    const result = buildCheckoutPrefill({ profile: null, addresses: [] });

    it("returns an empty object", () => {
      expect(result).toEqual({});
    });
  });

  // ── Email prefill ─────────────────────────────────────────────────────────
  describe("email prefill", () => {
    it("includes email when provided alongside address prefill", () => {
      const addr = makeAddress({ id: 1 });
      const result = buildCheckoutPrefill({
        profile: makeProfile({ default_shipping_address: 1 }),
        addresses: [addr],
        email: "prefilled@example.com",
      });
      expect(result.customer_email).toBe("prefilled@example.com");
    });

    it("omits customer_email when email is not provided", () => {
      const result = buildCheckoutPrefill({
        profile: makeProfile(),
        addresses: [],
      });
      expect(result.customer_email).toBeUndefined();
    });
  });

  // ── Phone prefill ─────────────────────────────────────────────────────────
  describe("phone prefill", () => {
    it("maps address phone to shipping_phone", () => {
      const addr = makeAddress({ id: 1, phone: "+420999888777" });
      const result = buildCheckoutPrefill({
        profile: makeProfile({ default_shipping_address: 1 }),
        addresses: [addr],
      });
      expect(result.shipping_phone).toBe("+420999888777");
    });

    it("maps address phone to billing_phone when billing falls back to shipping", () => {
      const addr = makeAddress({ id: 1, phone: "+420999888777" });
      const result = buildCheckoutPrefill({
        profile: makeProfile({ default_shipping_address: 1 }),
        addresses: [addr],
      });
      expect(result.billing_phone).toBe("+420999888777");
    });

    it("maps distinct phones when shipping and billing come from different addresses", () => {
      const s = makeAddress({ id: 1, phone: "+420111111111" });
      const b = makeAddress({ id: 2, phone: "+420222222222", city: "Brno" });
      const result = buildCheckoutPrefill({
        profile: makeProfile({
          default_shipping_address: 1,
          default_billing_address: 2,
        }),
        addresses: [s, b],
      });
      expect(result.shipping_phone).toBe("+420111111111");
      expect(result.billing_phone).toBe("+420222222222");
    });
  });

  // ── First/last name join ───────────────────────────────────────────────────
  describe("name mapping", () => {
    it("joins first_name and last_name into shipping_name", () => {
      const addr = makeAddress({
        id: 1,
        first_name: "Jane",
        last_name: "Smith",
      });
      const result = buildCheckoutPrefill({
        profile: makeProfile({ default_shipping_address: 1 }),
        addresses: [addr],
      });
      expect(result.shipping_name).toBe("Jane Smith");
    });

    it("joins first_name and last_name into billing_name", () => {
      const addr = makeAddress({
        id: 1,
        first_name: "Jane",
        last_name: "Smith",
      });
      const result = buildCheckoutPrefill({
        profile: makeProfile({ default_shipping_address: 1 }),
        addresses: [addr],
      });
      expect(result.billing_name).toBe("Jane Smith");
    });
  });
});
