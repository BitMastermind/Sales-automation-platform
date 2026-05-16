"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { MoreHorizontal } from "lucide-react"

import { fetchCampaigns, patchCampaignStatus } from "@/lib/api"
import type { Campaign, CampaignStatus, Meta } from "@/lib/types"

import EmptyState from "@/components/EmptyState"
import PageHeader from "@/components/PageHeader"
import StatusBadge from "@/components/StatusBadge"
import CreateCampaignModal from "@/components/campaigns/CreateCampaignModal"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

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

export default function CampaignsClient() {
  const [page, setPage] = useState(1)
  const [createOpen, setCreateOpen] = useState(false)
  const queryClient = useQueryClient()
  const router = useRouter()

  const q = useQuery({
    queryKey: ["campaigns", { page }],
    queryFn: () => fetchCampaigns(page, 20),
  })

  const campaigns = q.data?.data ?? []
  const meta = q.data?.meta

  const m = useMutation({
    mutationFn: ({ id, status }: { id: string; status: CampaignStatus }) =>
      patchCampaignStatus(id, status),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] })
      await queryClient.invalidateQueries({ queryKey: ["campaign"] })
    },
  })

  const rows = useMemo(() => {
    return campaigns.map((c) => {
      const s = c.stats
      return {
        ...c,
        leads: s?.leads_count ?? 0,
        sent: s?.emails_sent ?? 0,
        openRate: s?.open_rate ?? 0,
        replyRate: s?.reply_rate ?? 0,
      }
    })
  }, [campaigns])

  const empty = q.isSuccess && rows.length === 0
  const tp = totalPages(meta)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Campaigns"
        subtitle="Monitor status and performance at a glance"
        action={<Button onClick={() => setCreateOpen(true)}>New Campaign</Button>}
      />

      <CreateCampaignModal
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={async (id) => {
          await queryClient.invalidateQueries({ queryKey: ["campaigns"] })
          router.push(`/campaigns/${id}`)
        }}
      />

      <Card className="shadow-sm">
        <CardContent className="p-0">
          {empty ? (
            <EmptyState
              title="No campaigns yet"
              description="Create a campaign to start sending outreach and tracking replies."
              action={<Button onClick={() => setCreateOpen(true)}>New Campaign</Button>}
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[320px]">Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Leads</TableHead>
                    <TableHead className="text-right">Sent</TableHead>
                    <TableHead className="text-right">Opened %</TableHead>
                    <TableHead className="text-right">Replied %</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="w-[56px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {q.isLoading
                    ? Array.from({ length: 3 }).map((_, i) => (
                        <TableRow key={i}>
                          <TableCell>
                            <Skeleton className="h-4 w-[260px]" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-5 w-20 rounded-full" />
                          </TableCell>
                          <TableCell className="text-right">
                            <Skeleton className="h-4 w-10 ml-auto" />
                          </TableCell>
                          <TableCell className="text-right">
                            <Skeleton className="h-4 w-10 ml-auto" />
                          </TableCell>
                          <TableCell className="text-right">
                            <Skeleton className="h-4 w-12 ml-auto" />
                          </TableCell>
                          <TableCell className="text-right">
                            <Skeleton className="h-4 w-12 ml-auto" />
                          </TableCell>
                          <TableCell>
                            <Skeleton className="h-4 w-24" />
                          </TableCell>
                          <TableCell />
                        </TableRow>
                      ))
                    : rows.map((c: Campaign & { leads: number; sent: number; openRate: number; replyRate: number }) => (
                        <TableRow
                          key={c.id}
                          className="hover:bg-slate-50 cursor-pointer"
                          onClick={() => router.push(`/campaigns/${c.id}`)}
                        >
                          <TableCell className="font-medium">
                            <Link
                              href={`/campaigns/${c.id}`}
                              className="text-slate-900 hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {c.name}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <StatusBadge kind="campaign" value={c.status} />
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {c.leads}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {c.sent}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {fmtPct(c.openRate)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {fmtPct(c.replyRate)}
                          </TableCell>
                          <TableCell className="text-slate-600">
                            {fmtDate(c.created_at)}
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger
                                className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-slate-100 focus:outline-none"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem
                                  onSelect={() => router.push(`/campaigns/${c.id}`)}
                                >
                                  View
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  disabled={m.isPending}
                                  onSelect={() =>
                                    m.mutate({
                                      id: c.id,
                                      status: toggleStatus(c.status),
                                    })
                                  }
                                >
                                  {c.status === "active" ? "Pause" : "Resume"}
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem disabled>Archive</DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
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
                    disabled={page <= 1 || q.isLoading}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= tp || q.isLoading}
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
    </div>
  )
}
