import Header from "@/components/shell/Header";
import Footer from "@/components/shell/Footer";
import Container from "@/components/shell/Container";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { CartProvider } from "@/components/cart/CartProvider";
import { apiFetch } from "@/lib/server-fetch";

type AuthMeResponse =
  | { is_authenticated: true; email?: string }
  | { is_authenticated: false };

type CartDto = {
  items?: Array<{ quantity?: number }>;
  cart_items?: Array<{ quantity?: number }>;
};

export default async function ShopLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // SSR: fetch initial state once here to hydrate providers (avoids FOUC)
  let isAuthenticated = false;
  let email: string | undefined = undefined;
  let initialCartCount = 0;

  try {
    const me = await apiFetch<AuthMeResponse>("/api/v1/auth/me/", {
      forwardCookies: true,
    });
    if (me?.is_authenticated === true) {
      isAuthenticated = true;
      email = me.email;
    }
  } catch {
    // layout must be resilient
  }

  try {
    const cart = await apiFetch<CartDto>("/api/v1/cart/", {
      forwardCookies: true,
    });
    const list = cart.items ?? cart.cart_items ?? [];
    initialCartCount = list.reduce((sum, it) => sum + (it.quantity ?? 0), 0);
  } catch {
    // guest / anonymous: cart may not exist yet
  }

  return (
    <AuthProvider initialIsAuthenticated={isAuthenticated} initialEmail={email}>
      <CartProvider initialCount={initialCartCount}>
        <div className="min-h-dvh flex flex-col">
          <Header />
          <main className="flex-1">
            <Container>{children}</Container>
          </main>
          <Footer />
        </div>
      </CartProvider>
    </AuthProvider>
  );
}
