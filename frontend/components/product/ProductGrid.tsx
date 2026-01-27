"use client"

import * as React from "react"
import { ShoppingCart, ChevronLeft, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface Product {
  id: string
  name: string
  shortDescription?: string
  price: string
  currency?: string
  stockQuantity: number
  imageUrl?: string
}

interface ProductGridProps {
  products: Product[]
  page: number
  pageSize: number
  totalItems: number
  onPageChange: (nextPage: number) => void
  onAddToCart: (productId: string) => void
  onOpenProduct: (productId: string) => void
}

function ProductCard({
  product,
  onAddToCart,
  onOpenProduct,
}: {
  product: Product
  onAddToCart: (productId: string) => void
  onOpenProduct: (productId: string) => void
}) {
  const isInStock = product.stockQuantity > 0
  const currency = product.currency ?? "USD"

  const handleCardClick = () => {
    onOpenProduct(product.id)
  }

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation()
    onAddToCart(product.id)
  }

  const handleViewDetails = (e: React.MouseEvent) => {
    e.stopPropagation()
    onOpenProduct(product.id)
  }

  return (
    <Card
      className="group cursor-pointer overflow-hidden transition-shadow hover:shadow-md"
      onClick={handleCardClick}
    >
      {/* Image */}
      <div className="relative aspect-square w-full overflow-hidden">
        {product.imageUrl ? (
          <img
            src={product.imageUrl || "/placeholder.svg"}
            alt={product.name}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-linear-to-br from-muted to-muted-foreground/20">
            <span className="text-muted-foreground text-sm">No image</span>
          </div>
        )}
      </div>

      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="line-clamp-1 text-base">{product.name}</CardTitle>
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
        {product.shortDescription && (
          <CardDescription className="line-clamp-2">
            {product.shortDescription}
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="pb-2">
        <p className="text-foreground text-xl font-bold">
          {currency === "USD" ? "$" : currency}{" "}
          {product.price}
        </p>
      </CardContent>

      <CardFooter className="flex gap-2 pt-2">
        <Button
          onClick={handleAddToCart}
          disabled={!isInStock}
          className="flex-1"
          size="sm"
        >
          <ShoppingCart className="mr-1 h-4 w-4" />
          Add to cart
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleViewDetails}
        >
          View details
        </Button>
      </CardFooter>
    </Card>
  )
}

export function ProductGrid({
  products,
  page,
  pageSize,
  totalItems,
  onPageChange,
  onAddToCart,
  onOpenProduct,
}: ProductGridProps) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const canGoPrevious = page > 1
  const canGoNext = page < totalPages

  const handlePreviousPage = () => {
    if (canGoPrevious) {
      onPageChange(page - 1)
    }
  }

  const handleNextPage = () => {
    if (canGoNext) {
      onPageChange(page + 1)
    }
  }

  const handlePageSizeChange = (value: string) => {
    // Reset to page 1 when page size changes
    onPageChange(1)
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Product Grid */}
      {products.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              onAddToCart={onAddToCart}
              onOpenProduct={onOpenProduct}
            />
          ))}
        </div>
      ) : (
        <div className="flex min-h-50 items-center justify-center rounded-lg border border-dashed">
          <p className="text-muted-foreground">No products found</p>
        </div>
      )}

      {/* Pagination */}
      <Separator />
      <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
        {/* Page Size Selector */}
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-sm">Show</span>
          <Select defaultValue={String(pageSize)} onValueChange={handlePageSizeChange}>
            <SelectTrigger className="w-17.5" size="sm" aria-label="Select page size">
              <SelectValue placeholder={String(pageSize)} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="20">20</SelectItem>
              <SelectItem value="50">50</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-muted-foreground text-sm">per page</span>
        </div>

        {/* Page Navigation */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePreviousPage}
            disabled={!canGoPrevious}
            aria-label="Go to previous page"
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="sr-only sm:not-sr-only sm:ml-1">Previous</span>
          </Button>

          <span className="text-muted-foreground mx-2 text-sm">
            Page {page} of {totalPages}
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={handleNextPage}
            disabled={!canGoNext}
            aria-label="Go to next page"
          >
            <span className="sr-only sm:not-sr-only sm:mr-1">Next</span>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Total Items Info */}
        <div className="text-muted-foreground text-sm">
          {totalItems} {totalItems === 1 ? "item" : "items"} total
        </div>
      </div>
    </div>
  )
}
