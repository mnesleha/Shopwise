import type { CartDto } from "@/lib/api/cart";

export type CartVm = {
  id: string;
  currency?: string;
  items: Array<{
    productId: string;
    productName: string;
    productUrl?: string;
    shortDescription?: string;
    unitPrice: string;
    quantity: number;
    stockQuantity?: number;
    imageUrl?: string;
  }>;
  discount?: {
    code?: string;
    description?: string;
    amount?: string;
  };
  subtotal: string;
  tax?: string;
  total: string;
};

function addDecimalStrings(a: string, b: string): string {
  // simple decimal sum using JS number; OK for demo UI
  // (later can be moved to backend / decimal library)
  const sum = (Number(a) || 0) + (Number(b) || 0);
  return sum.toFixed(2);
}

function mulDecimalString(a: string, qty: number): string {
  const v = (Number(a) || 0) * qty;
  return v.toFixed(2);
}

export function mapCartToVm(dto: CartDto): CartVm {
  const items = dto.items.map((it) => ({
    productId: String(it.product.id), // product id!
    productName: it.product.name,
    productUrl: `/products/${it.product.id}`,
    shortDescription: "",
    unitPrice: it.price_at_add_time || it.product.price,
    quantity: it.quantity,
    imageUrl: "",
  }));

  // subtotal = sum(unitPrice * qty)
  const subtotal = items.reduce((acc, it) => addDecimalStrings(acc, mulDecimalString(it.unitPrice, it.quantity)), "0.00");

  // Discount: backend currently NOT in cart response (known gap)
  // Keep undefined so UI hides it.
  const discount = undefined;

  // Tax: not modeled yet
  const tax = undefined;

  // total = subtotal - discount + tax (for now just subtotal)
  const total = subtotal;

  return {
    id: String(dto.id),
    currency: "USD",
    items,
    discount,
    subtotal,
    tax,
    total,
  };
}
