# Phase 5A — Frontend Shell + Pages — Design Spec

**Date:** 2026-05-16
**Owner:** Phase 5 Frontend
**Source prompt:** [`docs/prompts/phase-5-frontend.md`](../../prompts/phase-5-frontend.md)
**Reference:** [`docs/06-FRONTEND.md`](../../06-FRONTEND.md)
**Supersedes (corrections):** the source prompt's Next.js 14 / Geist-via-google / unspecified open decisions

This document is the design of record for Phase 5A. The source prompt remains the user-intent narrative; this spec is what the implementation plan and code must conform to.

---

## 1. Scope

Build the frontend shell, four pages, shared components, and typed API client for the AI Sales Outreach Automation platform.

**In scope:**
- Sidebar layout + top header
- `/dashboard`, `/campaigns`, `/campaigns/[id]`, `/settings` pages
- Lead detail slide-out drawer
- Typed API client + TanStack Query data layer
- Shared UI primitives (`StatCard`, `StatusBadge`, `EmptyState`, `PageHeader`)

**Out of scope (deferred to Phase 5B):**
- Campaign creation modal (3-step flow)
- CSV upload + column mapping UI
- Reply detail / classification editing UI

---

## 2. Locked decisions

| Decision | Choice | Reason |
|---|---|---|
| Next.js version | **16 + React 19** | Matches actual scaffold. `frontend/AGENTS.md` requires reading `node_modules/next/dist/docs/` before non-trivial patterns. |
| Geist font | **`geist/font/sans` from `geist` npm package** | Geist is not on Google Fonts; `next/font/google` cannot serve it. |
| Dashboard data source | **Client-side aggregation of `GET /api/campaigns`** via TanStack Query `select` | No new backend endpoint needed; MVP scale (solo operator, few campaigns) tolerates it. |
| Lead drawer state | **URL search param `?lead=<id>`** on `/campaigns/[id]` | Shareable, refresh-safe, back-button closes drawer. Aligns with docs/06 rule: "If UI state survives a remount, it lives in URL params." |
| Server/client split | **Server `RootLayout`. Only `Sidebar` and the Gmail status pill island are `'use client'`** | Maximizes server rendering; `usePathname` + status fetch only need small client subtrees. |
| shadcn install | **Run `npx shadcn@latest add …` for the 13 components in §8 before building pages** | Components dir is currently empty. |

### 2.1 Known data gap (line chart)

The dashboard line chart requires "Emails Sent Per Day, last 30 days." `GET /api/campaigns` returns campaign rows + aggregate stats — there is no per-day breakdown.

**Decision:** stub the line chart in Phase 5A using `created_at`-bucketed campaign counts so the layout ships in its final form. File a follow-up to add `GET /api/stats/emails-daily` (Phase 5B or 6). The bucketing logic must be isolated in a single helper so swapping the data source later is a one-file change.

---

## 3. File tree

```
frontend/src
├── app/
│   ├── layout.tsx                # server, sidebar shell + header
│   ├── providers.tsx             # 'use client' QueryClientProvider
│   ├── dashboard/page.tsx        # stat cards + 2 charts
│   ├── campaigns/page.tsx        # campaigns table + pagination
│   ├── campaigns/[id]/page.tsx   # detail header + leads table + drawer
│   └── settings/page.tsx         # Gmail status + API key indicators
├── components/
│   ├── ui/                       # shadcn-generated primitives (§8)
│   ├── shell/
│   │   ├── Sidebar.tsx           # 'use client', usePathname for active state
│   │   └── HeaderGmailPill.tsx   # 'use client' island, fetches gmail status
│   ├── StatCard.tsx
│   ├── StatusBadge.tsx
│   ├── EmptyState.tsx
│   └── PageHeader.tsx
├── lib/
│   ├── types.ts                  # mirrors backend Pydantic schemas
│   ├── api.ts                    # 6 typed fetchers + envelope unwrap
│   └── utils.ts                  # existing
└── hooks/                        # reserved for Phase 5B; do not create empty dir
```

---

## 4. Data layer

### 4.1 `lib/types.ts`

TypeScript interfaces mirroring the backend Pydantic schemas. Required types:

- `Campaign` — list-row shape from `GET /api/campaigns`
- `CampaignDetail` — single-campaign shape with `stats`
- `Lead` — list-row shape from `GET /api/campaigns/{id}/leads`
- `LeadDetail` — single-lead shape with `emails[]` and `replies[]`
- `Email` — fields: `id`, `kind` (`"outreach" | "followup"`), `subject`, `body`, `sent_at`
- `Reply` — fields: `id`, `email_id`, `body`, `classification`, `received_at`
- `Meta` — pagination shape: `page`, `size`, `total`, `total_pages`
- `UploadResult` — fields per backend upload endpoint

The exact field names must be verified against `backend/app/schemas/` during implementation (do not invent fields).

