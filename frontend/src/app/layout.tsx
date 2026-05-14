import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SalesHQ",
  description: "AI-powered B2B sales outreach",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex">
        <aside className="w-56 border-r flex flex-col p-4 shrink-0 min-h-screen">
          <div className="font-semibold text-sm mb-6 px-2">SalesHQ</div>
          <nav className="flex flex-col gap-1 text-sm text-muted-foreground">
            {["Dashboard", "Campaigns", "Leads", "Templates", "Integrations", "Settings"].map(
              (item) => (
                <div key={item} className="px-2 py-1.5 rounded hover:bg-muted cursor-pointer">
                  {item}
                </div>
              )
            )}
          </nav>
        </aside>
        <div className="flex-1 flex flex-col">
          <header className="border-b h-14 flex items-center px-6 text-sm font-medium shrink-0">
            SalesHQ Workspace
          </header>
          <main className="flex-1 p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
