"use client"

import { useQuery } from "@tanstack/react-query"
import { Mail } from "lucide-react"

type GmailStatus = { connected: boolean; email: string | null }

async function fetchGmailStatus(): Promise<GmailStatus> {
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
    <div
      className={[
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium",
        connected
          ? "bg-emerald-50 text-emerald-800 border-emerald-200"
          : "bg-rose-50 text-rose-800 border-rose-200",
      ].join(" ")}
    >
      <Mail className="h-3.5 w-3.5" />
      <span>{connected ? "Gmail connected" : "Gmail not connected"}</span>
    </div>
  )
}
