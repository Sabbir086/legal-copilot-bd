import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Legal Copilot BD | বাংলাদেশের নথি ও আইন সহকারী",
  description: "বাংলাদেশের আইন, আইনি ঘটনা, মামলা ও নথি বুঝতে প্রমাণভিত্তিক AI সহায়তা।",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="bn">
      <body>{children}</body>
    </html>
  );
}
