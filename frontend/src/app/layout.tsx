import type { Metadata } from "next"
import { GeistMono } from "geist/font/mono"
import { GeistSans } from "geist/font/sans"

import "./globals.css"

import Providers from "@/app/providers"
import HeaderGmailPill from "@/components/shell/HeaderGmailPill"
import Sidebar from "@/components/shell/Sidebar"

const geistSans = GeistSans
const geistMono = GeistMono

export const metadata: Metadata = {
  title: "SalesHQ",
  description: "AI-powered B2B sales outreach",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex bg-slate-50 text-slate-900">
        <Providers>
          <Sidebar />
          <div className="flex-1 flex flex-col min-h-screen">
            <header className="h-14 shrink-0 border-b bg-white px-8 flex items-center justify-between">
              <div className="text-sm text-slate-600">Workspace</div>
              <HeaderGmailPill />
            </header>
            <main className="flex-1 p-8">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
