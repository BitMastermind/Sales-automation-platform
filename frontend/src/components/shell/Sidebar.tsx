"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  BarChart3,
  ChevronDown,
  LayoutDashboard,
  Mail,
  Settings,
  Sparkles,
  Target,
  Users,
} from "lucide-react"

import { cn } from "@/lib/utils"

type NavItem = {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  disabled?: boolean
}

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/campaigns", label: "Campaigns", icon: BarChart3 },
  { href: "/leads", label: "Leads", icon: Users },
  { href: "/templates", label: "Templates", icon: Sparkles },
  { href: "/integrations", label: "Integrations", icon: Mail },
  { href: "/settings", label: "Settings", icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside
      className="w-[240px] shrink-0 min-h-screen flex flex-col"
      style={{ backgroundColor: "#0d1117" }}
    >
      {/* Brand */}
      <div className="h-16 px-5 flex items-center gap-3 border-b border-white/5">
        <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
          <span className="text-white text-xs font-bold tracking-tight">SH</span>
        </div>
        <span className="font-semibold text-white tracking-tight">SalesHQ</span>
      </div>

      {/* Nav */}
      <nav className="px-3 py-4 flex flex-col gap-0.5 text-sm flex-1">
        {NAV.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname?.startsWith(`${item.href}/`))
          const Icon = item.icon

          if (item.disabled) {
            return (
              <div
                key={item.href}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-white/25 cursor-not-allowed select-none"
                aria-disabled
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </div>
            )
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 transition-all duration-150",
                active
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-900/40"
                  : "text-white/50 hover:text-white hover:bg-white/[0.06]",
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Monthly Goal */}
      <div
        className="mx-3 mb-3 rounded-xl border border-white/[0.08] p-4"
        style={{ backgroundColor: "rgba(255,255,255,0.04)" }}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-white/40">Monthly Goal</span>
          <Target className="h-3.5 w-3.5 text-white/25" />
        </div>
        <div className="text-sm font-semibold text-white">486 / 600 emails</div>
        <div className="text-xs text-white/35 mt-0.5 mb-3">81% of monthly target</div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "rgba(255,255,255,0.1)" }}>
          <div
            className="h-full rounded-full bg-indigo-500 transition-all"
            style={{ width: "81%" }}
          />
        </div>
      </div>

      {/* User */}
      <div className="px-3 pb-4">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2.5 hover:bg-white/[0.06] cursor-pointer transition-colors group">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center shrink-0">
            <span className="text-white text-xs font-semibold">AV</span>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-medium text-white/80 truncate">Ashit Verma</div>
            <div className="text-[11px] text-white/35 truncate">ashitverma56@gmail.com</div>
          </div>
          <ChevronDown className="h-3.5 w-3.5 text-white/25 shrink-0 group-hover:text-white/50 transition-colors" />
        </div>
      </div>
    </aside>
  )
}
