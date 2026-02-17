import type { OrderDto } from "@/lib/api/orders";
import type { OrderViewModel, OrderItem } from "@/components/order/OrderDetail";

const DEFAULT_SUPPLIER = {
  name: "Shopwise Demo Supplier Ltd.",
  addressLine1: "Demo Street 1",
  city: "Prague",
  postalCode: "110 00",
  country: "Czech Republic",
  companyId: "CZ12345678",
  vatId: "CZ12345678",
  email: "supplier@shopwise.demo",
  phone: "+420 000 000 000",
  bankAccount: {
    bankName: "Demo Bank",
    accountNumber: "000000-0000000000/0000",
    iban: "CZ0000000000000000000000",
    swift: "DEMOXXXX",
  },
};

const DEFAULT_CUSTOMER = {
  name: "Customer (missing in API)",
  addressLine1: "—",
  city: "—",
  postalCode: "—",
  country: "—",
  email: "—",
  phone: "—",
};

function formatOrderNumber(orderId: number): string {
  // simple demo formatting; replace once backend provides real order number
  const year = new Date().getFullYear();
  return `OBJ${year}${String(orderId).padStart(6, "0")}`;
}

function mapItem(dto: OrderDto["items"][number]): OrderItem {
  return {
    id: String(dto.id),
    productId: String(dto.product),
    productName: `Product #${dto.product}`, // TODO: enrich from product cache / include product name in API
    productUrl: `/products/${dto.product}`,
    quantity: dto.quantity,
    unitPrice: dto.unit_price,
    lineTotal: dto.line_total,
    discount: dto.discount,
  };
}

export function mapOrderToVm(dto: OrderDto): OrderViewModel {
  const orderNumber = formatOrderNumber(dto.id);

  return {
    id: String(dto.id),
    orderNumber,
    status: dto.status,
    createdAt: new Date().toLocaleDateString(), // TODO: backend created_at

    supplier: DEFAULT_SUPPLIER,
    customer: DEFAULT_CUSTOMER,

    shippingMethod: "Standard (simulated)",
    paymentMethod: "Card (simulated)",
    barcodeValue: orderNumber,

    items: dto.items.map(mapItem),

    total: dto.total,
    // Optional future fields:
    subtotal: dto.total,
    totalsBreakdown: [
      { label: "Subtotal", amount: dto.total },
      // discount/shipping/tax later once backend provides it
    ],
  };
}
