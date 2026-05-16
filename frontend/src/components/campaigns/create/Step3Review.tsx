"use client"

import * as React from "react"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { toast } from "sonner"

import type { CampaignFormData } from "@/components/campaigns/create/types"
import { createCampaign, patchCampaignStatus, uploadLeads } from "@/lib/api"
import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

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

function toneLabel(tone: CampaignFormData["tone"]): string {
  if (tone === "professional_friendly") return "Professional & Friendly"
  if (tone === "direct") return "Direct"
  return "Warm"
}

function fmtMinutes(v: number): string {
  if (!Number.isFinite(v) || v <= 0) return "—"
  if (v < 1) return "< 1 min"
  return v % 1 === 0 ? `${v.toFixed(0)} min` : `${v.toFixed(1)} min`
}

export default function Step3Review({
  formData,
  launchError,
  setLaunchError,
  setIsLaunching,
  setLaunchFn,
  onDone,
}: {
  formData: CampaignFormData
  launchError: string | null
  setLaunchError: (v: string | null) => void
  setIsLaunching: (v: boolean) => void
  setLaunchFn: (fn: () => void) => void
  onDone: (campaignId: string) => void
}) {
  const gmailQ = useQuery({
    queryKey: ["gmail-status"],
    queryFn: fetchGmailStatus,
    staleTime: 10_000,
  })

  const launch = React.useCallback(async () => {
    if (!formData.file) {
      setLaunchError("Missing CSV file. Go back and upload your leads.")
      return
    }
    if (formData.validRows <= 0) {
      setLaunchError("No valid leads to upload. Fix your mapping and try again.")
      return
    }

    setLaunchError(null)
    setIsLaunching(true)

    try {
      const campaign = await createCampaign({
        name: formData.name.trim(),
        settings: {
          product: formData.product.trim(),
          valueProp: formData.valueProp.trim(),
          caseStudy: formData.caseStudy.trim(),
          tone: formData.tone,
          columnMapping: formData.columnMapping,
          csvStats: {
            validRows: formData.validRows,
            invalidRows: formData.invalidRows.length,
          },
        },
      })

      await uploadLeads(campaign.id, formData.file)

      await patchCampaignStatus(campaign.id, "active")

      toast.success("Campaign launched")
      onDone(campaign.id)
    } catch (e) {
      const message =
        e instanceof Error
          ? e.message
          : "Something went wrong while launching. Please try again."
      setLaunchError(message)
    } finally {
      setIsLaunching(false)
    }
  }, [formData, onDone, setIsLaunching, setLaunchError])

  React.useEffect(() => {
    setLaunchFn(launch)
  }, [launch, setLaunchFn])

  const minutes = (formData.validRows * 30) / 60
  const connected = gmailQ.data?.connected ?? false

  return (
    <div className="space-y-4">
      {launchError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {launchError}
        </div>
      ) : null}

      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-slate-900">
            Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <div className="text-xs text-slate-600">Campaign</div>
              <div className="font-medium text-slate-900">
                {formData.name || "—"}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-600">Product</div>
              <div className="font-medium text-slate-900">
                {formData.product || "—"}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-600">Tone</div>
              <div className="font-medium text-slate-900">
                {toneLabel(formData.tone)}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-2 border-t">
            <div>
              <div className="text-xs text-slate-600">Leads</div>
              <div className="font-medium text-slate-900 tabular-nums">
                {formData.validRows} valid, {formData.invalidRows.length} skipped
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-600">Estimated send time</div>
              <div className="font-medium text-slate-900 tabular-nums">
                {fmtMinutes(minutes)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-600">Gmail status</div>
              <div className="font-medium">
                <span
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs",
                    connected
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                      : "bg-amber-50 text-amber-900 border-amber-200",
                  )}
                >
                  {connected ? "Connected ✓" : "Not connected ⚠"}
                </span>
                {!connected ? (
                  <Link
                    href="/settings"
                    className={cn(buttonVariants({ variant: "link" }), "h-auto p-0 ml-2 text-xs")}
                  >
                    Connect in settings
                  </Link>
                ) : null}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="rounded-xl border bg-white p-4">
        <div className="text-sm font-medium text-slate-900">Ready to launch?</div>
        <div className="text-xs text-slate-600 mt-1">
          Launch runs in 3 steps: create campaign → upload leads → activate. If any step fails, the campaign won’t be left active.
        </div>
      </div>
    </div>
  )
}
