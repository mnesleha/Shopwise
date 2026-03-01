type MailpitMessageSummary = {
  ID: string;
  Subject: string;
  From: { Address: string; Name: string }[];
  To: { Address: string; Name: string }[];
  Created: string; // ISO date string
};

type MailpitMessagesResponse = {
  messages: MailpitMessageSummary[];
  total: number;
  count: number;
  start: number;
};

type MailpitSearchResponse = {
  messages: MailpitMessageSummary[];
  total: number;
  count: number;
  start: number;
};

type MailpitMessageHtmlResponse = {
  HTML: string;
};

type MailpitMessageTextResponse = {
  Text: string;
};

/**
 * Minimal Mailpit v1 client for deterministic E2E email assertions.
 *
 * API docs: https://mailpit.axllent.org/docs/api-v1/
 */
export class MailpitClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = (
      baseUrl ??
      process.env.MAILPIT_BASE_URL ??
      "http://localhost:8025"
    ).replace(/\/+$/, "");
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        "content-type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(
        `Mailpit API ${path} failed: ${res.status} ${res.statusText} ${body}`,
      );
    }
    return (await res.json()) as T;
  }

  /** Delete ALL captured messages. Good to call in test beforeEach for isolation. */
  async deleteAllMessages(): Promise<void> {
    // Mailpit API v1 supports DELETE /api/v1/messages to delete all messages.
    // (If your version differs, we can switch to iterating deletes by ID.)
    const res = await fetch(`${this.baseUrl}/api/v1/messages`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(
        `Mailpit deleteAllMessages failed: ${res.status} ${res.statusText} ${body}`,
      );
    }
  }

  /** Search messages using Mailpit query syntax (e.g., to:someone@example.com subject:"Verify") */
  async search(query: string, limit = 50): Promise<MailpitSearchResponse> {
    const q = encodeURIComponent(query);
    return this.request<MailpitSearchResponse>(
      `/api/v1/search?query=${q}&limit=${limit}`,
    );
  }

  /** Get raw message list (usually you want search instead). */
  async list(limit = 50): Promise<MailpitMessagesResponse> {
    return this.request<MailpitMessagesResponse>(
      `/api/v1/messages?limit=${limit}`,
    );
  }

  /** Get rendered HTML body of a message. */
  async getMessageHtml(id: string): Promise<string> {
    const data = await this.request<MailpitMessageHtmlResponse>(
      `/api/v1/message/${encodeURIComponent(id)}/html`,
    );
    return data.HTML ?? "";
  }

  /** Get plain text body of a message. */
  async getMessageText(id: string): Promise<string> {
    const data = await this.request<MailpitMessageTextResponse>(
      `/api/v1/message/${encodeURIComponent(id)}/text`,
    );
    return data.Text ?? "";
  }

  /** Get body of a message (html/text endpoint not supported). */
  async getMessage(id: string): Promise<string> {
    const data = await this.request<MailpitMessageTextResponse>(
      `/api/v1/message/${encodeURIComponent(id)}`,
    );
    return data.Text ?? "";
  }

  /**
   * Wait until a message matching recipient + subject appears.
   * Uses /search to avoid race conditions.
   */
  async waitForMessage(opts: {
    to: string;
    subjectIncludes?: string;
    timeoutMs?: number;
    pollIntervalMs?: number;
  }): Promise<MailpitMessageSummary> {
    const timeoutMs = opts.timeoutMs ?? 15_000;
    const pollIntervalMs = opts.pollIntervalMs ?? 500;

    const subjectPart = opts.subjectIncludes
      ? ` subject:"${opts.subjectIncludes.replace(/"/g, '\\"')}"`
      : "";
    const query = `to:${opts.to}${subjectPart}`;

    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const res = await this.search(query, 10);
      const msg = res.messages?.[0];
      if (msg) return msg;
      await new Promise((r) => setTimeout(r, pollIntervalMs));
    }
    throw new Error(
      `Timed out waiting for email to=${opts.to} subject~=${opts.subjectIncludes ?? "(any)"}`,
    );
  }

  /**
   * Extract first matching URL from email body.
   * Tries HTML first, then text.
   */
  async extractLinkFromMessage(id: string, pattern: RegExp): Promise<string> {
    // const html = await this.getMessageHtml(id);
    // const htmlMatch = html.match(pattern);
    // if (htmlMatch?.[0]) return htmlMatch[0];

    const text = await this.getMessage(id);
    const textMatch = text.match(pattern);
    if (textMatch?.[0]) return textMatch[0];

    throw new Error(`No link matching ${pattern} found in message ${id}`);
  }

  /**
   * Specifically extract the Shopwise verify-email link.
   *
   * @param rewriteOrigin - When provided, replaces the origin (scheme + host +
   *   port) of the extracted URL with this value.  Pass `process.env.E2E_BASE_URL`
   *   so the link uses the same origin the browser logged in with; otherwise the
   *   browser's session cookies (set on `localhost`) won't be sent to `127.0.0.1`
   *   and `refresh()` will return `isAuthenticated: false`.
   */
  async getVerifyEmailLink(
    messageId: string,
    rewriteOrigin?: string,
  ): Promise<string> {
    // Matches e.g. http://localhost:3000/verify-email/?token=ABC... (or https, trailing slash optional)
    const re =
      /https?:\/\/[^\s"'<>()]+\/verify-email\/?\?token=[A-Za-z0-9._-]+/g;
    let link = await this.extractLinkFromMessage(messageId, re);
    if (rewriteOrigin) {
      // Strip trailing slash from rewriteOrigin to avoid double-slash
      const origin = rewriteOrigin.replace(/\/$/, "");
      link = link.replace(/^https?:\/\/[^/]+/, origin);
    }
    return link;
  }
}
