"use client";

import * as React from "react";
import { ArrowLeft, Printer, Download } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// Types
type SupplierInfo = {
  name: string;
  addressLine1: string;
  addressLine2?: string;
  city: string;
  postalCode: string;
  country: string;
  companyId?: string; // ICO
  vatId?: string; // DIC
  phone?: string;
  email?: string;
  bankAccount?: {
    bankName?: string;
    accountNumber?: string;
    iban?: string;
    swift?: string;
  };
};

type CustomerInfo = {
  name: string;
  addressLine1: string;
  addressLine2?: string;
  city: string;
  postalCode: string;
  country: string;
  phone?: string;
  email?: string;
};

type MoneyLine = {
  label: string;
  amount: string; // formatted decimal string
};

type OrderItem = {
  id: string;
  productId: string;
  productName: string;
  productUrl?: string;
  quantity: number;
  unitPrice: string;
  lineTotal: string;
  discount?: {
    type: "FIXED" | "PERCENT";
    value: string;
  } | null;
};

type OrderViewModel = {
  id: string;
  orderNumber: string; // e.g. "OBJ25284904"
  status: "CREATED" | "PAID" | "SHIPPED" | "DELIVERED" | "CANCELLED" | string;
  createdAt?: string; // display string
  supplier: SupplierInfo;
  customer: CustomerInfo;

  // Shipping & payment placeholders (may be mocked today)
  shippingMethod?: string; // e.g. "PPL"
  paymentMethod?: string; // e.g. "Bank transfer (simulated)"
  barcodeValue?: string; // optional text rendered as a pseudo-barcode block

  items: OrderItem[];

  // Totals block
  subtotal?: string;
  discountTotal?: string;
  shippingFee?: string;
  taxTotal?: string; // optional, show "Tax included" note if not provided
  total: string;

  // Optional: breakdown rows shown in summary card
  totalsBreakdown?: MoneyLine[];
};

interface OrderDetailProps {
  order: OrderViewModel;
  onBackToShop: () => void;
  headerActions?: React.ReactNode;
  onPrint?: () => void;
  onDownloadPdf?: () => void;
}

// Status badge styling
function getStatusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  const s = status.toUpperCase();
  if (s === "PAID" || s === "DELIVERED") return "default";
  if (s === "SHIPPED") return "secondary";
  if (s === "CANCELLED") return "destructive";
  return "outline";
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    CREATED: "Created",
    PAID: "Paid",
    SHIPPED: "Shipped",
    DELIVERED: "Delivered",
    CANCELLED: "Cancelled",
  };
  return labels[status.toUpperCase()] || status;
}

// Pseudo-barcode visual (styled monospace block)
function PseudoBarcode({ value }: { value: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex gap-px">
        {/* Generate visual bars based on character codes */}
        {value.split("").map((char, i) => {
          const code = char.charCodeAt(0);
          const width = (code % 3) + 1;
          const height = 32 + (code % 8);
          return (
            <div
              key={i}
              className="bg-foreground"
              style={{ width: `${width}px`, height: `${height}px` }}
            />
          );
        })}
      </div>
      <span className="font-mono text-xs text-muted-foreground">{value}</span>
    </div>
  );
}

