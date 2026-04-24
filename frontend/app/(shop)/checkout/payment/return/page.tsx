import PaymentReturnPageClient from "@/components/checkout/PaymentReturnPageClient";

type PaymentReturnPageSearchParams = {
  orderId?: string | string[];
  guest?: string | string[];
};

type Props = {
  searchParams: Promise<PaymentReturnPageSearchParams>;
};

function getSingleValue(
  value: string | string[] | undefined,
): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function PaymentReturnPage({ searchParams }: Props) {
  const params = await searchParams;

  return (
    <PaymentReturnPageClient
      initialOrderId={getSingleValue(params.orderId)}
      initialGuest={getSingleValue(params.guest)}
    />
  );
}
