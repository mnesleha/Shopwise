import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { getAccessToken } from "@/lib/auth/tokens";

let refreshPromise: Promise<void> | null = null;

async function refreshSession(): Promise<void> {
  await axios.post("/api/v1/auth/refresh/", null, { withCredentials: true });
}

export const api = axios.create({
  baseURL: "/api/v1",
  timeout: 10_000,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const url = config.url;
  if (!url || url.startsWith("http")) return config;

  const [path, query] = url.split("?");
  if (!path.endsWith("/")) {
    config.url = query ? `${path}/?${query}` : `${path}/`;
  }

  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const status = error.response?.status;
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;

    if (!original || status !== 401 || original._retry) throw error;

    // SESSION_REVOKED means the server explicitly invalidated this session
    // (logout-all / email change). The refresh token is also revoked, so
    // attempting to refresh is pointless and just delays the redirect.
    // Redirect to /login immediately without retrying.
    const responseBody = error.response?.data as
      | Record<string, unknown>
      | undefined;
    if (responseBody?.code === "SESSION_REVOKED") {
      if (typeof window !== "undefined") window.location.assign("/login");
      throw error;
    }

    const url = original.url ?? "";
    if (
      url.includes("/auth/me/") ||
      url.includes("/auth/login/") ||
      url.includes("/auth/refresh/") ||
      url.includes("/auth/logout/") ||
      url.includes("/account/logout-all/")
    ) {
      throw error;
    }

    original._retry = true;

    try {
      if (!refreshPromise)
        refreshPromise = refreshSession().finally(
          () => (refreshPromise = null),
        );
      await refreshPromise;
      return api.request(original);
    } catch {
      if (typeof window !== "undefined") window.location.assign("/login");
      throw error;
    }
  },
);
