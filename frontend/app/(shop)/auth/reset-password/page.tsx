/**
 * /auth/reset-password — password reset confirmation page (server wrapper).
 *
 * Reads `?token=` from the URL server-side and passes it to the client form.
 * In Next.js 15 `searchParams` is an async prop — must be awaited.
 */

import ResetPasswordForm from "./ResetPasswordForm";

interface Props {
  searchParams: Promise<{ token?: string }>;
}

export default async function ResetPasswordPage({ searchParams }: Props) {
  const { token } = await searchParams;

  return <ResetPasswordForm token={token ?? ""} />;
}
