export function hasAccessToken(): boolean {
  if (typeof window === "undefined") return false;
  const token = window.localStorage.getItem("access_token");
  return Boolean(token);
}
