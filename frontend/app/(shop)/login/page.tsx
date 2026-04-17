import LoginPageClient from "./LoginPageClient";

type LoginPageSearchParams = {
  verified?: string;
  emailChanged?: string;
  passwordChanged?: string;
  passwordReset?: string;
};

type Props = {
  searchParams: Promise<LoginPageSearchParams>;
};

export default async function LoginPage({ searchParams }: Props) {
  const params = await searchParams;

  return (
    <LoginPageClient
      showVerifiedToast={params.verified === "1"}
      showEmailChangedToast={params.emailChanged === "1"}
      showPasswordChangedToast={params.passwordChanged === "1"}
      showPasswordResetToast={params.passwordReset === "1"}
    />
  );
}
