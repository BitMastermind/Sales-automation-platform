"use client"

import Link from "next/link"
import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ArrowUpRight, CalendarDays, TrendingUp } from "lucide-react"

import { fetchCampaigns } from "@/lib/api"
import type { Campaign } from "@/lib/types"

import EmptyState from "@/components/EmptyState"
import StatCard from "@/components/StatCard"
import StatusBadge from "@/components/StatusBadge"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

function fmtPct(v: number) {
  return `${Math.round(v * 100)}%`
}

function ymd(d: Date) {
  return d.toISOString().slice(0, 10)
}

function last30Days(): string[] {
  const out: string[] = []
  const now = new Date()
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(now.getDate() - i)
    out.push(ymd(d))
  }
  return out
}

function fmtDate(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  return d.toLocaleDateString(undefined, { month: "short", day: "2-digit", year: "numeric" })
}

function deriveDashboard(campaigns: Campaign[]) {
  const totals = campaigns.reduce(
    (acc, c) => {
      const s = c.stats
      acc.leads += s?.leads_count ?? 0
      acc.sent += s?.emails_sent ?? 0
      acc.opened += (s?.open_rate ?? 0) * (s?.emails_sent ?? 0)
      acc.replied += (s?.reply_rate ?? 0) * (s?.emails_sent ?? 0)
      acc.meetings += s?.meetings_booked ?? 0
      return acc
    },
    { leads: 0, sent: 0, opened: 0, replied: 0, meetings: 0 },
  )

  const openRate = totals.sent ? totals.opened / totals.sent : 0
  const replyRate = totals.sent ? totals.replied / totals.sent : 0

  const days = last30Days()
  const byDay = new Map(days.map((d) => [d, 0]))
  for (const c of campaigns) {
    const key = (c.created_at || "").slice(0, 10)
    if (!key) continue
    const prev = byDay.get(key)
    if (prev !== undefined) {
      byDay.set(key, prev + (c.stats?.emails_sent ?? 0))
    }
  }
  const emailsSentPerDay = days.map((d) => ({
    day: d.slice(5),
    sent: byDay.get(d) ?? 0,
  }))

  const replyRateByCampaign = [...campaigns]
    .filter((c) => (c.stats?.emails_sent ?? 0) > 0)
    .sort((a, b) => (b.stats?.reply_rate ?? 0) - (a.stats?.reply_rate ?? 0))
    .slice(0, 6)
    .map((c) => ({
      name: c.name.length > 14 ? `${c.name.slice(0, 14)}…` : c.name,
      rate: Math.round((c.stats?.reply_rate ?? 0) * 100),
    }))

  const openRateByCampaign = [...campaigns]
    .filter((c) => (c.stats?.emails_sent ?? 0) > 0)
    .sort((a, b) => (b.stats?.open_rate ?? 0) - (a.stats?.open_rate ?? 0))
    .slice(0, 6)
    .map((c) => ({
      name: c.name.length > 14 ? `${c.name.slice(0, 14)}…` : c.name,
      rate: Math.round((c.stats?.open_rate ?? 0) * 100),
    }))

  const recentCampaigns = [...campaigns]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)

  const topCampaigns = [...campaigns]
    .filter((c) => (c.stats?.reply_rate ?? 0) > 0)
    .sort((a, b) => (b.stats?.reply_rate ?? 0) - (a.stats?.reply_rate ?? 0))
    .slice(0, 4)

  return {
    totals: { leads: totals.leads, sent: totals.sent, openRate, replyRate, meetings: totals.meetings },
    emailsSentPerDay,
    replyRateByCampaign,
    openRateByCampaign,
    recentCampaigns,
    topCampaigns,
  }
}

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-2xl bg-white border border-gray-100 shadow-sm p-5">
      <div className="mb-1 text-sm font-medium text-gray-500">{title}</div>
      <div className="text-xl font-bold text-gray-900 mb-4">{subtitle}</div>
      {children}
    </div>
  )
}

