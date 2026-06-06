import { ArrowUpRight } from "lucide-react"

import { cn } from "@/lib/utils"

export default function StatCard({
  label,
  value,
  trend,
  hero,
  className,
}: {
  label: string
  value: string | number
  trend?: { direction: "up" | "down" | "flat"; value: string }
  hero?: boolean
  className?: string
}) {
  if (hero) {
    return (
      <div
        className={cn(
          "rounded-2xl p-5 text-white relative overflow-hidden",
          "bg-gradient-to-br from-indigo-500 via-indigo-600 to-violet-600 shadow-lg shadow-indigo-200",
          className,
        )}
      >
        <div className="absolute -top-6 -right-6 h-28 w-28 rounded-full bg-white/10" />
        <div className="absolute bottom-0 right-6 h-16 w-16 translate-y-4 rounded-full bg-white/[0.06]" />

        <div className="relative">
          <div className="flex items-start justify-between">
            <div className="text-sm font-medium text-indigo-100">{label}</div>
            <div className="h-8 w-8 rounded-lg bg-white/20 flex items-center justify-center">
              <ArrowUpRight className="h-4 w-4 text-white" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-bold tracking-tight">{value}</div>
          {trend ? (
            <div className="mt-2.5 inline-flex items-center gap-1 rounded-full bg-white/20 px-2.5 py-1 text-xs font-medium text-white/90">
              {trend.direction === "up" ? "+" : trend.direction === "down" ? "−" : ""}
              {trend.value} from last month
            </div>
          ) : (
            <div className="mt-2.5 text-xs text-indigo-200">From last month</div>
          )}
        </div>
      </div>
    )
  }

  const trendClass =
    trend?.direction === "up"
      ? "text-emerald-600 bg-emerald-50 border border-emerald-100"
      : trend?.direction === "down"
        ? "text-rose-600 bg-rose-50 border border-rose-100"
        : "text-gray-500 bg-gray-50 border border-gray-100"

  const trendArrow =
    trend?.direction === "up" ? "↑" : trend?.direction === "down" ? "↓" : "•"

  return (
    <div
      className={cn(
        "rounded-2xl bg-white border border-gray-100 p-5 shadow-sm hover:shadow-md transition-shadow",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div className="text-sm font-medium text-gray-500">{label}</div>
        <div className="h-8 w-8 rounded-lg bg-gray-50 flex items-center justify-center">
          <ArrowUpRight className="h-4 w-4 text-gray-400" />
        </div>
      </div>
      <div className="mt-3 text-3xl font-bold tracking-tight text-gray-900">
        {value}
      </div>
      {trend ? (
        <div
          className={cn(
            "mt-2.5 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
            trendClass,
          )}
        >
          {trendArrow} {trend.value}
        </div>
      ) : (
        <div className="mt-2.5 text-xs text-gray-400">From last month</div>
      )}
    </div>
  )
}
