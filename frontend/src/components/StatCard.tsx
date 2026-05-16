import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

export default function StatCard({
  label,
  value,
  trend,
  className,
}: {
  label: string
  value: string | number
  trend?: { direction: "up" | "down" | "flat"; value: string }
  className?: string
}) {
  const tone =
    trend?.direction === "up"
      ? "text-emerald-700"
      : trend?.direction === "down"
        ? "text-rose-700"
        : "text-slate-600"

  return (
    <Card className={cn("shadow-sm", className)}>
      <CardContent className="p-4">
        <div className="text-xs text-slate-600">{label}</div>
        <div className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
          {value}
        </div>
        {trend ? (
          <div className={cn("mt-2 text-xs font-medium", tone)}>
            {trend.direction === "up"
              ? "▲"
              : trend.direction === "down"
                ? "▼"
                : "•"}{" "}
            {trend.value}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

