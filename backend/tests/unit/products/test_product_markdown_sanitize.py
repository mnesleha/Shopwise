"""Tests for Markdown sanitization of Product.full_description.

Covers the sanitize_markdown() utility directly and the Product.save() hook
that applies it. All raw HTML must be stripped; Markdown syntax must survive.
"""

import pytest

from utils.sanitize import sanitize_markdown
from products.models import Product


# ---------------------------------------------------------------------------
# Unit tests for sanitize_markdown()
# ---------------------------------------------------------------------------


class TestSanitizeMarkdown:
    def test_script_tag_is_stripped(self):
        raw = 'Hello <script>alert("xss")</script> world'
        assert sanitize_markdown(raw) == 'Hello alert("xss") world'

    def test_script_tag_with_src_is_stripped(self):
        raw = '<script src="https://evil.example/payload.js"></script>'
        assert sanitize_markdown(raw) == ""

    def test_javascript_href_in_raw_html_is_stripped(self):
        # Raw HTML anchor with javascript: URL — the tag must be stripped.
        raw = '<a href="javascript:alert(1)">click</a>'
        assert sanitize_markdown(raw) == "click"

    def test_inline_event_handler_is_stripped(self):
        raw = '<img src="x" onerror="alert(1)">'
        assert sanitize_markdown(raw) == ""

    def test_iframe_is_stripped(self):
        raw = '<iframe src="https://evil.example"></iframe>'
        assert sanitize_markdown(raw) == ""

    def test_plain_markdown_heading_is_preserved(self):
        raw = "## Section title"
        assert sanitize_markdown(raw) == "## Section title"

    def test_markdown_bold_and_italic_are_preserved(self):
        raw = "**bold** and *italic*"
        assert sanitize_markdown(raw) == "**bold** and *italic*"

    def test_markdown_link_syntax_is_preserved(self):
        # Markdown link syntax must not be touched — only raw HTML is stripped.
        raw = "[Visit site](https://example.com)"
        assert sanitize_markdown(raw) == "[Visit site](https://example.com)"

    def test_markdown_code_block_is_preserved(self):
        raw = "```python\nprint('hello')\n```"
        assert sanitize_markdown(raw) == "```python\nprint('hello')\n```"

    def test_empty_string_is_returned_unchanged(self):
        assert sanitize_markdown("") == ""

    def test_mixed_markdown_and_html_strips_html_only(self):
        raw = "# Title\n\n<script>evil()</script>\n\nNormal **text**."
        result = sanitize_markdown(raw)
        assert "<script>" not in result
        assert "# Title" in result
        assert "Normal **text**." in result


# ---------------------------------------------------------------------------
# Integration tests: Product.save() applies sanitization automatically
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProductSaveAppliesSanitization:
    def _make_product(self, full_description: str) -> Product:
        product = Product(
            name="Test product",
            price="9.99",
            stock_quantity=10,
            full_description=full_description,
        )
        product.save()
        return product

    def test_script_tag_stripped_on_save(self):
        p = self._make_product('<script>evil()</script>## Description')
        assert "<script>" not in p.full_description
        assert "## Description" in p.full_description

    def test_javascript_link_stripped_on_save(self):
        p = self._make_product('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in p.full_description

    def test_clean_markdown_survives_save(self):
        md = "## Features\n\n- **Fast**\n- [Docs](https://example.com)"
        p = self._make_product(md)
        assert p.full_description == md

    def test_sanitization_persisted_to_db(self):
        p = self._make_product('<script>x</script>Hello')
        refreshed = Product.objects.get(pk=p.pk)
        assert "<script>" not in refreshed.full_description
        assert "Hello" in refreshed.full_description
