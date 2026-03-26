import { describe, it, expect, beforeEach } from "vitest";
import {
  savePaymentReturnContext,
  loadAndClearPaymentReturnContext,
} from "@/lib/utils/paymentReturn";

// ---------------------------------------------------------------------------
// sessionStorage is available through the happy-dom environment configured
// in vitest.setup.ts.  Each test clears storage in beforeEach to stay
// isolated.
// ---------------------------------------------------------------------------

const STORAGE_KEY = "shopwise_payment_return_ctx";

describe("paymentReturn helpers", () => {
  beforeEach(() => {
    sessionStorage.clear();
    loadAndClearPaymentReturnContext();
  });

  describe("loadAndClearPaymentReturnContext", () => {
    it("returns null when nothing has been saved", () => {
      expect(loadAndClearPaymentReturnContext()).toBeNull();
    });

    it("returns null for invalid JSON in storage", () => {
      sessionStorage.setItem(STORAGE_KEY, "not-json{{{");
      expect(loadAndClearPaymentReturnContext()).toBeNull();
    });

    it("returns null when stored value is missing required fields", () => {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ orderId: 1 }));
      expect(loadAndClearPaymentReturnContext()).toBeNull();
    });

    it("returns null when orderId is not a number", () => {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ orderId: "1", isGuest: false }),
      );
      expect(loadAndClearPaymentReturnContext()).toBeNull();
    });

    it("returns null when isGuest is not a boolean", () => {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ orderId: 1, isGuest: "false" }),
      );
      expect(loadAndClearPaymentReturnContext()).toBeNull();
    });
  });

  describe("savePaymentReturnContext + loadAndClearPaymentReturnContext", () => {
    it("roundtrips an authenticated checkout context", () => {
      savePaymentReturnContext({ orderId: 42, isGuest: false });
      expect(loadAndClearPaymentReturnContext()).toEqual({
        orderId: 42,
        isGuest: false,
      });
    });

    it("roundtrips a guest checkout context", () => {
      savePaymentReturnContext({ orderId: 7, isGuest: true });
      expect(loadAndClearPaymentReturnContext()).toEqual({
        orderId: 7,
        isGuest: true,
      });
    });

    it("allows one strict-mode replay before clearing the context", () => {
      savePaymentReturnContext({ orderId: 5, isGuest: false });
      const first = loadAndClearPaymentReturnContext();
      const second = loadAndClearPaymentReturnContext();
      const third = loadAndClearPaymentReturnContext();
      expect(first).not.toBeNull();
      expect(second).toEqual(first);
      expect(third).toBeNull();
    });

    it("does not interfere with other sessionStorage keys", () => {
      sessionStorage.setItem("other_key", "preserved");
      savePaymentReturnContext({ orderId: 1, isGuest: false });
      loadAndClearPaymentReturnContext();
      expect(sessionStorage.getItem("other_key")).toBe("preserved");
    });
  });
});
