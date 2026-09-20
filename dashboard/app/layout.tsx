import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "mint — LLM 비용 최적화",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}
