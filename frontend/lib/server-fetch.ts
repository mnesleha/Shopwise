import { cookies } from "next/headers";

type ApiError = {
  status: number;
  message: string;
  body?: unknown;
};

type ApiFetchInit = RequestInit & {
  forwardCookies?: boolean;
};

function buildCookieHeader(): string {
  // NOTE: In Next 16, cookies() is async in Server Components.
  // This helper is kept sync-only; actual reading is in apiFetch.
  return "";
}

export async function apiFetch<T>(
  path: string,
  init?: ApiFetchInit,
): Promise<T> {
  const baseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
  const url = `${baseUrl}${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };

  if (init?.forwardCookies) {
    const cookieStore = await cookies();
    const cookieHeader = cookieStore
      .getAll()
      .map((c) => `${c.name}=${c.value}`)
      .join("; ");

    if (cookieHeader) {
      headers["Cookie"] = cookieHeader;
    }
  }

  const res = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    let body: unknown = undefined;
    try {
      body = await res.json();
    } catch {
      // ignore
    }
    const err: ApiError = {
      status: res.status,
      message: `API request failed: ${res.status} ${res.statusText}`,
      body,
    };
    throw err;
  }

  return (await res.json()) as T;
}
