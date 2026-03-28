/**
 * Payment return context helpers.
 *
 * Before performing a browser redirect to a hosted payment page, the checkout
 * flow saves a small context object to sessionStorage so the return page can
 * identify which order to check and how to navigate afterward.
 *
 * sessionStorage is appropriate here:
 * - It survives the outbound redirect and the inbound return within the same
 *   browser tab.
 * - It is automatically cleared when the tab is closed, preventing stale state.
 * - It is not sent to servers, so there is no privacy concern.
 */

const STORAGE_KEY = "shopwise_payment_return_ctx";
let replayRawContext: string | null = null;

/**
 * Minimal context stored before a hosted-payment redirect.
 *
 * `isGuest` true  → guest checkout; the return page shows a generic success
 *                   message (no backend order fetch possible without the token
 *                   that was emailed to the customer).
 * `isGuest` false → authenticated checkout; the return page fetches order
 *                   status from the backend using the session cookie.
 */
export type PaymentReturnContext = {
  orderId: number;
  isGuest: boolean;
};

/**
 * Persist payment return context before the browser redirect.
 *
 * Silent no-op when sessionStorage is unavailable (e.g. private-mode
 * browsers that have storage access blocked).
 */
export function savePaymentReturnContext(ctx: PaymentReturnContext): void {
  try {
    replayRawContext = null;
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(ctx));
  } catch {
    // sessionStorage may be blocked in some environments — acceptable
  }
}

function parseStoredContext(raw: string): PaymentReturnContext | null {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      typeof (parsed as Record<string, unknown>).orderId === "number" &&
      typeof (parsed as Record<string, unknown>).isGuest === "boolean"
    ) {
      return parsed as PaymentReturnContext;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Read and immediately remove the stored payment return context.
 *
 * Removes the entry on read so that a page refresh after viewing the return
 * page does not re-trigger the order fetch with stale context.
 *
 * Returns `null` when:
 * - No context was saved (direct navigation, sessionStorage unavailable).
 * - The stored value cannot be parsed or is structurally invalid.
 */
export function loadAndClearPaymentReturnContext(): PaymentReturnContext | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      sessionStorage.removeItem(STORAGE_KEY);
      replayRawContext = raw;
      return parseStoredContext(raw);
    }

    if (replayRawContext) {
      const replay = replayRawContext;
      replayRawContext = null;
      return parseStoredContext(replay);
    }

    return null;
  } catch {
    replayRawContext = null;
    return null;
  }
}
