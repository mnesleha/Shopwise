import { apiFetch } from "@/lib/server-fetch";
import { mapProductToDetailVm, type ProductDetailDto } from "@/lib/mappers/products";
import ProductDetailClient from "@/components/product/ProductDetailClient";

type Params = { id: string };

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;

  const dto = await apiFetch<ProductDetailDto>(`/api/v1/products/${id}/`);
  const product = mapProductToDetailVm(dto);

  return (
    <div className="space-y-6">
      <ProductDetailClient product={product} />
    </div>
  );
}
