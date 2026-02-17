"use client"

import * as React from "react"
import { ShoppingCart, Trash2, Plus, Minus, ArrowRight, ArrowLeft, ShoppingBag } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"

interface CartItem {
  productId: string
  productName: string
  productUrl?: string
  shortDescription?: string
  unitPrice: string
  quantity: number
  stockQuantity?: number
  imageUrl?: string
}

interface CartDiscount {
  code?: string
  description?: string
  amount?: string
}

interface Cart {
  id: string
  currency?: string
  items: CartItem[]
  discount?: CartDiscount
  subtotal: string
  tax?: string
  total: string
}

interface CartDetailProps {
  cart: Cart
  onContinueShopping: () => void
  onRemoveItem: (productId: string) => void
  onDecreaseQty: (productId: string) => void
  onIncreaseQty: (productId: string) => void
  onClearCart: () => void
  onCheckout: () => void
  onApplyDiscountCode?: (code: string) => void
}

function CartItemRow({
  item,
  currency,
  currencySymbol,
  onRemoveItem,
  onDecreaseQty,
  onIncreaseQty,
}: {
  item: CartItem
  currency: string
  currencySymbol: string
  onRemoveItem: (productId: string) => void
  onDecreaseQty: (productId: string) => void
  onIncreaseQty: (productId: string) => void
}) {
  const canDecrease = item.quantity > 1
  const canIncrease = item.stockQuantity === undefined || item.quantity < item.stockQuantity

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex gap-4">
          {/* Image */}
          <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-md bg-muted">
            {item.imageUrl ? (
              <img
                src={item.imageUrl || "/placeholder.svg"}
                alt={item.productName}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-linear-to-br from-muted to-muted-foreground/20">
                <ShoppingBag className="h-6 w-6 text-muted-foreground" />
              </div>
            )}
          </div>

          {/* Details */}
          <div className="flex flex-1 flex-col gap-1">
            <div className="flex items-start justify-between gap-2">
              {item.productUrl ? (
                <a
                  href={item.productUrl}
                  className="text-foreground font-medium hover:underline line-clamp-1"
                >
                  {item.productName}
                </a>
              ) : (
                <span className="text-foreground font-medium line-clamp-1">
                  {item.productName}
                </span>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
                onClick={() => onRemoveItem(item.productId)}
                aria-label={`Remove ${item.productName} from cart`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>

            {item.shortDescription && (
              <p className="text-muted-foreground text-sm line-clamp-1">
                {item.shortDescription}
              </p>
            )}

            <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
              {/* Price */}
              <p className="text-foreground font-semibold">
                {currencySymbol}{item.unitPrice}
              </p>

              {/* Quantity Controls */}
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8 bg-transparent"
                  onClick={() => onDecreaseQty(item.productId)}
                  disabled={!canDecrease}
                  aria-label={`Decrease quantity of ${item.productName}`}
                >
                  <Minus className="h-3 w-3" />
                </Button>
                <span
                  className="w-10 text-center text-sm font-medium"
                  aria-label={`Quantity: ${item.quantity}`}
                >
                  {item.quantity}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8 bg-transparent"
                  onClick={() => onIncreaseQty(item.productId)}
                  disabled={!canIncrease}
                  aria-label={`Increase quantity of ${item.productName}`}
                >
                  <Plus className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function OrderSummary({
  cart,
  currencySymbol,
  onCheckout,
  onApplyDiscountCode,
}: {
  cart: Cart
  currencySymbol: string
  onCheckout: () => void
  onApplyDiscountCode?: (code: string) => void
}) {
  const [discountCode, setDiscountCode] = React.useState("")

  const handleApplyDiscount = () => {
    if (discountCode.trim() && onApplyDiscountCode) {
      onApplyDiscountCode(discountCode.trim())
      setDiscountCode("")
    }
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-lg">Order Summary</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {/* Subtotal */}
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Subtotal</span>
          <span className="text-foreground">{currencySymbol}{cart.subtotal}</span>
        </div>

        {/* Discount */}
        {cart.discount && cart.discount.amount && (
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">
              Discount
              {cart.discount.code && (
                <span className="ml-1 text-xs">({cart.discount.code})</span>
              )}
            </span>
            <span className="text-emerald-600 dark:text-emerald-400">
              -{currencySymbol}{cart.discount.amount}
            </span>
          </div>
        )}

        {/* Tax */}
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Tax</span>
          <span className="text-foreground">
            {cart.tax ? `${currencySymbol}${cart.tax}` : "Calculated at checkout"}
          </span>
        </div>

        <Separator className="my-1" />

        {/* Total */}
        <div className="flex justify-between">
          <span className="text-foreground font-semibold">Total</span>
          <span className="text-foreground text-lg font-bold">
            {currencySymbol}{cart.total}
          </span>
        </div>

        {/* Discount Code Input */}
        {onApplyDiscountCode && (
          <>
            <Separator className="my-1" />
            <div className="flex flex-col gap-2">
              <label htmlFor="discount-code" className="text-sm text-muted-foreground">
                Discount code
              </label>
              <div className="flex gap-2">
                <Input
                  id="discount-code"
                  type="text"
                  placeholder="Enter code"
                  value={discountCode}
                  onChange={(e) => setDiscountCode(e.target.value)}
                  className="flex-1"
                />
                <Button
                  variant="outline"
                  onClick={handleApplyDiscount}
                  disabled={!discountCode.trim()}
                >
                  Apply
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
      <CardFooter className="flex flex-col gap-3 pt-2">
        <Button
          className="w-full"
          size="lg"
          onClick={onCheckout}
        >
          Proceed to checkout
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
        <p className="text-muted-foreground text-center text-xs">
          Shipping and payment are simulated in this demo.
        </p>
      </CardFooter>
    </Card>
  )
}

function EmptyCart({ onContinueShopping }: { onContinueShopping: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-16">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
        <ShoppingCart className="h-10 w-10 text-muted-foreground" />
      </div>
      <div className="flex flex-col items-center gap-2 text-center">
        <h2 className="text-foreground text-xl font-semibold">Your cart is empty</h2>
        <p className="text-muted-foreground max-w-sm">
          Looks like you haven't added any items to your cart yet. Start shopping to find something you'll love!
        </p>
      </div>
      <Button onClick={onContinueShopping} size="lg">
        <ShoppingBag className="mr-2 h-5 w-5" />
        Browse products
      </Button>
    </div>
  )
}

export function CartDetail({
  cart,
  onContinueShopping,
  onRemoveItem,
  onDecreaseQty,
  onIncreaseQty,
  onClearCart,
  onCheckout,
  onApplyDiscountCode,
}: CartDetailProps) {
  const [showClearConfirm, setShowClearConfirm] = React.useState(false)

  const currency = cart.currency ?? "USD"
  const currencySymbol = currency === "USD" ? "$" : currency
  const isEmpty = cart.items.length === 0

  const handleClearCart = () => {
    if (showClearConfirm) {
      onClearCart()
      setShowClearConfirm(false)
    } else {
      setShowClearConfirm(true)
    }
  }

  const handleCancelClear = () => {
    setShowClearConfirm(false)
  }

  // Empty state
  if (isEmpty) {
    return (
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-foreground text-2xl font-bold tracking-tight">Your Cart</h1>
          <Button
            variant="ghost"
            onClick={onContinueShopping}
            className="gap-1"
          >
            <ArrowLeft className="h-4 w-4" />
            Continue shopping
          </Button>
        </div>
        <EmptyCart onContinueShopping={onContinueShopping} />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-foreground text-2xl font-bold tracking-tight">
          Your Cart ({cart.items.length} {cart.items.length === 1 ? "item" : "items"})
        </h1>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            onClick={onContinueShopping}
            className="gap-1"
          >
            <ArrowLeft className="h-4 w-4" />
            Continue shopping
          </Button>
          {showClearConfirm ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Clear all?</span>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleClearCart}
              >
                Confirm
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancelClear}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              onClick={handleClearCart}
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="mr-1 h-4 w-4" />
              Clear cart
            </Button>
          )}
        </div>
      </div>

      {/* Main Layout: 2 columns on desktop, stacked on mobile */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Items List */}
        <div className="flex flex-col gap-4 lg:col-span-2">
          {cart.items.map((item) => (
            <CartItemRow
              key={item.productId}
              item={item}
              currency={currency}
              currencySymbol={currencySymbol}
              onRemoveItem={onRemoveItem}
              onDecreaseQty={onDecreaseQty}
              onIncreaseQty={onIncreaseQty}
            />
          ))}
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="sticky top-4">
            <OrderSummary
              cart={cart}
              currencySymbol={currencySymbol}
              onCheckout={onCheckout}
              onApplyDiscountCode={onApplyDiscountCode}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