### 4.2 `lib/api.ts`

```typescript
const BASE = process.env.NEXT_PUBLIC_API_BASE!;

class ApiError extends Error {
  constructor(public code: string, message: string) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<{ data: T; meta?: Meta }> {
  const res = await fetch(`${BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
  const env = await res.json();
  if (env.error) throw new ApiError(env.error.code, env.error.message);
  return { data: env.data, meta: env.meta };
}

export function fetchCampaigns(page: number, size: number): Promise<{ data: Campaign[]; meta: Meta }>;
export function fetchCampaign(id: string): Promise<{ data: CampaignDetail }>;
export function patchCampaignStatus(id: string, status: string): Promise<void>;
export function uploadLeads(campaignId: string, file: File): Promise<UploadResult>;
export function fetchLeads(campaignId: string, page: number): Promise<{ data: Lead[]; meta: Meta }>;
export function fetchLead(id: string): Promise<{ data: LeadDetail }>;
```

`uploadLeads` uses `FormData` and must NOT set `Content-Type` (browser sets multipart boundary).

### 4.3 Query keys (per docs/06)

| Hook | Key | Notes |
|---|---|---|
| Campaigns list | `["campaigns", { page, size }]` | |
| Campaign detail | `["campaign", id]` | |
| Leads list | `["leads", campaignId, { page }]` | |
| Lead detail | `["lead", id]` | Fetched only when drawer is open |
| Dashboard stats | `["dashboard-stats"]` | Derived via `useQuery({ queryKey: ["campaigns", { page: 1, size: 100 }], select: aggregateDashboardStats })` |
| Gmail status | `["gmail-status"]` | |

Mutations invalidate the relevant queries; no optimistic updates.

---

## 5. Layout shell

### 5.1 `app/providers.tsx` ('use client')

Wraps `QueryClientProvider` with a singleton `QueryClient` (defaults: `staleTime: 30_000`, `refetchOnWindowFocus: false`). Must be a separate client component to keep `RootLayout` server-side.

### 5.2 `app/layout.tsx` (server)

- `geist/font/sans` applied to `<body>`.
- Renders `<Providers>{children + chrome}</Providers>`.
- Layout chrome:
  - Left sidebar: `<Sidebar />` (client component).
  - Top header: breadcrumb (server, derived from segment) + `<HeaderGmailPill />` (client island).
  - Main area: `slate-50` background, generous padding.

### 5.3 `components/shell/Sidebar.tsx` ('use client')

- Fixed left, ~240px wide, `slate-900` background.
- Nav items (in order, with `lucide-react` icons): Dashboard, Campaigns, Leads, Templates, Integrations, Settings.
- "Leads", "Templates", "Integrations" are link-only stubs in Phase 5A (route exists or 404 acceptable; flag as Phase 5B).
- Uses `usePathname()` to highlight active item: white text + subtle accent stripe.
- All nav items use Next.js `<Link>` (not `router.push`) for prefetching.

### 5.4 `components/shell/HeaderGmailPill.tsx` ('use client')

- `useQuery(["gmail-status"])` → green pill + email if connected, red pill + "Not connected" otherwise.
- Renders nothing while loading (no skeleton — small surface).

---

## 6. Pages

### 6.1 `/dashboard`

- 5 `StatCard`s in a responsive grid: Total Leads, Emails Sent, Open Rate, Reply Rate, Meetings Booked. Big number + label + trend indicator (trend may be `null` for Phase 5A — show only if backend provides).
- Two charts in a 60/40 horizontal split:
  - **Line chart** (60%): Emails Sent Per Day, last 30 days. `Recharts LineChart`. Stub data per §2.1.
  - **Bar chart** (40%): Reply Rate by Campaign. `Recharts BarChart`, green bars, top 10 campaigns, names truncated to 12 chars.
- Both charts live in a parent `div` with `style={{ height: 320 }}` and the chart in a `ResponsiveContainer` — explicitly avoiding the 0px-render bug from the source prompt.
- Empty state: muted icon + "No campaigns yet. Create your first one." + button (button is no-op stub for Phase 5A).
- All data via `useQuery(["dashboard-stats"])` deriving from `["campaigns", { page: 1, size: 100 }]`.

### 6.2 `/campaigns`

- shadcn `Table`. Columns: Name, Status (badge), Leads, Sent, Opened %, Replied %, Created.
- `StatusBadge` colors: `draft=gray`, `active=green`, `paused=amber`, `completed=blue`.
- Row click → `<Link>` to `/campaigns/[id]`.
- Row 3-dot menu (shadcn `DropdownMenu`): View, Pause/Resume, Archive.
  - Pause/Resume calls `patchCampaignStatus`. Archive is a stub (alert + TODO comment) if backend doesn't yet support it.
- Top right: "New Campaign" button — no-op stub in Phase 5A; opens modal in Phase 5B.
- Loading: 3 skeleton rows. Empty state: centered `EmptyState` with CTA.
- Bottom pagination derived from `meta.total_pages`.

### 6.3 `/campaigns/[id]`

**Header:**
- Campaign name + `StatusBadge` + 5 inline stats + "Launched [date]" + Pause/Resume button.

**Leads table:**
- Columns: Company, Contact, Email, Status (badge), Last Touched, Actions.
- Lead status badges: `new=gray`, `researched=blue`, `email_sent=purple`, `replied=amber`, `meeting_booked=green`, `unsubscribed=slate`.
- Row click → `router.replace('?lead=<id>')` (no scroll jump).

**Drawer (slide-out shadcn `Sheet`):**
- A small client subtree on the page reads `useSearchParams().get("lead")`. When set, opens the `Sheet` and fires `useQuery(["lead", id])`.
- Sheet contents:
  - Title: company + contact name.
  - Timeline of email thread (oldest first). Each email row:
    - Tag chip: Outreach (purple) / Follow-up (blue).
    - Date.
    - Subject in bold.
    - Body, 3-line truncate, expandable on click.
  - Replies appear inline immediately below their parent email with `bg-slate-50`, classification badge.
  - "Research in progress…" placeholder if no emails yet.
- Closing the Sheet (X, Esc, overlay click) calls `router.replace(pathname)` to clear the param.

### 6.4 `/settings`

- **Gmail section:**
  - `useQuery(["gmail-status"])`. Connected → green pill + email. Not connected → red pill + "Connect Gmail" button hitting `GET /api/auth/gmail` (full page nav).
  - On mount, if `useSearchParams().get("gmail") === "connected"`, fire a one-time shadcn `Toast` ("Gmail connected").
- **API Keys section:**
  - Reads from a `GET /api/settings/integrations-status` endpoint returning `{ tavily: bool, firecrawl: bool, openai: bool, anthropic: bool, slack: bool }`. Render green/red dot per key. Never display values. If the endpoint does not yet exist, render a placeholder card with a TODO comment and flag it in the implementation plan as a backend prerequisite.

---

## 7. Shared components

| Component | Props | Purpose |
|---|---|---|
| `StatCard` | `label`, `value`, `trend?: { value: number; direction: "up" \| "down" }` | Metric tile on dashboard + campaign detail |
| `StatusBadge` | `status: string`, `kind: "campaign" \| "lead"` | Color map driven by `kind` + `status` |
| `EmptyState` | `icon`, `message`, `cta?: { label, onClick }` | Centered empty state |
| `PageHeader` | `title`, `subtitle?`, `action?: ReactNode` | Page-top title row |

All functional components, no class components. No `console.log` in committed code.

---

## 8. shadcn components to install

One-time setup before page work:

1. If `frontend/components.json` is missing: `npx shadcn@latest init` → Default style, slate base, CSS variables.
2. `npx shadcn@latest add button table card badge sheet skeleton dropdown-menu sonner avatar separator input label tabs`

(`sonner` replaces deprecated `toast`. `tabs` reserved for Phase 5B but cheap to install now.)

---

## 9. Coding rules (project-wide, restated)

- Functional components only.
- All data fetching via TanStack Query — no raw `fetch` in components.
- No Redux / Zustand / React Context for server data.
- Desktop only — no mobile responsive work.
- No `console.log` in committed code.
- No animations beyond what shadcn ships.
- `NEXT_PUBLIC_API_BASE` is the only allowed base URL source.
- Read `node_modules/next/dist/docs/` before any non-trivial Next 16 pattern (App Router conventions, fonts, fetch caching, server actions).

---

## 10. Verification

```bash
cd frontend
npm install geist                                                              # if not installed
npx shadcn@latest init                                                         # only if components.json missing
npx shadcn@latest add button table card badge sheet skeleton dropdown-menu sonner avatar separator input label tabs
npm run build                                                                   # zero TS errors
npm run dev                                                                     # localhost:3000
```

**Manual checks (all 5 must pass):**
1. Sidebar active state changes correctly on every nav click.
2. Header Gmail pill renders (connected or not).
3. `/dashboard` loads with both charts at non-zero height.
4. `/campaigns` row click navigates to `/campaigns/[id]`.
5. On `/campaigns/[id]`, lead row click opens drawer with `?lead=<id>` in URL; refreshing the page keeps the drawer open; closing the drawer clears the param.

---

## 11. Out-of-scope follow-ups (file as Phase 5B / Phase 6 issues)

- Campaign creation modal (3-step flow + CSV upload) — Phase 5B.
- `GET /api/stats/emails-daily` endpoint to replace dashboard line chart stub.
- `GET /api/settings/integrations-status` endpoint (if not present).
- Archive action wiring (if backend doesn't support yet).
- `/leads`, `/templates`, `/integrations` pages — Phase 5B.
