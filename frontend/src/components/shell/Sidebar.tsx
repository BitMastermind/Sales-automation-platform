"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  BarChart3,
  LayoutDashboard,
  Mail,
  Settings,
  Sparkles,
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
  { href: "/leads", label: "Leads", icon: Users, disabled: true },
  { href: "/templates", label: "Templates", icon: Sparkles, disabled: true },
  { href: "/integrations", label: "Integrations", icon: Mail, disabled: true },
  { href: "/settings", label: "Settings", icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-[240px] bg-slate-900 text-slate-200 shrink-0 min-h-screen flex flex-col border-r border-slate-800">
      <div className="h-14 px-5 flex items-center border-b border-slate-800">
        <div className="font-semibold tracking-tight text-white">SalesHQ</div>
      </div>
      <nav className="px-3 py-4 flex flex-col gap-1 text-sm">
        {NAV.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname?.startsWith(`${item.href}/`))
          const Icon = item.icon
          const base =
            "flex items-center gap-2 rounded-md px-3 py-2 transition-colors"
          if (item.disabled) {
            return (
              <div
                key={item.href}
                className={cn(base, "text-slate-500 cursor-not-allowed")}
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
                base,
                active
                  ? "bg-slate-800 text-white"
                  : "text-slate-300 hover:bg-slate-800/60 hover:text-white",
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>
      <div className="mt-auto px-5 py-4 text-xs text-slate-500">
        v0.1 • Desktop MVP
      </div>
    </aside>
  )
}

