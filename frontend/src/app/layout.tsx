import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MyLegal AI | বাংলাদেশের AI Legal Assistant",
  description: "বাংলাদেশের আইনি প্রশ্ন, নথি ও কথোপকথনের জন্য AI-powered legal assistant।",
};

function getOrigin(value: string | undefined) {
  if (!value) return "";
  try {
    return new URL(value).origin;
  } catch {
    return "";
  }
}

// Warm up DNS/TLS for the existing Singapore Render API and Seoul Supabase project.
// This improves first-request setup time without moving either deployed service.
const apiOrigin = getOrigin(process.env.NEXT_PUBLIC_API_URL);
const supabaseOrigin = getOrigin(process.env.NEXT_PUBLIC_SUPABASE_URL);

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="bn">
      <head>
        {apiOrigin && <link rel="preconnect" href={apiOrigin} crossOrigin="anonymous" />}
        {supabaseOrigin && <link rel="preconnect" href={supabaseOrigin} crossOrigin="anonymous" />}
        {apiOrigin && <link rel="dns-prefetch" href={apiOrigin} />}
        {supabaseOrigin && <link rel="dns-prefetch" href={supabaseOrigin} />}
      </head>
      <body>{children}</body>
    </html>
  );
}
