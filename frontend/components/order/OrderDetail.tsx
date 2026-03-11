"use client";

import * as React from "react";
import { ArrowLeft, Printer, Download } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

type VatBreakdownLine = {
  /** Tax rate percentage, e.g. "10.00" */
  taxRate: string;
  /** Sum of net line totals for this rate */
  taxBase: string;
  /** Sum of VAT amounts for this rate */
  vatAmount: string;
  /** Sum of gross line totals for this rate */
  totalInclVat: string;
};

type OrderItem = {
  id: string;
  productId: string;
  productName: string;
  productUrl?: string;
  quantity: number;
  /** Gross unit price — backward-compat legacy field */
  unitPrice: string;
  /** Net unit price excl. VAT — null for pre-snapshot / unmigrated products */
  unitPriceNet?: string | null;
  /** Gross unit price incl. VAT */
  unitPriceGross?: string | null;
  /** Per-unit VAT amount */
  taxAmount?: string | null;
  /** Effective tax rate percentage, e.g. "10.00" */
  taxRate?: string | null;
  /** Gross line total — backward-compat legacy field */
  lineTotal: string;
  /** Net line total */
  lineTotalNet?: string | null;
  /** Gross line total (preferred for invoice display) */
  lineTotalGross?: string | null;
  /** Neutral inline note for line-level discount, e.g. "Includes line discount 10%" */
  discountNote?: string | null;
  /** Raw discount — kept for legacy callers */
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
  barcodeValue?: string;

  items: OrderItem[];

  // Phase 3 order-level totals snapshot
  subtotalNet?: string | null;
  subtotalGross?: string | null;
  totalTax?: string | null;
  totalDiscount?: string | null;
  currency?: string;
  vatBreakdown?: VatBreakdownLine[] | null;

  /** Gross total — backward-compat field */
  total: string;
  /** @deprecated Use subtotalNet / subtotalGross / totalTax instead */
  subtotal?: string;
  /** @deprecated Use vatBreakdown instead */
  totalsBreakdown?: MoneyLine[];
};

