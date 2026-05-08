import "./globals.css";
import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import { Analytics } from "@vercel/analytics/next";
import ClaritySnippet from "@/components/analytics/ClaritySnippet";

export const metadata: Metadata = {
  title: "Shopwise",
  description: "Demo e-commerce frontend guard for Shopwise backend",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        {children}
        <Analytics />
        <ClaritySnippet />
        <Toaster
          richColors
          position="top-center"
          expand
          visibleToasts={6}
          duration={8000}
          closeButton
        />
      </body>
    </html>
  );
}
