import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Transfer Investigation — Wealthsimple Ops",
  description:
    "Internal ops tool for investigating stuck or failed transfer complaints.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-white text-dune min-h-screen font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
