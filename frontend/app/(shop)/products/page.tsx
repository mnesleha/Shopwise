"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Product = {
  id: string | number;
  name: string;
  price: string;
};

export default function ProductsPage() {
  const [data, setData] = useState<Product[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/v1/products/")
      .then((r: any) => setData(r.data?.results ?? r.data))
      .catch((e: any) => setErr(String(e?.message ?? e)));
  }, []);

  return (
    <main style={{ padding: 16 }}>
      <h1>Products connectivity test</h1>

      {err && <pre style={{ whiteSpace: "pre-wrap" }}>ERROR: {err}</pre>}
      {!err && !data && <p>Loading…</p>}

      {data && (
        <ul>
          {data.map((p) => (
            <li key={String(p.id)}>
              {p.name} – {p.price}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
