import type { Metadata } from "next";
import RegisterForm from "@/components/register/RegisterForm";

export const metadata: Metadata = {
  title: "Create Account",
  description: "Sign up for a new account to start placing orders.",
};

export default function RegisterPage() {
  return (
    <main className="container mx-auto px-4 py-8">
      <RegisterForm />
    </main>
  );
}
