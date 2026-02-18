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
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }

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

    const url = original.url ?? "";
    if (
      url.includes("/auth/login/") ||
      url.includes("/auth/refresh/") ||
      url.includes("/auth/logout/")
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
