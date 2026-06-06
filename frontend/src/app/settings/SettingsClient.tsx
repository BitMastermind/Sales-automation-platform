"use client"

import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useEffect, useMemo } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import PageHeader from "@/components/PageHeader"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
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

async function fetchGmailAuthUrl(): Promise<string> {
  const base = process.env.NEXT_PUBLIC_API_BASE
  if (!base) throw new Error("Missing env var: NEXT_PUBLIC_API_BASE")
  const res = await fetch(`${base.replace(/\/+$/, "")}/api/auth/gmail`)
  const json = (await res.json()) as
    | { data: { auth_url: string }; error: null; meta: Record<string, unknown> }
    | { detail: { data: { auth_url: string }; error: unknown; meta: Record<string, unknown> } }
  const envelope = "detail" in json ? json.detail : json
  return envelope.data.auth_url
}

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={[
        "inline-block h-2.5 w-2.5 rounded-full",
        ok ? "bg-emerald-500" : "bg-rose-500",
      ].join(" ")}
    />
  )
}

export default function SettingsClient({ envOk }: { envOk: Record<string, boolean> }) {
  const queryClient = useQueryClient()

  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const gmailQ = useQuery({
    queryKey: ["gmail-status"],
    queryFn: fetchGmailStatus,
    staleTime: 10_000,
  })

  const connectM = useMutation({
    mutationFn: fetchGmailAuthUrl,
    onSuccess: (url) => {
      window.location.href = url
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: ["gmail-status"] })
    },
  })

  useEffect(() => {
    const param = searchParams.get("gmail")
    if (param !== "connected") return
    toast.success("Gmail connected")
    const params = new URLSearchParams(searchParams.toString())
    params.delete("gmail")
    const qs = params.toString()
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [pathname, router, searchParams])

  const connected = gmailQ.data?.connected ?? false

  const keyRows = useMemo(() => {
    return [
      { key: "NEXT_PUBLIC_API_BASE", ok: Boolean(envOk.NEXT_PUBLIC_API_BASE) },
    ]
  }, [envOk.NEXT_PUBLIC_API_BASE])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Integrations and environment diagnostics"
      />

      <div className="grid grid-cols-2 gap-4">
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-900">
              Gmail
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between gap-4">
              <div className="text-sm">
                <div className="font-medium text-slate-900">
                  {connected ? "Connected" : "Not connected"}
                </div>
                <div className="text-slate-600">
                  {connected ? gmailQ.data?.email ?? "—" : "Connect to send and monitor replies."}
                </div>
              </div>
              <div className="shrink-0 flex items-center gap-2">
                <span
                  className={[
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium",
                    connected
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                      : "bg-rose-50 text-rose-800 border-rose-200",
                  ].join(" ")}
                >
                  <Dot ok={connected} />
                  {connected ? "Connected" : "Disconnected"}
                </span>
                {!connected ? (
                  <Button
                    onClick={() => connectM.mutate()}
                    disabled={connectM.isPending}
                  >
                    Connect Gmail
                  </Button>
                ) : (
                  <Link
                    href="/campaigns"
                    className={cn(buttonVariants({ variant: "outline" }))}
                  >
                    Go to Campaigns
                  </Link>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-900">
              API Keys
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-slate-600">
              Only presence is shown. Values are never displayed.
            </div>
            <Separator className="my-4" />
            <div className="space-y-3">
              {keyRows.map((r) => (
                <div key={r.key} className="flex items-center justify-between">
                  <div className="text-sm font-medium text-slate-900">{r.key}</div>
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <Dot ok={r.ok} />
                    {r.ok ? "Configured" : "Missing"}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
