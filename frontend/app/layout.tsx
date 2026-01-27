import "./globals.css";
import type { Metadata } from "next";

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
      <body>{children}</body>
    </html>
  );
}
