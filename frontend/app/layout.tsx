import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEO Tracker — Competitor Intelligence Platform",
  description: "Monitor competitors, track rankings, analyze AI visibility",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-surface-0 text-zinc-200 antialiased">
        {children}
      </body>
    </html>
  );
}
