"use client"

import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ExternalLink, FileSpreadsheet, X } from "lucide-react"

import {
  fetchCampaign,
  fetchLead,
  fetchLeads,
  patchCampaignStatus,
} from "@/lib/api"
import type { CampaignDetail, CampaignStatus, Lead, Meta } from "@/lib/types"

import EmptyState from "@/components/EmptyState"
import PageHeader from "@/components/PageHeader"
import StatCard from "@/components/StatCard"
import StatusBadge from "@/components/StatusBadge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

function fmtDateTime(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit" })
}

function fmtDate(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" })
}

function fmtPct(v: number) {
  return `${Math.round(v * 100)}%`
}

function totalPages(meta: Meta | undefined) {
  if (!meta?.size) return 1
  return Math.max(1, Math.ceil((meta.total ?? 0) / meta.size))
}

function toggleStatus(status: string): CampaignStatus {
  return status === "active" ? "paused" : "active"
}

function emailTone(type: string) {
  return type === "outreach"
    ? "bg-sky-50 text-sky-800 border-sky-200"
    : "bg-violet-50 text-violet-800 border-violet-200"
}

export default function CampaignDetailClient({ campaignId }: { campaignId: string }) {
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const queryClient = useQueryClient()

  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const leadId = searchParams.get("lead")

  const campaignQ = useQuery({
    queryKey: ["campaign", campaignId],
    queryFn: () => fetchCampaign(campaignId),
    select: (r) => r.data,
  })

  const leadsQ = useQuery({
    queryKey: ["leads", { campaignId, page }],
    queryFn: () => fetchLeads(campaignId, page),
  })

  const statusM = useMutation({
    mutationFn: ({ id, status }: { id: string; status: CampaignStatus }) =>
      patchCampaignStatus(id, status),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] })
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] })
    },
  })

  const leadQ = useQuery({
    queryKey: ["lead", leadId],
    enabled: Boolean(leadId),
    queryFn: async () => {
      if (!leadId) throw new Error("Missing lead id")
      return await fetchLead(leadId)
    },
    select: (r) => r.data,
  })

  const tp = totalPages(leadsQ.data?.meta)

  const campaign = campaignQ.data
  const stats = campaign?.stats

  const setLeadParam = (id: string | null) => {
    const params = new URLSearchParams(searchParams.toString())
    if (!id) params.delete("lead")
    else params.set("lead", id)
    const qs = params.toString()
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }

  const cards = useMemo(() => {
    if (!stats) return []
    return [
      { label: "Total Leads", value: stats.leads_count },
      { label: "Emails Sent", value: stats.emails_sent },
      { label: "Open Rate", value: fmtPct(stats.open_rate) },
      { label: "Reply Rate", value: fmtPct(stats.reply_rate) },
      { label: "Meetings Booked", value: stats.meetings_booked },
    ]
  }, [stats])

  if (campaignQ.isError) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-500 gap-2">
        <p className="text-base font-medium">Campaign not found</p>
        <p className="text-sm">This campaign may have been deleted or the link is incorrect.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={campaign?.name ?? "Campaign"}
        subtitle={
          campaign?.created_at
            ? `Launched ${fmtDate(campaign.created_at)}`
            : "—"
        }
        action={
          campaign ? (
            <div className="flex items-center gap-3">
              <StatusBadge kind="campaign" value={campaign.status} />
              <Button
                variant="outline"
                disabled={statusM.isPending || campaign.status === "draft"}
                onClick={() =>
                  statusM.mutate({
                    id: campaign.id,
                    status: toggleStatus(campaign.status),
                  })
                }
              >
                {campaign.status === "active" ? "Pause" : "Resume"}
              </Button>
            </div>
          ) : null
        }
      />

      <div className="grid grid-cols-5 gap-4">
        {cards.length
          ? cards.map((c) => <StatCard key={c.label} label={c.label} value={c.value} />)
          : Array.from({ length: 5 }).map((_, i) => (
              <Card key={i} className="shadow-sm">
                <CardContent className="p-4">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-7 w-16 mt-2" />
                </CardContent>
              </Card>
            ))}
      </div>

      <Card className="shadow-sm">
        <CardContent className="p-0">
          <div className="px-4 py-3 flex items-center justify-between border-b">
            <div className="text-sm font-semibold text-slate-900">Leads</div>
            <Button variant="outline" size="sm" disabled>
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              Upload CSV
            </Button>
          </div>

          {leadsQ.isSuccess && leadsQ.data.data.length === 0 ? (
            <EmptyState
              title="No leads yet"
              description="Upload a CSV to start outreach."
              action={<Button disabled>Upload Leads</Button>}
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[260px]">Company</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Touched</TableHead>
                    <TableHead className="w-[56px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leadsQ.isLoading
                    ? Array.from({ length: 6 }).map((_, i) => (
                        <TableRow key={i}>
                          <TableCell>
                            <Skeleton className="h-4 w-[200px]" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-4 w-24" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-4 w-[220px]" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-5 w-20 rounded-full" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-4 w-28" />
                          </TableCell>
                          <TableCell />
                        </TableRow>
                      ))
                    : (leadsQ.data?.data ?? []).map((l: Lead) => (
                        <TableRow
                          key={l.id}
                          className="hover:bg-slate-50 cursor-pointer"
                          onClick={() => setLeadParam(l.id)}
                        >
                          <TableCell className="font-medium">
                            {l.company_name}
                          </TableCell>
                          <TableCell className="text-slate-700">
                            {l.contact_name ?? "—"}
                          </TableCell>
                          <TableCell className="text-slate-700">
                            {l.email}
                          </TableCell>
                          <TableCell>
                            <StatusBadge kind="lead" value={l.status} />
                          </TableCell>
                          <TableCell className="text-slate-600">
                            {fmtDateTime(l.created_at)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={(e) => {
                                e.stopPropagation()
                                setLeadParam(l.id)
                              }}
                            >
                              <ExternalLink className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                </TableBody>
              </Table>

              <div className="flex items-center justify-between px-4 py-3 border-t">
                <div className="text-xs text-slate-600">
                  Page {page} of {tp}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1 || leadsQ.isLoading}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= tp || leadsQ.isLoading}
                    onClick={() => setPage((p) => Math.min(tp, p + 1))}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Sheet
        open={Boolean(leadId)}
        onOpenChange={(open) => {
          if (!open) setLeadParam(null)
        }}
      >
        <SheetContent className="w-[520px] sm:max-w-[520px] p-0">
          <div className="px-5 py-4 border-b flex items-center justify-between">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-base font-semibold text-slate-900">
                {leadQ.data?.company_name ?? "Lead"}
              </SheetTitle>
              <div className="text-sm text-slate-600">
                {leadQ.data?.contact_name ?? "—"} • {leadQ.data?.email ?? "—"}
              </div>
            </SheetHeader>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setLeadParam(null)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="px-5 py-4">
            {leadQ.isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : leadQ.data?.emails?.length ? (
              <div className="space-y-5">
                {leadQ.data.emails.map((email) => {
                  const open = expanded[email.id] ?? false
                  const hasBody = Boolean(email.body)
                  const replies = email.replies ?? []
                  return (
                    <div key={email.id} className="rounded-lg border bg-white">
                      <div className="px-4 py-3 flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <Badge
                              variant="outline"
                              className={[
                                "rounded-full text-[11px] px-2 py-0.5 border",
                                emailTone(email.type),
                              ].join(" ")}
                            >
                              {email.type === "outreach" ? "Outreach" : "Follow-up"}
                            </Badge>
                            <div className="text-xs text-slate-600">
                              {email.sent_at ? fmtDateTime(email.sent_at) : "—"}
                            </div>
                          </div>
                          <div className="mt-2 font-semibold text-sm text-slate-900 truncate">
                            {email.subject ?? "(no subject)"}
                          </div>
                        </div>
                        {hasBody ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8"
                            onClick={() =>
                              setExpanded((p) => ({ ...p, [email.id]: !open }))
                            }
                          >
                            {open ? "Collapse" : "Expand"}
                          </Button>
                        ) : null}
                      </div>

                      {hasBody ? (
                        <div className="px-4 pb-3 text-sm text-slate-700">
                          <div
                            style={
                              open
                                ? undefined
                                : {
                                    display: "-webkit-box",
                                    WebkitLineClamp: 3,
                                    WebkitBoxOrient: "vertical",
                                    overflow: "hidden",
                                  }
                            }
                          >
                            {email.body}
                          </div>
                        </div>
                      ) : null}

                      {replies.length ? (
                        <div className="px-4 pb-4">
                          <Separator className="my-3" />
                          {replies.map((r) => (
                            <div
                              key={r.id}
                              className="rounded-md bg-slate-50 border px-3 py-2"
                            >
                              <div className="flex items-center justify-between gap-3">
                                <Badge variant="outline" className="text-xs capitalize">
                                  {r.classified_as.replaceAll("_", " ")}
                                </Badge>
                                <div className="text-xs text-slate-600">
                                  {fmtDateTime(r.received_at)}
                                </div>
                              </div>
                              <div className="mt-2 text-sm text-slate-800 whitespace-pre-wrap">
                                {r.content}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            ) : (
              <Card className="shadow-sm">
                <CardContent className="p-0">
                  <EmptyState
                    title="Research in progress…"
                    description="No email thread for this lead yet."
                  />
                </CardContent>
              </Card>
            )}

            <div className="mt-6 text-xs text-slate-500">
              <Link href={`/campaigns/${campaignId}`} className="hover:underline">
                View campaign
              </Link>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
