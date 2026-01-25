// This file configures the initialization of Sentry on the server.
// The config you add here will be used whenever the server handles a request.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

const SENTRY_ENABLED = process.env.SENTRY_ENABLED !== "false";

if (SENTRY_ENABLED) {
  Sentry.init({
    dsn: "https://e0d954f9de8b5a2fb932db9d7f598d2e@o4510765395476480.ingest.de.sentry.io/4510765410025552",

    // Define how likely traces are sampled. Adjust this value in production, or use tracesSampler for greater control.
    tracesSampleRate: 1,

    // Enable logs to be sent to Sentry
    enableLogs: true,

    // Enable sending user PII (Personally Identifiable Information)
    // https://docs.sentry.io/platforms/javascript/guides/nextjs/configuration/options/#sendDefaultPii
    sendDefaultPii: true,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
  });
}
