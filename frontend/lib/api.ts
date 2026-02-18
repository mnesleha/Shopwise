import axios from "axios";
import { getAccessToken } from "@/lib/auth/tokens";

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
