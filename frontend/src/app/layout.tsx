import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { Toaster } from "sonner";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["300", "400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Data Analyst Copilot — AI-Powered Data Analysis",
  description:
    "An AI-powered assistant that analyzes CSV/Excel datasets, answers questions in natural language, generates visualizations, performs statistical analysis, and creates reports.",
  keywords: ["data analysis", "AI", "CSV", "machine learning", "visualization", "pandas", "analytics"],
  authors: [{ name: "Data Analyst Copilot" }],
  openGraph: {
    title: "Data Analyst Copilot",
    description: "AI-powered data analysis platform",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className={`${inter.variable} antialiased`}>
        <Providers>
          {children}
          <Toaster
            position="bottom-right"
            theme="dark"
            toastOptions={{
              style: {
                background: "#0f1f35",
                border: "1px solid #1e3a5f",
                color: "#e8f0fe",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
