import type { Metadata } from "next";
import { Figtree, Newsreader } from "next/font/google";

import "./globals.css";

const figtree = Figtree({
  subsets: ["latin"],
  variable: "--font-figtree",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
});

export const metadata: Metadata = {
  title: "CFIP · College Football Intelligence",
  description:
    "A sourced college football team ledger. Select a season and a team to view stored season stats and results, with the data source labeled. Not a betting product.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${figtree.variable} ${newsreader.variable} dark h-full`}>
      <body className="min-h-full bg-background text-foreground antialiased">{children}</body>
    </html>
  );
}
