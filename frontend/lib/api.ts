import axios from "axios";

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
