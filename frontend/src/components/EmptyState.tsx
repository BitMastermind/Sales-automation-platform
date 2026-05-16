import * as React from "react"
import { Inbox } from "lucide-react"

import { cn } from "@/lib/utils"

export default function EmptyState({
  title,
  description,
  action,
  icon,
  className,
}: {
  title: string
  description?: string
  action?: React.ReactNode
  icon?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center py-14 px-6",
        className,
      )}
    >
      <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600">
        {icon ?? <Inbox className="h-5 w-5" />}
      </div>
      <div className="mt-4 text-sm font-medium text-slate-900">{title}</div>
      {description ? (
        <div className="mt-1 text-sm text-slate-600 max-w-sm">
          {description}
        </div>
      ) : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  )
}