interface OrderDetailProps {
  order: OrderViewModel;
  onBackToShop: () => void;
  headerActions?: React.ReactNode;
  onPrint?: () => void;
  onDownloadPdf?: () => void;
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Pseudo-barcode visual (styled monospace block)
// ---------------------------------------------------------------------------

function PseudoBarcode({ value }: { value: string }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="flex gap-px">
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

// ---------------------------------------------------------------------------
// Address display component
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Currency formatting
// ---------------------------------------------------------------------------

/**
 * Resolve an ISO 4217 currency code to a display symbol.
 * Unknown codes render as "CODE\u00a0" (ISO code + NBSP) so output stays legible.
 */
function currencySymbol(code: string): string {
  const symbols: Record<string, string> = {
    EUR: "\u20ac",
    USD: "$",
    GBP: "\u00a3",
    CZK: "K\u010d\u00a0",
  };
  return symbols[code] ?? `${code}\u00a0`;
}

/**
 * Format an amount string with its currency symbol prefix.
 * Returns "\u2014" when amount is null/undefined (missing historical snapshot data).
 */
function formatMoney(
  amount: string | null | undefined,
  currencyCode: string,
): string {
  if (amount == null) return "\u2014";
  return `${currencySymbol(currencyCode)}${amount}`;
}

// ---------------------------------------------------------------------------
// Invoice items table
// Columns: Qty | Product | Unit excl. VAT | VAT rate | VAT | Total incl. VAT
// ---------------------------------------------------------------------------

function ItemsTable({
  items,
  currency,
}: {
  items: OrderItem[];
  currency: string;
}) {
  return (
    <Card data-testid="order-items-table">
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
                  Unit excl. VAT
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  VAT rate
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  VAT
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  Total incl. VAT
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const displayUnitNet = item.unitPriceNet ?? item.unitPrice;
                const displayLineGross = item.lineTotalGross ?? item.lineTotal;
                return (
                  <tr
                    key={item.id}
                    className="border-b border-border last:border-0"
                  >
                    <td className="px-4 py-3 text-foreground">
                      {item.quantity}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        {item.productUrl ? (
                          <a
                            href={item.productUrl}
                            className="text-foreground font-medium hover:underline"
                          >
                            {item.productName}
                          </a>
                        ) : (
                          <span className="text-foreground font-medium">
                            {item.productName}
                          </span>
                        )}
                        {item.discountNote && (
                          <p
                            className="text-xs text-muted-foreground mt-0.5"
                            data-testid="item-discount-note"
                          >
                            {item.discountNote}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-muted-foreground">
                      {formatMoney(displayUnitNet, currency)}
                    </td>
                    <td className="px-4 py-3 text-right text-muted-foreground">
                      {item.taxRate != null ? `${item.taxRate}%` : "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-right text-muted-foreground">
                      {formatMoney(item.taxAmount, currency)}
                    </td>
                    <td className="px-4 py-3 text-right text-foreground font-medium">
                      {formatMoney(displayLineGross, currency)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// VAT breakdown section
// Rows: tax rate | tax base | VAT amount | total incl. VAT
// ---------------------------------------------------------------------------

function VatBreakdownTable({
  rows,
  currency,
}: {
  rows: VatBreakdownLine[];
  currency: string;
}) {
  const totals = rows.reduce(
    (acc, row) => ({
      taxBase: (parseFloat(acc.taxBase) + parseFloat(row.taxBase)).toFixed(2),
      vatAmount: (
        parseFloat(acc.vatAmount) + parseFloat(row.vatAmount)
      ).toFixed(2),
      totalInclVat: (
        parseFloat(acc.totalInclVat) + parseFloat(row.totalInclVat)
      ).toFixed(2),
    }),
    { taxBase: "0.00", vatAmount: "0.00", totalInclVat: "0.00" },
  );

  return (
    <Card data-testid="vat-breakdown">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          VAT Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                  VAT rate
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  Tax base
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  VAT amount
                </th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                  Total incl. VAT
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.taxRate}
                  className="border-b border-border last:border-0"
                  data-testid={`vat-row-${row.taxRate}`}
                >
                  <td className="px-4 py-3 text-foreground">{row.taxRate}%</td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    {formatMoney(row.taxBase, currency)}
                  </td>
                  <td className="px-4 py-3 text-right text-muted-foreground">
                    {formatMoney(row.vatAmount, currency)}
                  </td>
                  <td className="px-4 py-3 text-right text-foreground font-medium">
                    {formatMoney(row.totalInclVat, currency)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-border bg-muted/50">
                <td className="px-4 py-3 font-semibold text-foreground">
                  Total
                </td>
                <td className="px-4 py-3 text-right font-semibold text-foreground">
                  {formatMoney(totals.taxBase, currency)}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-foreground">
                  {formatMoney(totals.vatAmount, currency)}
                </td>
                <td className="px-4 py-3 text-right font-bold text-foreground">
                  {formatMoney(totals.totalInclVat, currency)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Order summary
// Shows: Subtotal excl. VAT | VAT | Total incl. VAT
// No line-level discount row: discounts are already reflected in item prices.
// ---------------------------------------------------------------------------

function OrderSummary({ order }: { order: OrderViewModel }) {
  const currency = order.currency ?? "EUR";
  const subtotalNet = order.subtotalNet ?? null;
  const totalTax = order.totalTax ?? null;
  const total = order.subtotalGross ?? order.total;

  return (
    <Card data-testid="order-summary">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Order Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {subtotalNet !== null && (
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Subtotal excl. VAT</span>
            <span className="text-foreground">
              {formatMoney(subtotalNet, currency)}
            </span>
          </div>
        )}

        {totalTax !== null && (
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">VAT</span>
            <span className="text-foreground">
              {formatMoney(totalTax, currency)}
            </span>
          </div>
        )}

        {subtotalNet === null && totalTax === null && (
          <p className="text-xs text-muted-foreground italic">
            VAT included in price
          </p>
        )}

        <Separator className="my-2" />

        <div className="flex justify-between">
          <span className="text-foreground font-semibold">Total incl. VAT</span>
          <span className="text-lg font-bold text-foreground">
            {formatMoney(total, currency)}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main OrderDetail component
// ---------------------------------------------------------------------------

export function OrderDetail({
  order,
  onBackToShop,
  headerActions,
  onPrint,
  onDownloadPdf,
}: OrderDetailProps) {
  const barcodeValue = order.barcodeValue || order.orderNumber;
  const hasVatBreakdown =
    order.vatBreakdown !== null &&
    order.vatBreakdown !== undefined &&
    order.vatBreakdown.length > 0;

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
        <ItemsTable items={order.items} currency={order.currency ?? "EUR"} />

        {/* VAT breakdown (only when backend provides it) */}
        {hasVatBreakdown && (
          <div className="mt-6">
            <VatBreakdownTable
              rows={order.vatBreakdown!}
              currency={order.currency ?? "EUR"}
            />
          </div>
        )}

        {/* Order summary */}
        <div className="mt-6 flex justify-end">
          <div className="w-full max-w-sm">
            <OrderSummary order={order} />
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
  VatBreakdownLine,
};