// Address display component
function AddressBlock({
  title,
  info,
  showBankAccount = false,
}: {
  title: string;
  info: SupplierInfo | CustomerInfo;
  showBankAccount?: boolean;
}) {
  const isSupplier =
    "companyId" in info || "vatId" in info || "bankAccount" in info;
  const supplierInfo = info as SupplierInfo;

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2 text-sm">
        <p className="font-semibold text-foreground">{info.name}</p>
        <div className="text-muted-foreground">
          <p>{info.addressLine1}</p>
          {info.addressLine2 && <p>{info.addressLine2}</p>}
          <p>
            {info.city}, {info.postalCode}
          </p>
          <p>{info.country}</p>
        </div>

        {(info.phone || info.email) && (
          <div className="mt-2 text-muted-foreground">
            {info.phone && <p>Tel: {info.phone}</p>}
            {info.email && <p>Email: {info.email}</p>}
          </div>
        )}

        {isSupplier && (supplierInfo.companyId || supplierInfo.vatId) && (
          <div className="mt-2 text-muted-foreground">
            {supplierInfo.companyId && (
              <p>Company ID: {supplierInfo.companyId}</p>
            )}
            {supplierInfo.vatId && <p>VAT ID: {supplierInfo.vatId}</p>}
          </div>
        )}

        {showBankAccount && isSupplier && supplierInfo.bankAccount && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="font-medium text-foreground mb-1">Bank Details</p>
            <div className="text-muted-foreground">
              {supplierInfo.bankAccount.bankName && (
                <p>Bank: {supplierInfo.bankAccount.bankName}</p>
              )}
              {supplierInfo.bankAccount.accountNumber && (
                <p>Account: {supplierInfo.bankAccount.accountNumber}</p>
              )}
              {supplierInfo.bankAccount.iban && (
                <p>IBAN: {supplierInfo.bankAccount.iban}</p>
              )}
              {supplierInfo.bankAccount.swift && (
                <p>SWIFT: {supplierInfo.bankAccount.swift}</p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Order items table
function ItemsTable({ items }: { items: OrderItem[] }) {
  const formatDiscount = (discount: OrderItem["discount"]) => {
    if (!discount) return "—";
    if (discount.type === "FIXED") return `- $${discount.value}`;
    return `- ${discount.value}%`;
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Order Items
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                  Qty
                </th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                  Product
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  Unit Price
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  Discount
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  Line Total
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-border last:border-0"
                >
                  <td className="px-4 py-3 text-foreground">{item.quantity}</td>
                  <td className="px-4 py-3">
                    {item.productUrl ? (
                      <a
                        href={item.productUrl}
                        className="text-primary hover:underline font-medium"
                      >
                        {item.productName}
                      </a>
                    ) : (
                      <span className="text-foreground font-medium">
                        {item.productName}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    ${item.unitPrice}
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    {formatDiscount(item.discount)}
                  </td>
                  <td className="px-4 py-3 text-right text-foreground font-medium">
                    ${item.lineTotal}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// Totals summary
function TotalsSummary({ order }: { order: OrderViewModel }) {
  // Use totalsBreakdown if provided, otherwise derive from available fields
  const breakdownRows: MoneyLine[] = order.totalsBreakdown ?? [
    ...(order.subtotal ? [{ label: "Subtotal", amount: order.subtotal }] : []),
    ...(order.shippingFee
      ? [{ label: "Shipping", amount: order.shippingFee }]
      : []),
    ...(order.discountTotal
      ? [{ label: "Discount", amount: `-${order.discountTotal}` }]
      : []),
    ...(order.taxTotal ? [{ label: "Tax", amount: order.taxTotal }] : []),
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Order Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {breakdownRows.map((row, index) => (
          <div key={index} className="flex justify-between text-sm">
            <span className="text-muted-foreground">{row.label}</span>
            <span className="text-foreground">
              {row.amount.startsWith("-") ? row.amount : `$${row.amount}`}
            </span>
          </div>
        ))}

        {!order.taxTotal && (
          <p className="text-xs text-muted-foreground italic">
            Tax included in price
          </p>
        )}

        <Separator className="my-2" />

        <div className="flex justify-between">
          <span className="text-foreground font-semibold">Total</span>
          <span className="text-lg font-bold text-foreground">
            ${order.total}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

export function OrderDetail({
  order,
  onBackToShop,
  headerActions,
  onPrint,
  onDownloadPdf,
}: OrderDetailProps) {
  const barcodeValue = order.barcodeValue || order.orderNumber;

  return (
    <div className="mx-auto max-w-4xl print:max-w-none">
      {/* Action buttons (hidden on print) */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Button
          variant="outline"
          onClick={onBackToShop}
          className="gap-2 bg-transparent"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to shop
        </Button>
        <div className="flex gap-2">
          {headerActions}
          {onPrint && (
            <Button
              variant="outline"
              onClick={onPrint}
              className="gap-2 bg-transparent"
            >
              <Printer className="h-4 w-4" />
              Print
            </Button>
          )}
          {onDownloadPdf && (
            <Button
              variant="outline"
              onClick={onDownloadPdf}
              className="gap-2 bg-transparent"
            >
              <Download className="h-4 w-4" />
              Download PDF
            </Button>
          )}
        </div>
      </div>

      {/* Invoice container */}
      <div className="rounded-lg border border-border bg-background p-6 shadow-sm print:border-0 print:shadow-none print:p-0">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-1">
            {/* Logo placeholder */}
            <span className="text-2xl font-bold text-foreground">Shopwise</span>
            <h1
              data-testid="order-title"
              className="text-lg text-muted-foreground"
            >
              Order:{" "}
              <span className="font-semibold text-foreground">
                {order.orderNumber}
              </span>
            </h1>
          </div>
          <div className="shrink-0">
            <PseudoBarcode value={barcodeValue} />
          </div>
        </div>

        <Separator className="my-6" />

        {/* Two columns: Supplier & Customer */}
        <div className="grid gap-6 md:grid-cols-2">
          <AddressBlock
            title="Supplier"
            info={order.supplier}
            showBankAccount
          />
          <AddressBlock title="Customer" info={order.customer} />
        </div>

        <Separator className="my-6" />

        {/* Order meta row */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm">
          {order.createdAt && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Date:</span>
              <span className="text-foreground font-medium">
                {order.createdAt}
              </span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Status:</span>
            <Badge
              data-testid="order-status"
              variant={getStatusBadgeVariant(order.status)}
            >
              {getStatusLabel(order.status)}
            </Badge>
          </div>
          {order.shippingMethod && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Shipping:</span>
              <span className="text-foreground font-medium">
                {order.shippingMethod}
              </span>
            </div>
          )}
          {order.paymentMethod && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Payment:</span>
              <span className="text-foreground font-medium">
                {order.paymentMethod}
              </span>
            </div>
          )}
        </div>

        <Separator className="my-6" />

        {/* Items table */}
        <ItemsTable items={order.items} />

        {/* Totals summary */}
        <div className="mt-6 flex justify-end">
          <div className="w-full max-w-sm">
            <TotalsSummary order={order} />
          </div>
        </div>

        <Separator className="my-6" />

        {/* Footer notes */}
        <div className="flex flex-col gap-2 text-center text-sm text-muted-foreground">
          <p>This is a demo invoice. Payment and shipping are simulated.</p>
          <p>
            Need help? Contact us at{" "}
            <a
              href="mailto:support@shopwise.demo"
              className="text-primary hover:underline"
            >
              support@shopwise.demo
            </a>
          </p>
        </div>
      </div>

      {/* Bottom actions (hidden on print) */}
      <div className="mt-6 flex justify-center print:hidden">
        <Button
          variant="outline"
          onClick={onBackToShop}
          className="gap-2 bg-transparent"
        >
          <ArrowLeft className="h-4 w-4" />
          Continue shopping
        </Button>
      </div>
    </div>
  );
}

export type {
  OrderViewModel,
  SupplierInfo,
  CustomerInfo,
  OrderItem,
  MoneyLine,
};
