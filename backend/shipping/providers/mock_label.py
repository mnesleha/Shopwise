from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape

from shipping.providers.base import GeneratedShippingLabel


def build_mock_shipping_label(
    *,
    carrier_name: str,
    service_name: str,
    tracking_number: str,
    order_reference: str,
    receiver: dict[str, Any],
) -> GeneratedShippingLabel:
    receiver_lines = _receiver_lines(receiver)
    qr_svg = _qr_svg(tracking_number, start_x=506, start_y=122, cell_size=5)
    receiver_svg = "".join(
        f'<text x="72" y="{286 + (index * 24)}" font-size="18" font-family="Arial, sans-serif" fill="#111827">{escape(line)}</text>'
        for index, line in enumerate(receiver_lines)
    )

    svg = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"760\" height=\"560\" viewBox=\"0 0 760 560\" role=\"img\" aria-label=\"Mock shipping label\">
  <rect width=\"760\" height=\"560\" fill=\"#f8fafc\"/>
  <rect x=\"24\" y=\"24\" width=\"712\" height=\"512\" rx=\"24\" fill=\"#ffffff\" stroke=\"#d1d5db\" stroke-width=\"2\"/>
  <rect x=\"48\" y=\"48\" width=\"204\" height=\"44\" rx=\"12\" fill=\"#111827\"/>
    <text x=\"150\" y=\"77\" text-anchor=\"middle\" font-size=\"22\" font-family=\"Arial, sans-serif\" font-weight=\"700\" fill=\"#f9fafb\">SHIPPING LABEL</text>
  <text x=\"48\" y=\"132\" font-size=\"30\" font-family=\"Arial, sans-serif\" font-weight=\"700\" fill=\"#111827\">{escape(carrier_name)} - {escape(service_name)}</text>
  <text x=\"48\" y=\"168\" font-size=\"18\" font-family=\"Arial, sans-serif\" fill=\"#4b5563\">Order reference: {escape(order_reference)}</text>
  <text x=\"48\" y=\"198\" font-size=\"18\" font-family=\"Arial, sans-serif\" fill=\"#4b5563\">Tracking number: {escape(tracking_number)}</text>
  <rect x=\"48\" y=\"226\" width=\"356\" height=\"198\" rx=\"18\" fill=\"#f8fafc\" stroke=\"#e5e7eb\" stroke-width=\"2\"/>
  <text x=\"72\" y=\"258\" font-size=\"18\" font-family=\"Arial, sans-serif\" font-weight=\"700\" fill=\"#111827\">Ship to</text>
  {receiver_svg}
    <rect x=\"440\" y=\"64\" width=\"256\" height=\"244\" rx=\"16\" fill=\"#f3f4f6\" stroke=\"#d1d5db\" stroke-width=\"2\"/>
    <text x=\"456\" y=\"90\" font-size=\"16\" font-family=\"Arial, sans-serif\" font-weight=\"700\" fill=\"#374151\">QR code</text>
    <text x=\"456\" y=\"112\" font-size=\"13\" font-family=\"Arial, sans-serif\" fill=\"#6b7280\">Carrier scan reference</text>
    {qr_svg}
    <text x=\"568\" y=\"272\" text-anchor=\"middle\" font-size=\"16\" font-family=\"Courier New, monospace\" fill=\"#111827\">{escape(tracking_number)}</text>
  <rect x=\"48\" y=\"452\" width=\"648\" height=\"56\" rx=\"16\" fill=\"#eff6ff\"/>
    <text x=\"72\" y=\"486\" font-size=\"18\" font-family=\"Arial, sans-serif\" fill=\"#1d4ed8\">Keep this label attached to the parcel until delivery.</text>
</svg>
"""

    return GeneratedShippingLabel(
        filename=f"mock-label-{tracking_number.lower()}.svg",
        content=svg.encode("utf-8"),
        content_type="image/svg+xml",
    )


def _receiver_lines(receiver: dict[str, Any]) -> list[str]:
    name = " ".join(
        part for part in [receiver.get("first_name"), receiver.get("last_name")] if part
    ).strip()
    city_line = " ".join(
        part for part in [receiver.get("postal_code"), receiver.get("city")] if part
    ).strip()
    location_line = ", ".join(
        part for part in [city_line, receiver.get("country")] if part
    ).strip()
    contact_line = receiver.get("phone") or ""

    lines = [
        name or "Receiver",
        receiver.get("company") or "",
        receiver.get("address_line1") or "",
        receiver.get("address_line2") or "",
        location_line,
        contact_line,
    ]
    return [str(line) for line in lines if line]


def _qr_svg(value: str, *, start_x: int, start_y: int, cell_size: int) -> str:
    matrix = _qr_matrix(value, size=21)
    qr_size = (21 * cell_size) + 16
    parts = [
        f'<g aria-label="QR code"><rect x="{start_x}" y="{start_y}" width="{qr_size}" height="{qr_size}" rx="10" fill="#ffffff" stroke="#d1d5db" stroke-width="1.5"/>'
    ]

    for row_index, row in enumerate(matrix):
        for column_index, enabled in enumerate(row):
            if not enabled:
                continue
            x = start_x + 8 + (column_index * cell_size)
            y = start_y + 8 + (row_index * cell_size)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="#111827"/>'
            )

    parts.append("</g>")
    return "".join(parts)


def _qr_matrix(value: str, *, size: int) -> list[list[bool]]:
    matrix = [[False for _ in range(size)] for _ in range(size)]

    for top, left in ((0, 0), (0, size - 7), (size - 7, 0)):
        _apply_finder_pattern(matrix, top=top, left=left)

    bits = "".join(f"{ord(character):08b}" for character in value) or "0"
    bit_index = 0
    for row_index in range(size):
        for column_index in range(size):
            if matrix[row_index][column_index]:
                continue
            if _is_finder_zone(row_index, column_index, size=size):
                continue

            enabled = bits[bit_index % len(bits)] == "1"
            if (row_index + column_index) % 3 == 0:
                enabled = not enabled
            matrix[row_index][column_index] = enabled
            bit_index += 1

    return matrix


def _apply_finder_pattern(matrix: list[list[bool]], *, top: int, left: int) -> None:
    for row_offset in range(7):
        for column_offset in range(7):
            row_index = top + row_offset
            column_index = left + column_offset
            is_outer = row_offset in (0, 6) or column_offset in (0, 6)
            is_inner = row_offset in (2, 3, 4) and column_offset in (2, 3, 4)
            matrix[row_index][column_index] = is_outer or is_inner


def _is_finder_zone(row_index: int, column_index: int, *, size: int) -> bool:
    return (
        (row_index < 7 and column_index < 7)
        or (row_index < 7 and column_index >= size - 7)
        or (row_index >= size - 7 and column_index < 7)
    )