export default function DashboardClient() {
  const q = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => fetchCampaigns(1, 200),
    select: (res) => deriveDashboard(res.data),
  })

  const hasCampaigns =
    (q.data?.totals.leads ?? 0) > 0 || (q.data?.totals.sent ?? 0) > 0
  const empty = q.isSuccess && !hasCampaigns

  const statCards = useMemo(() => {
    const t = q.data?.totals
    return [
      { label: "Total Leads", value: t?.leads ?? "—", hero: true, trend: { direction: "up" as const, value: "12%" } },
      { label: "Emails Sent", value: t?.sent ?? "—", trend: { direction: "up" as const, value: "8%" } },
      { label: "Open Rate", value: t ? fmtPct(t.openRate) : "—", trend: { direction: "up" as const, value: "3%" } },
      { label: "Meetings Booked", value: t?.meetings ?? "—", trend: { direction: "up" as const, value: "15%" } },
    ]
  }, [q.data?.totals])

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Dashboard</h1>
          <div className="mt-1 flex items-center gap-1.5 text-sm text-gray-400">
            Here&apos;s your analytic for:
            <button
              type="button"
              className="inline-flex items-center gap-1 text-indigo-600 font-medium hover:text-indigo-700"
            >
              <CalendarDays className="h-3.5 w-3.5" />
              This Month
              <span className="text-xs">▾</span>
            </button>
          </div>
        </div>
        <Link
          href="/campaigns"
          className={cn(
            buttonVariants(),
            "rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-200",
          )}
        >
          View Campaigns
        </Link>
      </div>

      {empty ? (
        <div className="rounded-2xl bg-white border border-gray-100 shadow-sm">
          <EmptyState
            title="No campaigns yet. Create your first one."
            description="Once you launch a campaign, stats and charts will show up here."
            action={<Link href="/campaigns" className={buttonVariants()}>Go to Campaigns</Link>}
          />
        </div>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-4 gap-4">
            {statCards.map((s) => (
              <StatCard
                key={s.label}
                label={s.label}
                value={s.value}
                trend={s.trend}
                hero={s.hero}
              />
            ))}
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-3 gap-4">
            <ChartCard
              title="Total Emails Sent"
              subtitle={`${q.data?.totals.sent ?? 0} this month`}
            >
              <div className="flex items-center gap-4 mb-3 text-xs text-gray-400">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-0.5 w-6 rounded bg-indigo-500" />
                  Current
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-0.5 w-6 rounded bg-gray-200" style={{ borderStyle: "dashed" }} />
                  Last Month
                </span>
              </div>
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={q.data?.emailsSentPerDay ?? []}>
                    <defs>
                      <linearGradient id="sentGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }}
                      cursor={{ stroke: "#e2e8f0" }}
                    />
                    <Area
                      type="monotone"
                      dataKey="sent"
                      stroke="#4f46e5"
                      strokeWidth={2}
                      fill="url(#sentGrad)"
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="Open Rate by Campaign"
              subtitle={`${Math.round((q.data?.totals.openRate ?? 0) * 100)}% avg open rate`}
            >
              <div className="flex items-center gap-4 mb-3 text-xs text-gray-400">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-3 w-3 rounded bg-indigo-500/80" />
                  Open %
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-3 w-3 rounded bg-gray-200" />
                  Reply %
                </span>
              </div>
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={q.data?.openRateByCampaign ?? []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }}
                      cursor={{ fill: "#f8fafc" }}
                    />
                    <Bar dataKey="rate" fill="#818cf8" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="Reply Rate Growth"
              subtitle={`${Math.round((q.data?.totals.replyRate ?? 0) * 100)}% avg reply rate`}
            >
              <div className="flex items-center gap-4 mb-3 text-xs text-gray-400">
                <span className="flex items-center gap-1.5">
                  <TrendingUp className="h-3.5 w-3.5 text-indigo-400" />
                  By campaign
                </span>
              </div>
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={q.data?.replyRateByCampaign ?? []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }}
                      cursor={{ stroke: "#e2e8f0" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="rate"
                      stroke="#4f46e5"
                      strokeWidth={2.5}
                      dot={{ fill: "#4f46e5", r: 4, strokeWidth: 2, stroke: "#fff" }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* Bottom: Recent Campaigns + Top Performers */}
          <div className="grid grid-cols-5 gap-4">
            {/* Recent Campaigns */}
            <div className="col-span-3 rounded-2xl bg-white border border-gray-100 shadow-sm">
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-50">
                <h2 className="text-sm font-semibold text-gray-900">Recent Campaigns</h2>
                <Link
                  href="/campaigns"
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                >
                  See All <ArrowUpRight className="h-3 w-3" />
                </Link>
              </div>
              <div className="divide-y divide-gray-50">
                {q.data?.recentCampaigns.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-center gap-4 px-6 py-3.5 hover:bg-gray-50/60 transition-colors"
                  >
                    <div className="h-8 w-8 rounded-lg bg-indigo-50 flex items-center justify-center shrink-0">
                      <span className="text-indigo-600 text-xs font-bold">
                        {c.name.slice(0, 2).toUpperCase()}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">{c.name}</div>
                      <div className="text-xs text-gray-400">{fmtDate(c.created_at)}</div>
                    </div>
                    <div className="shrink-0">
                      <StatusBadge kind="campaign" value={c.status} />
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="text-sm font-semibold text-gray-900">
                        {c.stats?.emails_sent ?? 0}
                      </div>
                      <div className="text-xs text-gray-400">sent</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Performing Campaigns */}
            <div className="col-span-2 rounded-2xl bg-white border border-gray-100 shadow-sm">
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-50">
                <h2 className="text-sm font-semibold text-gray-900">Top Performers</h2>
                <Link
                  href="/campaigns"
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
                >
                  See All <ArrowUpRight className="h-3 w-3" />
                </Link>
              </div>
              <div className="divide-y divide-gray-50">
                {q.data?.topCampaigns.map((c, i) => (
                  <div
                    key={c.id}
                    className="flex items-center gap-4 px-6 py-3.5 hover:bg-gray-50/60 transition-colors"
                  >
                    <div className="h-9 w-9 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0 overflow-hidden">
                      <span className="text-xs font-bold text-gray-400">#{i + 1}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">{c.name}</div>
                      <div className="text-xs text-gray-400">
                        {c.stats?.meetings_booked ?? 0} meetings booked
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="text-sm font-bold text-indigo-600">
                        {fmtPct(c.stats?.reply_rate ?? 0)}
                      </div>
                      <div className="text-xs text-gray-400">reply rate</div>
                    </div>
                  </div>
                ))}
                {(q.data?.topCampaigns.length ?? 0) === 0 && (
                  <div className="px-6 py-8 text-center text-sm text-gray-400">
                    No data yet
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
