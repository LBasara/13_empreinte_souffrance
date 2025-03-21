import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/app/ui/general/navbar";

export const metadata: Metadata = {
  title: "Create Next App",
  description: "Generated by create next app",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`antialiased`}>
        <header>
          <div className="w-full flex-none fixed">
            <Navbar />
          </div>
        </header>
        <div>{children}</div>
      </body>
    </html>
  );
}
