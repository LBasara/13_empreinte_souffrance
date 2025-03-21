import type { Metadata } from "next";
import "./globals.css";
import { I18nProviderClient } from "../../locales/client";
import { ReactElement } from "react";
import Navbar from "./ui/general/navbar";

export const metadata: Metadata = {
  title: "Create Next App",
  description: "Generated by create next app",
};

export default async function RootLayout({
  params,
  children,
}: {
  params: Promise<{ locale: string }>;
  children: ReactElement;
}) {
  const { locale } = await params;

  return (
    <html lang={locale}>
      <body className="antialiased">
        <header>
          <div className="w-full flex-none fixed">
            <Navbar />
          </div>
        </header>
        <I18nProviderClient locale={locale}>{children}</I18nProviderClient>
      </body>
    </html>
  );
}
