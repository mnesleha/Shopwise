import ProductGridClient, {
  type ProductGridItem,
} from "@/components/product/ProductGridClient";
import { apiFetch } from "@/lib/server-fetch";
import {
  mapProductToGridItem,
  type ProductListItemDto,
} from "@/lib/mappers/products";

type SearchParams = {
  page?: string;
  pageSize?: string;
  category?: string;
};

function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page ?? "1") || 1);
  const pageSize = Math.min(50, Math.max(5, Number(sp.pageSize ?? "12") || 12));
  const categoryId = sp.category ? Number(sp.category) : null;

  const qs = new URLSearchParams();
  if (categoryId) qs.set("category", String(categoryId));
  const dto = await apiFetch<ProductListItemDto[]>(
    qs.toString() ? `/api/v1/products/?${qs.toString()}` : "/api/v1/products/",
  );
  const all: ProductGridItem[] = dto.map(mapProductToGridItem);

  const totalItems = all.length;
  const products = paginate(all, page, pageSize);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Products</h1>
        <p className="text-muted-foreground">Frontend guard: DRF wiring</p>
      </div>

      <ProductGridClient
        products={products}
        page={page}
        pageSize={pageSize}
        totalItems={totalItems}
      />
    </div>
  );
}
