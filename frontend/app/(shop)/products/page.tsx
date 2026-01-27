"use client"

import { useState } from "react"
import { ProductGrid } from "@/components/product/ProductGrid"

const sampleProducts = [
  {
    id: "1",
    name: "Wireless Bluetooth Headphones",
    shortDescription: "Premium noise-cancelling headphones with 30-hour battery life and crystal clear audio.",
    price: "149.99",
    currency: "USD",
    stockQuantity: 25,
    imageUrl: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop",
  },
  {
    id: "2",
    name: "Minimalist Watch",
    shortDescription: "Elegant timepiece with leather strap and sapphire crystal face.",
    price: "299.00",
    currency: "USD",
    stockQuantity: 12,
    imageUrl: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop",
  },
  {
    id: "3",
    name: "Organic Cotton T-Shirt",
    shortDescription: "Soft, breathable fabric made from 100% organic cotton.",
    price: "34.99",
    currency: "USD",
    stockQuantity: 0,
    imageUrl: "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop",
  },
  {
    id: "4",
    name: "Smart Home Speaker",
    shortDescription: "Voice-controlled speaker with premium sound quality.",
    price: "89.99",
    currency: "USD",
    stockQuantity: 50,
    imageUrl: "https://images.unsplash.com/photo-1543512214-318c7553f230?w=400&h=400&fit=crop",
  },
  {
    id: "5",
    name: "Leather Backpack",
    shortDescription: "Handcrafted genuine leather backpack with laptop compartment.",
    price: "189.00",
    currency: "USD",
    stockQuantity: 8,
  },
  {
    id: "6",
    name: "Ceramic Coffee Mug Set",
    shortDescription: "Set of 4 artisan mugs in earth tones.",
    price: "45.00",
    currency: "USD",
    stockQuantity: 0,
    imageUrl: "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=400&h=400&fit=crop",
  },
  {
    id: "7",
    name: "Yoga Mat Pro",
    shortDescription: "Extra thick, non-slip yoga mat with alignment guides.",
    price: "68.00",
    currency: "USD",
    stockQuantity: 35,
    imageUrl: "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=400&h=400&fit=crop",
  },
  {
    id: "8",
    name: "Stainless Steel Water Bottle",
    shortDescription: "Double-walled insulated bottle keeps drinks cold for 24 hours.",
    price: "29.99",
    currency: "USD",
    stockQuantity: 100,
    imageUrl: "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400&h=400&fit=crop",
  },
]

export default function ProductsPage() {
  const [page, setPage] = useState(1)
  const pageSize = 10
  const totalItems = sampleProducts.length

  const handlePageChange = (nextPage: number) => {
    setPage(nextPage)
    console.log("Page changed to:", nextPage)
  }

  const handleAddToCart = (productId: string) => {
    console.log("Add to cart:", productId)
    alert(`Added product ${productId} to cart!`)
  }

  const handleOpenProduct = (productId: string) => {
    console.log("Open product:", productId)
    alert(`Opening product details for: ${productId}`)
  }

  return (
    <main className="container mx-auto px-4 py-8">
      <h1 className="mb-8 text-3xl font-bold">Products</h1>
      <ProductGrid
        products={sampleProducts}
        page={page}
        pageSize={pageSize}
        totalItems={totalItems}
        onPageChange={handlePageChange}
        onAddToCart={handleAddToCart}
        onOpenProduct={handleOpenProduct}
      />
    </main>
  )
}
