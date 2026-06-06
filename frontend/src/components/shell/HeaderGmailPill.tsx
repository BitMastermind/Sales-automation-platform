"use client"

import { useQuery } from "@tanstack/react-query"
import { Bell, Mail } from "lucide-react"

import { cn } from "@/lib/utils"

type GmailStatus = { connected: boolean; email: string | null }

async function fetchGmailStatus(): Promise<GmailStatus> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
    return { connected: true, email: "ashitverma56@gmail.com" }
  }
  const base = process.env.NEXT_PUBLIC_API_BASE
  if (!base) throw new Error("Missing env var: NEXT_PUBLIC_API_BASE")
  const res = await fetch(`${base.replace(/\/+$/, "")}/api/auth/gmail/status`)
  const json = (await res.json()) as
    | { data: GmailStatus; error: null; meta: Record<string, unknown> }
    | { detail: { data: GmailStatus; error: unknown; meta: Record<string, unknown> } }

  const envelope = "detail" in json ? json.detail : json
  return envelope.data
}

export default function HeaderGmailPill() {
  const { data } = useQuery({
    queryKey: ["gmail-status"],
    queryFn: fetchGmailStatus,
    staleTime: 10_000,
  })

  const connected = data?.connected ?? false

  return (
    <div className="flex items-center gap-3">
      {/* Notification bell */}
      <button
        type="button"
        className="relative h-9 w-9 rounded-xl bg-gray-50 hover:bg-gray-100 border border-gray-100 flex items-center justify-center transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4 text-gray-500" />
        <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-indigo-600" />
      </button>

      {/* Gmail status */}
      <div
        className={cn(
          "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium",
          connected
            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
            : "bg-rose-50 text-rose-700 border-rose-200",
        )}
      >
        <Mail className="h-3.5 w-3.5" />
        <span>{connected ? "Gmail connected" : "Gmail not connected"}</span>
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            connected ? "bg-emerald-500" : "bg-rose-500",
          )}
        />
      </div>

      {/* User avatar */}
      <div className="h-9 w-9 rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center cursor-pointer shrink-0">
        <span className="text-white text-xs font-semibold">AV</span>
      </div>
    </div>
  )
}
