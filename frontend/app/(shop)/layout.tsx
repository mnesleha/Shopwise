import Header from "@/components/shell/Header";
import Footer from "@/components/shell/Footer";
import Container from "@/components/shell/Container";
import { AuthProvider } from "@/components/auth/AuthProvider";

export default function ShopLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <div className="min-h-dvh flex flex-col">
        <Header />
        <main className="flex-1">
          <Container>{children}</Container>
        </main>
        <Footer />
      </div>
    </AuthProvider>
  );
}
