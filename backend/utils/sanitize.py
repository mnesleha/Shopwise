"""Markdown sanitization utilities."""

import bleach


def sanitize_markdown(raw: str) -> str:
    """Strip raw HTML from a Markdown string to defend against XSS.

    Markdown syntax (headings, bold, links, lists, code blocks, etc.) is
    preserved as plain text/markup because bleach operates only on HTML tags —
    characters like #, *, [], () that form Markdown syntax are left untouched.

    An empty *tags* allowlist combined with strip=True means every HTML element
    (including <script>, <iframe>, raw event-handler attributes, and
    javascript: URLs embedded in raw HTML) is stripped from the output.

    Args:
        raw: Raw user-supplied Markdown string.

    Returns:
        Sanitized string with all raw HTML removed; Markdown syntax intact.
    """
    if not raw:
        return raw

    return bleach.clean(raw, tags=[], attributes={}, strip=True)
