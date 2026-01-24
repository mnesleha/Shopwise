"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

type ProductDetail = {
  id: number;
  name: string;
  price: string;
  stock_quantity: number;
};

export default function ProductDetailPage() {
  const params = useParams();
  const productId = params?.id as string | undefined;

  const [data, setData] = useState<ProductDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;

    api.get(`/api/v1/products/${productId}/`)
      .then((r: any) => setData(r.data))
      .catch((e: any) => setErr(String(e?.response?.data?.detail || e?.message || e)));
  }, [productId]);

  return (
    <main className="p-4">
      <Link href="/products" className="text-blue-600 hover:underline mb-4 inline-block">
        ← Back to products
      </Link>

      <h1 className="text-3xl font-bold mb-4">Product Detail (Connectivity Test)</h1>

      {err && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          ERROR: {err}
        </div>
      )}

      {!err && !data && <p>Loading…</p>}

      {data && (
        <div className="bg-gray-100 p-4 rounded">
          <dl className="space-y-2">
            <div>
              <dt className="font-bold">ID:</dt>
              <dd>{data.id}</dd>
            </div>
            <div>
              <dt className="font-bold">Name:</dt>
              <dd>{data.name}</dd>
            </div>
            <div>
              <dt className="font-bold">Price:</dt>
              <dd>{data.price}</dd>
            </div>
            <div>
              <dt className="font-bold">Stock Quantity:</dt>
              <dd>{data.stock_quantity}</dd>
            </div>
          </dl>
        </div>
      )}
    </main>
  );
}
