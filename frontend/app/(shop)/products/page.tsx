import ProductGridClient from "@/components/product/ProductGridClient";
import SortDropdown from "@/components/product/SortDropdown";
import ActiveFilterChips from "@/components/product/ActiveFilterChips";
import { apiFetch } from "@/lib/server-fetch";
import {
  mapProductToGridItem,
  type CatalogueResponseDto,
} from "@/lib/mappers/products";

type SearchParams = {
  page?: string;
  pageSize?: string;
  category?: string | string[];
  min_price?: string;
  max_price?: string;
  in_stock_only?: string;
  sort?: string;
  search?: string;
};

type CategoryDto = { id: number; name: string };

function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

function buildProductsQs(sp: SearchParams): string {
  const params = new URLSearchParams();

  // Multi-value category
  const cats = Array.isArray(sp.category)
    ? sp.category
    : sp.category
      ? [sp.category]
      : [];
  cats.forEach((c) => params.append("category", c));

  if (sp.min_price) params.set("min_price", sp.min_price);
  if (sp.max_price) params.set("max_price", sp.max_price);
  if (sp.in_stock_only === "true") params.set("in_stock_only", "true");
  if (sp.sort) params.set("sort", sp.sort);
  if (sp.search) params.set("search", sp.search);

  return params.toString();
}

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page ?? "1") || 1);
  const pageSize = Math.min(50, Math.max(5, Number(sp.pageSize ?? "12") || 12));

  const qs = buildProductsQs(sp);

  const [catalogueDto, categories] = await Promise.all([
    apiFetch<CatalogueResponseDto>(
      qs ? `/api/v1/products/?${qs}` : "/api/v1/products/",
    ),
    apiFetch<CategoryDto[]>("/api/v1/categories/").catch(
      () => [] as CategoryDto[],
    ),
  ]);

  const all = catalogueDto.results.map(mapProductToGridItem);
  const totalItems = all.length;
  const products = paginate(all, page, pageSize);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Products</h1>

      {/* ── Toolbar: chips (left) + sort (pinned right) ─────── */}
      <div className="flex items-center gap-3 flex-wrap">
        <ActiveFilterChips categories={categories} />
        <div className="ml-auto shrink-0">
          <SortDropdown />
        </div>
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
