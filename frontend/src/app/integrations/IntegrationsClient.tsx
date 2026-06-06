"use client"

import { useQuery } from "@tanstack/react-query"
import {
  CheckCircle2,
  Circle,
  ExternalLink,
  Lock,
  Plug,
  Unplug,
} from "lucide-react"

import { fetchIntegrations } from "@/lib/api"
import type { Integration } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const CATEGORY_META: Record<string, { label: string; description: string }> = {
  email: {
    label: "Email",
    description: "Send and track outbound emails through your own inbox.",
  },
  crm: {
    label: "CRM",
    description: "Keep your CRM in sync — contacts, deals, and activity auto-logged.",
  },
  enrichment: {
    label: "Enrichment",
    description: "Power the research agent with real-time web data and company signals.",
  },
  automation: {
    label: "Automation",
    description: "Trigger workflows, alerts, and data pipelines across your stack.",
  },
}

const CATEGORY_ORDER = ["email", "crm", "enrichment", "automation"]

const INTEGRATION_ICONS: Record<string, React.ReactNode> = {
  "int-gmail": (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none">
      <path d="M22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6z" fill="#EA4335" opacity=".15"/>
      <path d="M22 6L12 13 2 6" stroke="#EA4335" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M2 6l10 7 10-7" fill="none" stroke="#EA4335" strokeWidth="1.5"/>
      <rect x="2" y="6" width="20" height="12" rx="2" stroke="#EA4335" strokeWidth="1.5" fill="none"/>
    </svg>
  ),
  "int-hubspot": (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none">
      <circle cx="12" cy="12" r="10" fill="#FF7A59" opacity=".15"/>
      <path d="M9 9.5C9 8.12 10.12 7 11.5 7S14 8.12 14 9.5c0 1.18-.8 2.17-1.9 2.45V14h-1.2v-2.05C9.8 11.67 9 10.68 9 9.5z" fill="#FF7A59"/>
      <circle cx="12" cy="17" r="1.5" fill="#FF7A59"/>
    </svg>
  ),
  "int-slack": (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none">
      <rect x="2" y="2" width="20" height="20" rx="5" fill="#4A154B" opacity=".1"/>
      <path d="M8.5 14.5a1.5 1.5 0 01-3 0 1.5 1.5 0 013 0zm0-5a1.5 1.5 0 01-3 0 1.5 1.5 0 013 0z" fill="#E01E5A"/>
      <path d="M15.5 14.5a1.5 1.5 0 01-3 0v-5a1.5 1.5 0 013 0v5z" fill="#2EB67D"/>
      <path d="M9.5 9.5a1.5 1.5 0 010-3h5a1.5 1.5 0 010 3h-5z" fill="#ECB22E"/>
      <path d="M9.5 15.5a1.5 1.5 0 010-3h5a1.5 1.5 0 010 3h-5z" fill="#36C5F0"/>
    </svg>
  ),
  "int-sheets": (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="3" fill="#0F9D58" opacity=".15"/>
      <rect x="3" y="3" width="18" height="18" rx="3" stroke="#0F9D58" strokeWidth="1.5" fill="none"/>
      <path d="M3 9h18M3 15h18M9 9v6M15 9v6" stroke="#0F9D58" strokeWidth="1.5"/>
    </svg>
  ),
  "int-tavily": (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none">
      <circle cx="12" cy="12" r="10" fill="#6366f1" opacity=".15"/>
      <circle cx="12" cy="12" r="10" stroke="#6366f1" strokeWidth="1.5" fill="none"/>
      <path d="M8 12l3 3 5-5" stroke="#6366f1" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  "int-firecrawl": (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none">
      <circle cx="12" cy="12" r="10" fill="#f97316" opacity=".15"/>
      <path d="M12 3c0 0-5 4-5 9a5 5 0 0010 0c0-2-1-4-2-5 0 2-1 3-3 3s-2-2-2-3c0 0 0 2 2 2z" fill="#f97316" opacity=".8"/>
    </svg>
  ),
  "int-salesforce": (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none">
      <ellipse cx="12" cy="12" rx="10" ry="8" fill="#00A1E0" opacity=".15"/>
      <ellipse cx="12" cy="12" rx="10" ry="8" stroke="#00A1E0" strokeWidth="1.5" fill="none"/>
      <path d="M8 12h8M12 8v8" stroke="#00A1E0" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "2-digit", year: "numeric" })
}

