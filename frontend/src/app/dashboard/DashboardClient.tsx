"use client"

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import {
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

import { fetchCampaigns } from "@/lib/api"
import type { Campaign } from "@/lib/types"

import EmptyState from "@/components/EmptyState"
import PageHeader from "@/components/PageHeader"
import StatCard from "@/components/StatCard"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

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
  const emailsSentPerDay = days.map((d) => ({ day: d.slice(5), sent: byDay.get(d) ?? 0 }))

  const replyRateByCampaign = [...campaigns]
    .filter((c) => (c.stats?.emails_sent ?? 0) > 0)
    .sort((a, b) => (b.stats?.reply_rate ?? 0) - (a.stats?.reply_rate ?? 0))
    .slice(0, 10)
    .map((c) => ({
      name: c.name.length > 12 ? `${c.name.slice(0, 12)}…` : c.name,
      rate: Math.round((c.stats?.reply_rate ?? 0) * 100),
    }))

  return {
    totals: {
      leads: totals.leads,
      sent: totals.sent,
      openRate,
      replyRate,
      meetings: totals.meetings,
    },
    emailsSentPerDay,
    replyRateByCampaign,
  }
}

export default function DashboardClient() {
  const q = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => fetchCampaigns(1, 200),
    select: (res) => deriveDashboard(res.data),
  })

  const hasCampaigns = (q.data?.totals.leads ?? 0) > 0 || (q.data?.totals.sent ?? 0) > 0
  const empty = q.isSuccess && !hasCampaigns

  const statCards = useMemo(() => {
    const t = q.data?.totals
    return [
      { label: "Total Leads", value: t?.leads ?? "—" },
      { label: "Emails Sent", value: t?.sent ?? "—" },
      { label: "Open Rate", value: t ? fmtPct(t.openRate) : "—" },
      { label: "Reply Rate", value: t ? fmtPct(t.replyRate) : "—" },
      { label: "Meetings Booked", value: t?.meetings ?? "—" },
    ]
  }, [q.data?.totals])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Campaign performance overview"
        action={<Button disabled>New Campaign</Button>}
      />

      {empty ? (
        <Card className="shadow-sm">
          <CardContent className="p-0">
            <EmptyState
              title="No campaigns yet. Create your first one."
              description="Once you launch a campaign, stats and charts will show up here."
              action={<Button disabled>Create Campaign</Button>}
            />
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-5 gap-4">
            {statCards.map((s) => (
              <StatCard key={s.label} label={s.label} value={s.value} />
            ))}
          </div>

          <div className="grid grid-cols-5 gap-4">
            <Card className="col-span-3 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-slate-900">
                  Emails Sent Per Day
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={q.data?.emailsSentPerDay ?? []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="sent"
                        stroke="#0f172a"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="col-span-2 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-slate-900">
                  Reply Rate by Campaign
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[320px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={q.data?.replyRateByCampaign ?? []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} interval={0} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="rate" fill="#16a34a" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

