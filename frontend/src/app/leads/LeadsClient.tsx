"use client"

import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  Search,
  SlidersHorizontal,
  Mail,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  CalendarCheck,
  MailOpen,
  MessageSquareReply,
  Users,
} from "lucide-react"

import { fetchAllLeads, fetchCampaigns } from "@/lib/api"
import type { Lead } from "@/lib/types"
import StatusBadge from "@/components/StatusBadge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
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

const STATUSES = [
  { value: "", label: "All Statuses" },
  { value: "new", label: "New" },
  { value: "researched", label: "Researched" },
  { value: "email_sent", label: "Email Sent" },
  { value: "replied", label: "Replied" },
  { value: "meeting_booked", label: "Meeting Booked" },
  { value: "unsubscribed", label: "Unsubscribed" },
]

function fmtDate(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  return d.toLocaleDateString(undefined, { month: "short", day: "2-digit" })
}

function LeadAvatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()
  const colors = [
    "from-violet-400 to-indigo-500",
    "from-sky-400 to-cyan-500",
    "from-emerald-400 to-teal-500",
    "from-amber-400 to-orange-500",
    "from-rose-400 to-pink-500",
  ]
  const color = colors[name.charCodeAt(0) % colors.length]
  return (
    <div
      className={`h-8 w-8 rounded-full bg-gradient-to-br ${color} flex items-center justify-center shrink-0`}
    >
      <span className="text-white text-[11px] font-semibold">{initials}</span>
    </div>
  )
}

function StatPill({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  color: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-white border border-gray-100 shadow-sm px-5 py-4">
      <div className={`h-9 w-9 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="h-4 w-4 text-white" />
      </div>
      <div>
        <div className="text-xl font-bold text-gray-900">{value.toLocaleString()}</div>
        <div className="text-xs text-gray-400">{label}</div>
      </div>
    </div>
  )
}

export default function LeadsClient() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [campaignFilter, setCampaignFilter] = useState("")
  const [statusFilter, setStatusFilter] = useState("")

  const campaignsQ = useQuery({
    queryKey: ["campaigns-list"],
    queryFn: () => fetchCampaigns(1, 100),
  })
  const campaigns = campaignsQ.data?.data ?? []

  const q = useQuery({
    queryKey: ["all-leads", page, campaignFilter, statusFilter],
    queryFn: () => fetchAllLeads(page, campaignFilter || undefined, statusFilter || undefined),
  })

  const leads = q.data?.data ?? []
  const meta = q.data?.meta

  const filtered = useMemo(() => {
    if (!search.trim()) return leads
    const s = search.toLowerCase()
    return leads.filter(
      (l) =>
        l.contact_name?.toLowerCase().includes(s) ||
        l.company_name.toLowerCase().includes(s) ||
        l.email.toLowerCase().includes(s),
    )
  }, [leads, search])

  const totalPages = meta ? Math.max(1, Math.ceil(meta.total / meta.size)) : 1

  const allLeads = Object.values(
    (campaignsQ.data?.data ?? []).reduce(
      (acc: Record<string, Lead[]>, _c) => acc,
      {},
    ),
  ).flat()

  const stats = useMemo(() => {
    const all = q.data?.data ?? []
    return {
      total: meta?.total ?? all.length,
      emailed: all.filter((l) => ["email_sent", "replied", "meeting_booked"].includes(l.status)).length,
      replied: all.filter((l) => ["replied", "meeting_booked"].includes(l.status)).length,
      meetings: all.filter((l) => l.status === "meeting_booked").length,
    }
  }, [q.data, meta])

  const campaignName = (id: string) =>
    campaigns.find((c) => c.id === id)?.name ?? id

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Leads</h1>
          <p className="mt-1 text-sm text-gray-400">All contacts across every campaign</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatPill icon={Users} label="Total Leads" value={stats.total} color="bg-indigo-500" />
        <StatPill icon={Mail} label="Emailed" value={stats.emailed} color="bg-sky-500" />
        <StatPill icon={MessageSquareReply} label="Replied" value={stats.replied} color="bg-emerald-500" />
        <StatPill icon={CalendarCheck} label="Meetings Booked" value={stats.meetings} color="bg-violet-500" />
      </div>

      {/* Filters */}
      <div className="rounded-2xl bg-white border border-gray-100 shadow-sm">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-50">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search name, company, email…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 placeholder:text-gray-400"
            />
          </div>

          {/* Campaign filter */}
          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 focus:outline-none transition-colors">
              <SlidersHorizontal className="h-3.5 w-3.5" />
              {campaignFilter ? campaignName(campaignFilter) : "All Campaigns"}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuItem onClick={() => { setCampaignFilter(""); setPage(1) }}>
                All Campaigns
              </DropdownMenuItem>
              {campaigns.map((c) => (
                <DropdownMenuItem key={c.id} onClick={() => { setCampaignFilter(c.id); setPage(1) }}>
                  {c.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Status filter */}
          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 focus:outline-none transition-colors">
              {STATUSES.find((s) => s.value === statusFilter)?.label ?? "All Statuses"}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              {STATUSES.map((s) => (
                <DropdownMenuItem key={s.value} onClick={() => { setStatusFilter(s.value); setPage(1) }}>
                  {s.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <div className="ml-auto text-xs text-gray-400">
            {meta?.total ?? 0} leads
          </div>
        </div>

        {/* Table */}
        <Table>
          <TableHeader>
            <TableRow className="border-gray-50 hover:bg-transparent">
              <TableHead className="text-xs font-semibold text-gray-400 uppercase tracking-wide w-[280px]">Contact</TableHead>
              <TableHead className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Campaign</TableHead>
              <TableHead className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Status</TableHead>
              <TableHead className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Email</TableHead>
              <TableHead className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Added</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {q.isLoading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i} className="border-gray-50">
                    <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20 rounded-full" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-44" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                    <TableCell />
                  </TableRow>
                ))
              : filtered.map((lead) => (
                  <TableRow key={lead.id} className="border-gray-50 hover:bg-gray-50/60 cursor-default">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <LeadAvatar name={lead.contact_name ?? lead.company_name} />
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-gray-900 truncate">
                            {lead.contact_name ?? "—"}
                          </div>
                          <div className="text-xs text-gray-400 truncate">{lead.company_name}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-gray-600 truncate block max-w-[180px]">
                        {campaignName(lead.campaign_id)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusBadge kind="lead" value={lead.status} />
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-gray-500">{lead.email}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-gray-400">{fmtDate(lead.created_at)}</span>
                    </TableCell>
                    <TableCell>
                      {lead.website && (
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-gray-300 hover:text-indigo-500 transition-colors"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
            {!q.isLoading && filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-16 text-center">
                  <div className="text-sm text-gray-400">No leads match your filters.</div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-50">
            <span className="text-xs text-gray-400">
              Page {page} of {totalPages}
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0 rounded-lg border-gray-200"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0 rounded-lg border-gray-200"
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
