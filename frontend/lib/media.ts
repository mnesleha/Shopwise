/**
 * Media URL helpers.
 *
 * Backend stores relative paths in markdown (e.g. /media/products/descriptions/abc.png).
 * The browser would look for those on port 3000 (Next.js dev server), where they don't exist.
 * This helper prepends the backend origin so the absolute URL is constructed at render time —
 * the stored value in the database always stays relative.
 *
 * Configuration:
 *   NEXT_PUBLIC_BACKEND_ORIGIN  — e.g. "http://127.0.0.1:8000"
 *   Falls back to "http://127.0.0.1:8000" when not set.
 */

const BACKEND_ORIGIN =
  process.env.NEXT_PUBLIC_BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

/**
 * Resolve a potentially relative media URL to an absolute URL.
 *
 * Rules:
 *   - Already absolute (http:// / https://)  → returned as-is.
 *   - Starts with "/"                         → prepend BACKEND_ORIGIN.
 *   - Otherwise                               → prepend BACKEND_ORIGIN + "/".
 */
export function resolveMediaUrl(src: string): string {
  if (src.startsWith("http://") || src.startsWith("https://")) {
    return src;
  }
  if (src.startsWith("/")) {
    return `${BACKEND_ORIGIN}${src}`;
  }
  return `${BACKEND_ORIGIN}/${src}`;
}
