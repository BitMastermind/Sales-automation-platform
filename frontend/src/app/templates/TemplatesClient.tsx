"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  Sparkles,
  Copy,
  Eye,
  Trash2,
  Plus,
  X,
  Tag,
  BarChart2,
  Zap,
  RefreshCw,
  Mail,
} from "lucide-react"

import { fetchTemplates } from "@/lib/api"
import type { Template, TemplateType } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const TYPE_TABS: { value: "" | TemplateType; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { value: "", label: "All", icon: Mail },
  { value: "intro", label: "Intro", icon: Zap },
  { value: "followup", label: "Follow-up", icon: RefreshCw },
  { value: "re_engagement", label: "Re-engagement", icon: Sparkles },
]

const TYPE_META: Record<string, { label: string; bg: string; text: string }> = {
  intro: { label: "Intro", bg: "bg-indigo-50", text: "text-indigo-600" },
  followup: { label: "Follow-up", bg: "bg-sky-50", text: "text-sky-600" },
  re_engagement: { label: "Re-engagement", bg: "bg-violet-50", text: "text-violet-600" },
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "2-digit", year: "numeric" })
}

function TemplateCard({
  template,
  onPreview,
}: {
  template: Template
  onPreview: (t: Template) => void
}) {
  const meta = TYPE_META[template.type] ?? TYPE_META.intro
  const bodyPreview = template.body.slice(0, 120).replace(/\n/g, " ") + "…"

  return (
    <div className="group rounded-2xl bg-white border border-gray-100 shadow-sm hover:shadow-md hover:border-gray-200 transition-all duration-200 flex flex-col overflow-hidden">
      {/* Top accent bar */}
      <div
        className={cn(
          "h-1 w-full",
          template.type === "intro" && "bg-gradient-to-r from-indigo-500 to-violet-500",
          template.type === "followup" && "bg-gradient-to-r from-sky-500 to-cyan-400",
          template.type === "re_engagement" && "bg-gradient-to-r from-violet-500 to-pink-500",
        )}
      />

      <div className="p-5 flex flex-col gap-3 flex-1">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={cn("text-[11px] font-semibold px-2 py-0.5 rounded-full", meta.bg, meta.text)}>
                {meta.label}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-gray-900 leading-snug">{template.name}</h3>
          </div>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            <button
              onClick={() => onPreview(template)}
              className="h-7 w-7 rounded-lg flex items-center justify-center text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
              title="Preview"
            >
              <Eye className="h-3.5 w-3.5" />
            </button>
            <button
              className="h-7 w-7 rounded-lg flex items-center justify-center text-gray-400 hover:text-sky-600 hover:bg-sky-50 transition-colors"
              title="Duplicate"
            >
              <Copy className="h-3.5 w-3.5" />
            </button>
            <button
              className="h-7 w-7 rounded-lg flex items-center justify-center text-gray-400 hover:text-rose-500 hover:bg-rose-50 transition-colors"
              title="Delete"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Subject */}
        <div className="rounded-xl bg-gray-50 px-3 py-2">
          <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-0.5">Subject</div>
          <div className="text-xs text-gray-700 font-medium truncate">{template.subject}</div>
        </div>

        {/* Body preview */}
        <p className="text-xs text-gray-500 leading-relaxed flex-1">{bodyPreview}</p>

        {/* Tags */}
        {template.tags.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <Tag className="h-3 w-3 text-gray-300 shrink-0" />
            {template.tags.map((tag) => (
              <span key={tag} className="text-[10px] font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <BarChart2 className="h-3.5 w-3.5" />
          <span>Used {template.used_count}×</span>
        </div>
        <span className="text-xs text-gray-400">{fmtDate(template.created_at)}</span>
      </div>
    </div>
  )
}

function PreviewModal({ template, onClose }: { template: Template; onClose: () => void }) {
  const meta = TYPE_META[template.type] ?? TYPE_META.intro

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)" }}
    >
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <span className={cn("text-xs font-semibold px-2.5 py-1 rounded-full", meta.bg, meta.text)}>
              {meta.label}
            </span>
            <h2 className="text-sm font-semibold text-gray-900">{template.name}</h2>
          </div>
          <button
            onClick={onClose}
            className="h-8 w-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Subject */}
        <div className="px-6 pt-4 pb-3 border-b border-gray-100">
          <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Subject line</div>
          <div className="text-sm font-medium text-gray-900">{template.subject}</div>
        </div>

        {/* Body */}
        <div className="px-6 py-4 max-h-80 overflow-y-auto">
          <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-2">Body</div>
          <pre className="text-sm text-gray-700 font-sans whitespace-pre-wrap leading-relaxed">{template.body}</pre>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50/50">
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className="font-medium text-indigo-600">{"{{variable}}"}</span>
            <span>= auto-filled by research agent</span>
          </div>
          <Button
            size="sm"
            className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white gap-2"
          >
            <Copy className="h-3.5 w-3.5" />
            Duplicate
          </Button>
        </div>
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl bg-white border border-gray-100 shadow-sm p-5 space-y-3">
      <Skeleton className="h-4 w-16 rounded-full" />
      <Skeleton className="h-4 w-48" />
      <Skeleton className="h-12 w-full rounded-xl" />
      <Skeleton className="h-10 w-full" />
      <div className="flex gap-1.5">
        <Skeleton className="h-4 w-14 rounded-full" />
        <Skeleton className="h-4 w-14 rounded-full" />
      </div>
    </div>
  )
}

export default function TemplatesClient() {
  const [activeTab, setActiveTab] = useState<"" | TemplateType>("")
  const [preview, setPreview] = useState<Template | null>(null)

  const q = useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
  })

  const templates = q.data ?? []

  const filtered = activeTab ? templates.filter((t) => t.type === activeTab) : templates

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Templates</h1>
          <p className="mt-1 text-sm text-gray-400">
            AI-generated email templates — personalized per lead at send time
          </p>
        </div>
        <Button className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-200 gap-2">
          <Plus className="h-4 w-4" />
          New Template
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-xl w-fit">
        {TYPE_TABS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            onClick={() => setActiveTab(value)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150",
              activeTab === value
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
            {value !== "" && (
              <span
                className={cn(
                  "text-[10px] font-bold ml-0.5 px-1.5 py-0.5 rounded-full",
                  activeTab === value ? "bg-indigo-100 text-indigo-600" : "bg-gray-200 text-gray-500",
                )}
              >
                {templates.filter((t) => t.type === value).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-3 gap-4">
        {q.isLoading
          ? Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
          : filtered.map((t) => (
              <TemplateCard key={t.id} template={t} onPreview={setPreview} />
            ))}

        {!q.isLoading && filtered.length === 0 && (
          <div className="col-span-3 rounded-2xl bg-white border border-gray-100 shadow-sm py-20 text-center">
            <Sparkles className="h-8 w-8 text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-400">No templates in this category yet.</p>
          </div>
        )}
      </div>

      {preview && <PreviewModal template={preview} onClose={() => setPreview(null)} />}
    </div>
  )
}
