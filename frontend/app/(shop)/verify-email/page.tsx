import VerifyEmailPageClient from "./VerifyEmailPageClient";

type VerifyEmailSearchParams = {
  token?: string;
};

type Props = {
  searchParams: Promise<VerifyEmailSearchParams>;
};

export default async function VerifyEmailPage({ searchParams }: Props) {
  const params = await searchParams;

  return <VerifyEmailPageClient token={params.token ?? null} />;
}
