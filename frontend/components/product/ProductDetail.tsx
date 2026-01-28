"use client"

import * as React from "react"
import { ShoppingCart, ArrowLeft } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"

interface ProductSpec {
  label: string
  value: string
}

interface Product {
  id: string
  name: string
  description?: string
  price: string
  currency?: string
  stockQuantity: number
  images?: string[]
  specs?: ProductSpec[]
}

interface ProductDetailProps {
  product: Product
  onAddToCart: (productId: string) => void
  onBack: () => void
}

function ImageGallery({ images, productName }: { images?: string[]; productName: string }) {
  const [activeIndex, setActiveIndex] = React.useState(0)

  const hasImages = images && images.length > 0
  const activeImage = hasImages ? images[activeIndex] : null

  return (
    <div className="flex flex-col gap-4">
      {/* Main Image */}
      <div className="relative aspect-square w-full overflow-hidden rounded-lg border bg-muted">
        {activeImage ? (
          <img
            src={activeImage || "/placeholder.svg"}
            alt={`${productName} - Image ${activeIndex + 1}`}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-linear-to-br from-muted to-muted-foreground/20">
            <span className="text-muted-foreground text-sm">No image available</span>
          </div>
        )}
      </div>

      {/* Thumbnail Strip */}
      {hasImages && images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {images.map((image, index) => (
            <button
              key={index}
              type="button"
              onClick={() => setActiveIndex(index)}
              className={cn(
                "relative h-16 w-16 shrink-0 overflow-hidden rounded-md border-2 transition-all",
                index === activeIndex
                  ? "border-primary ring-2 ring-primary/20"
                  : "border-transparent hover:border-muted-foreground/30"
              )}
              aria-label={`View image ${index + 1}`}
              aria-current={index === activeIndex ? "true" : undefined}
            >
              <img
                src={image || "/placeholder.svg"}
                alt={`${productName} thumbnail ${index + 1}`}
                className="h-full w-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SpecsList({ specs }: { specs: ProductSpec[] }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Specifications</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <dl className="grid gap-2">
          {specs.map((spec, index) => (
            <div
              key={index}
              className="flex justify-between gap-4 text-sm"
            >
              <dt className="text-muted-foreground">{spec.label}</dt>
              <dd className="text-foreground font-medium text-right">{spec.value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  )
}

export function ProductDetail({ product, onAddToCart, onBack }: ProductDetailProps) {
  const isInStock = product.stockQuantity > 0
  const currency = product.currency ?? "USD"
  const currencySymbol = currency === "USD" ? "$" : currency

  const handleAddToCart = () => {
    onAddToCart(product.id)
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Back Button */}
      <div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="gap-1"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
      </div>

      {/* Main Content: Two-column on desktop, stacked on mobile */}
      <div className="grid gap-8 md:grid-cols-2">
        {/* Left: Image Gallery */}
        <ImageGallery images={product.images} productName={product.name} />

        {/* Right: Product Info */}
        <div className="flex flex-col gap-6">
          {/* Name and Stock Badge */}
          <div className="flex flex-col gap-2">
            <div className="flex items-start justify-between gap-4">
              <h1 className="text-foreground text-2xl font-bold tracking-tight">
                {product.name}
              </h1>
              <Badge
                variant={isInStock ? "secondary" : "destructive"}
                className={cn(
                  "shrink-0",
                  isInStock && "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                )}
              >
                {isInStock ? "In stock" : "Out of stock"}
              </Badge>
            </div>

            {/* Price */}
            <p className="text-foreground text-3xl font-bold">
              {currencySymbol}{product.price}
            </p>
          </div>

          <Separator />

          {/* Description */}
          {product.description && (
            <div className="flex flex-col gap-2">
              <h2 className="text-foreground text-sm font-semibold uppercase tracking-wide">
                Description
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                {product.description}
              </p>
            </div>
          )}

          {/* Specs */}
          {product.specs && product.specs.length > 0 && (
            <SpecsList specs={product.specs} />
          )}

          {/* Actions */}
          <div className="mt-auto flex flex-col gap-3 pt-4 sm:flex-row">
            <Button
              onClick={handleAddToCart}
              disabled={!isInStock}
              className="flex-1"
              size="lg"
            >
              <ShoppingCart className="mr-2 h-5 w-5" />
              Add to cart
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={onBack}
              className="sm:w-auto bg-transparent"
            >
              Back
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
