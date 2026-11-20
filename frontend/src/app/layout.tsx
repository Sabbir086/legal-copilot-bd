import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MyLegal AI | বাংলাদেশের AI Legal Assistant",
  description: "বাংলাদেশের আইনি প্রশ্ন, নথি ও কথোপকথনের জন্য AI-powered legal assistant।",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="bn">
      <body>{children}</body>
    </html>
  );
}
