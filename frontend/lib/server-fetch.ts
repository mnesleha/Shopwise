type ApiError = {
  status: number;
  message: string;
  body?: unknown;
};

export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const baseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
  const url = `${baseUrl}${path}`;

  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    // for server-side calls in dev: don't cache
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