function IntegrationCard({ integration }: { integration: Integration }) {
  const isConnected = integration.status === "connected"
  const isComingSoon = integration.status === "coming_soon"
  const icon = INTEGRATION_ICONS[integration.id]

  return (
    <div
      className={cn(
        "rounded-2xl bg-white border shadow-sm transition-all duration-200 flex flex-col overflow-hidden",
        isConnected
          ? "border-emerald-200 shadow-emerald-100/60"
          : isComingSoon
          ? "border-gray-100 opacity-60"
          : "border-gray-100 hover:border-gray-200 hover:shadow-md",
      )}
    >
      <div className="p-5 flex items-start gap-4 flex-1">
        {/* Icon */}
        <div
          className={cn(
            "h-12 w-12 rounded-xl flex items-center justify-center shrink-0 border",
            isConnected ? "border-emerald-200 bg-emerald-50" : "border-gray-100 bg-gray-50",
          )}
        >
          {icon ?? <Plug className="h-5 w-5 text-gray-400" />}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-900">{integration.name}</h3>
            {isConnected && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                <CheckCircle2 className="h-3 w-3" />
                Connected
              </span>
            )}
            {isComingSoon && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                <Lock className="h-3 w-3" />
                Coming Soon
              </span>
            )}
            {!isConnected && !isComingSoon && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-gray-400 bg-gray-50 border border-gray-200 px-2 py-0.5 rounded-full">
                <Circle className="h-3 w-3" />
                Not connected
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">{integration.description}</p>

          {isConnected && integration.connected_email && (
            <div className="mt-2 flex items-center gap-1.5 text-xs text-emerald-600">
              <CheckCircle2 className="h-3 w-3" />
              <span className="font-medium">{integration.connected_email}</span>
            </div>
          )}
          {isConnected && integration.connected_at && !integration.connected_email && (
            <div className="mt-2 text-xs text-gray-400">
              Connected {fmtDate(integration.connected_at)}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-5 pb-4 flex items-center justify-between">
        <div />
        {isConnected ? (
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl text-rose-500 border-rose-200 hover:bg-rose-50 hover:border-rose-300 gap-1.5 text-xs"
          >
            <Unplug className="h-3.5 w-3.5" />
            Disconnect
          </Button>
        ) : isComingSoon ? (
          <Button
            variant="outline"
            size="sm"
            disabled
            className="rounded-xl text-gray-400 border-gray-200 text-xs cursor-not-allowed"
          >
            Coming Soon
          </Button>
        ) : (
          <Button
            size="sm"
            className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5 text-xs shadow-sm shadow-indigo-200"
          >
            <Plug className="h-3.5 w-3.5" />
            Connect
          </Button>
        )}
      </div>
    </div>
  )
}

function SectionSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-5 w-32" />
      <div className="grid grid-cols-2 gap-4">
        {[1, 2].map((i) => (
          <div key={i} className="rounded-2xl bg-white border border-gray-100 p-5 space-y-3">
            <div className="flex gap-4">
              <Skeleton className="h-12 w-12 rounded-xl shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-3/4" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function IntegrationsClient() {
  const q = useQuery({
    queryKey: ["integrations"],
    queryFn: fetchIntegrations,
  })

  const integrations = q.data ?? []

  const byCategory = CATEGORY_ORDER.reduce(
    (acc, cat) => {
      acc[cat] = integrations.filter((i) => i.category === cat)
      return acc
    },
    {} as Record<string, Integration[]>,
  )

  const connectedCount = integrations.filter((i) => i.status === "connected").length

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Integrations</h1>
          <p className="mt-1 text-sm text-gray-400">
            Connect your tools to power automated research, sending, and CRM sync
          </p>
        </div>
        {!q.isLoading && (
          <div className="flex items-center gap-2 rounded-xl bg-white border border-gray-100 shadow-sm px-4 py-2.5">
            <div className="flex -space-x-1">
              {integrations
                .filter((i) => i.status === "connected")
                .slice(0, 3)
                .map((i) => (
                  <div
                    key={i.id}
                    className="h-6 w-6 rounded-full bg-emerald-100 border-2 border-white flex items-center justify-center"
                  >
                    <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                  </div>
                ))}
            </div>
            <span className="text-sm font-medium text-gray-700">
              {connectedCount} connected
            </span>
          </div>
        )}
      </div>

      {/* Sections */}
      {q.isLoading ? (
        <div className="space-y-8">
          <SectionSkeleton />
          <SectionSkeleton />
        </div>
      ) : (
        CATEGORY_ORDER.map((cat) => {
          const items = byCategory[cat]
          if (!items || items.length === 0) return null
          const { label, description } = CATEGORY_META[cat]
          return (
            <section key={cat} className="space-y-3">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">{label}</h2>
                <p className="text-xs text-gray-400 mt-0.5">{description}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {items.map((integration) => (
                  <IntegrationCard key={integration.id} integration={integration} />
                ))}
              </div>
            </section>
          )
        })
      )}

      {/* Docs link */}
      <div className="rounded-2xl bg-gradient-to-r from-indigo-50 to-violet-50 border border-indigo-100 p-5 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Need a custom integration?</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            All integrations are powered by n8n workflows — you can extend them or add new ones.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="rounded-xl border-indigo-200 text-indigo-600 hover:bg-indigo-50 gap-1.5 text-xs shrink-0"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          View n8n Docs
        </Button>
      </div>
    </div>
  )
}
