import ClaimOfferClient from "./ClaimOfferClient";

export const metadata = {
  title: "Claim Offer | Shopwise",
};

type ClaimOfferSearchParams = {
  token?: string;
};

type Props = {
  searchParams: Promise<ClaimOfferSearchParams>;
};

export default async function ClaimOfferPage({ searchParams }: Props) {
  const params = await searchParams;

  return <ClaimOfferClient token={params.token ?? null} />;
}
