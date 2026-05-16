# Phase 5 — Next.js Frontend

> Build a SaaS dashboard — not a chatbot. Two sub-sessions. Use the frontend-design skill.

---

## Session Setup

| | |
|---|---|
| **Depends on** | Phase 2 complete (FastAPI running, `/api/campaigns` returns data). Phase 0 complete (Next.js initialized with shadcn/ui). |
| **Estimated time** | 2–3 hours across 2–3 sub-sessions |

> The goal is a polished, production-feel SaaS dashboard — not generic AI output.

### Phase 5A routing — Hybrid (Claude Code first, then Codex)

5A spans many components and pages. Split it into two passes to get design quality AND breadth:

| Pass | Agent | Model | What to do |
|------|-------|-------|------------|
| **5A-Pass-1** | **Claude Code** | `claude-opus-4-7` | Design the sidebar layout shell + the Dashboard page only. Invoke `/skill frontend-design` first. Get the design pattern right on one page before replicating. |
| **5A-Pass-2** | **Codex** | n/a | Paste the Phase 5A prompt below. Codex uses the first page as the established pattern and scaffolds the remaining 3 pages (Leads, Campaigns, Settings) + shared components. |

### Phase 5B routing — Claude Code

| | |
|---|---|
| **Agent** | **Claude Code** |
| **Model** | `claude-opus-4-7` |
| **Skills** | Invoke `brainstorming` first, then `frontend-design`. |

---

## Phase 5A — Dashboard Layout + Pages

---

#### ROLE & PERSONA

You are a senior frontend engineer with a strong design eye, specializing in Next.js 14 App Router, TanStack Query, shadcn/ui, and Recharts. You have built production B2B SaaS dashboards that prioritize clarity, hierarchy, and data density over decoration.

---

#### TASK & OBJECTIVE

Build the full frontend shell (sidebar layout, 4 pages, shared components, typed API client) for the AI Sales Outreach Automation platform — achieving zero TypeScript errors and all 5 manual navigation/render checks passing.

---

#### MY SITUATION

Phase 0 initialized Next.js 14 with TypeScript, Tailwind, App Router, `src/` dir, and shadcn/ui (Default style, slate base, CSS variables). TanStack Query, Recharts, and react-dropzone are installed. The FastAPI backend is at `http://localhost:8000`. The layout shell at `/frontend/src/app/layout.tsx` exists as a basic placeholder.

---

#### CONSTRAINTS

- **All data fetching through TanStack Query** — no raw `fetch()` in components.
- **No class components.** No Redux, no Zustand, no React Context for server data.
- **Desktop only for MVP** — do not make the layout responsive for mobile.
- **No `console.log`** anywhere in committed code.
- **No animations** unless shadcn/ui provides them out of the box.
- `NEXT_PUBLIC_API_BASE` is the only allowed base URL source — always read from `process.env`.

---

#### AUDIENCE FOR THE OUTPUT

This frontend is used by a solo operator or small sales team who monitors campaign performance, uploads lead CSVs, and checks reply status daily. Clarity and information density matter more than visual complexity. The campaign detail drawer is the most-used view after launch.

---

#### PRIOR ATTEMPTS / WHAT FAILED

- Do not use `response_model=` patterns from the backend in the frontend types — model the `{ data, error, meta }` envelope in `api.ts` and unwrap it before returning to consumers.
- Do not put Recharts `ResponsiveContainer` inside a flex parent without an explicit `height` — it will render at 0px.
- Do not use `useRouter().push()` for the sidebar nav — use Next.js `<Link>` for prefetching.
- Do not add the `QueryClientProvider` directly in `layout.tsx` — it must be in a separate `"use client"` component (`providers.tsx`) to avoid server component conflicts.

---

#### FORMAT

Deliver files in this order:
1. `/frontend/src/lib/types.ts` — all TypeScript interfaces
2. `/frontend/src/lib/api.ts` — typed API client with 6 exported functions
3. `/frontend/src/app/providers.tsx` — `QueryClientProvider` wrapper
4. `/frontend/src/app/layout.tsx` — sidebar shell + top header
5. `/frontend/src/app/dashboard/page.tsx` — stat cards + charts
6. `/frontend/src/app/campaigns/page.tsx` — campaigns table + pagination
7. `/frontend/src/app/campaigns/[id]/page.tsx` — campaign detail + lead table + slide-out drawer
8. `/frontend/src/app/settings/page.tsx` — Gmail integration + API key status
9. `/frontend/src/components/StatCard.tsx`, `StatusBadge.tsx`, `EmptyState.tsx`, `PageHeader.tsx`
10. Verify steps.

---

#### TONE & EXPERTISE LEVEL

Expert. Next.js 14 App Router, shadcn/ui component API, and TanStack Query patterns assumed known.

---

#### THINKING INSTRUCTION

Before writing `layout.tsx`, decide how to handle the "use client" boundary given that the sidebar needs `usePathname()` for active state. State the boundary decision (which components are server vs. client) before writing any layout code. Before writing the campaign detail page, decide whether the slide-out drawer is managed with URL state or component state — state the choice and why.

---

#### DETAILED SPEC

**`/frontend/src/lib/types.ts`** — mirror backend Pydantic schemas:
```typescript
Campaign, CampaignDetail (with stats), Lead, LeadDetail (with emails + replies),
Email, Reply, Meta, UploadResult
```

**`/frontend/src/lib/api.ts`** — native `fetch`, base URL from `process.env.NEXT_PUBLIC_API_BASE`. Generic request function handles `{ data, error, meta }` envelope. If `error` is non-null: throw with `error.code` and `error.message`.
```typescript
fetchCampaigns(page: number, size: number): Promise<{ data: Campaign[], meta: Meta }>
fetchCampaign(id: string): Promise<{ data: CampaignDetail }>
patchCampaignStatus(id: string, status: string): Promise<void>
uploadLeads(campaignId: string, file: File): Promise<UploadResult>
fetchLeads(campaignId: string, page: number): Promise<{ data: Lead[], meta: Meta }>
fetchLead(id: string): Promise<{ data: LeadDetail }>
```

**`/frontend/src/app/layout.tsx`** — design direction:
- Left sidebar, fixed, ~240px wide, `slate-900` background.
- Logo at top. Nav items with icons: Dashboard, Campaigns, Leads, Templates (link only), Integrations (link only), Settings.
- Active item: white text + subtle accent highlight.
- Main content: `slate-50` background, generous padding.
- Top header bar: breadcrumb left, Gmail connection status pill (green/red) right.
- Geist font via `next/font/google`.

**`/frontend/src/app/dashboard/page.tsx`:**
- 5 stat cards (responsive grid): Total Leads, Emails Sent, Open Rate, Reply Rate, Meetings Booked. Big number + label + trend indicator. `shadcn/ui Card`.
- Line chart (60% width): "Emails Sent Per Day", last 30 days. Recharts `LineChart`.
- Bar chart (40% width): "Reply Rate by Campaign". Recharts `BarChart`, green bars, campaign names truncated to 12 chars.
- Data: `useQuery(["dashboard-stats"])` → `GET /api/campaigns`, aggregate client-side.
- Empty state: muted icon + "No campaigns yet. Create your first one." + button.

**`/frontend/src/app/campaigns/page.tsx`:**
- `shadcn/ui Table`. Columns: Name, Status (badge), Leads, Sent, Opened %, Replied %, Created.
- Status badges: draft=gray, active=green, paused=amber, completed=blue.
- Row click → `/campaigns/[id]`. Row 3-dot menu: View, Pause/Resume, Archive.
- Top right: "New Campaign" button (opens creation modal from Phase 5B).
- Bottom pagination. Loading: 3 skeleton rows. Empty state centered.

**`/frontend/src/app/campaigns/[id]/page.tsx`:**
- Top: campaign name, status badge, 5 stats inline, "Launched [date]", Pause/Resume button.
- Leads table. Columns: Company, Contact, Email, Status (badge), Last Touched, Actions.
- Lead status badges: new=gray, researched=blue, email_sent=purple, replied=amber, meeting_booked=green, unsubscribed=slate.
- Row click → slide-out `shadcn/ui Sheet` (drawer).
- Drawer: company + contact as title. Timeline email thread. Each email: tag (Outreach/Follow-up), date, subject (bold), body (3-line truncate, expandable). Reply shown below with slate-50 background + classification badge. "Research in progress..." if no emails.

**`/frontend/src/app/settings/page.tsx`:**
- Gmail section: connected (green pill + email) or not connected (red pill) + "Connect Gmail" button.
- `?gmail=connected` URL param → show `shadcn/ui Toast` success.
- API Keys section: green/red indicators for configured env vars — no actual key values shown.

**Shared components:**
- `StatCard.tsx` — metric card used on dashboard and campaign detail.
- `StatusBadge.tsx` — colored badge from status string.
- `EmptyState.tsx` — centered icon + message + optional button.
- `PageHeader.tsx` — title + optional subtitle + optional action button.

**Verify:**
```bash
cd frontend && npm run dev   # starts on localhost:3000

# Manual checks:
# 1. /dashboard renders stat cards and chart containers
# 2. /campaigns renders empty state
# 3. /settings renders "Not Connected" Gmail status
# 4. /campaigns/[fake-uuid] shows empty state, not a crash
# 5. Sidebar navigation works without full reload

cd frontend && npx tsc --noEmit
# Expected: Zero type errors
```

---

## Phase 5B — Campaign Creation Flow

---

#### ROLE & PERSONA

You are a senior frontend engineer who specializes in multi-step form UX, typed React state machines, and browser-side data processing. You have built campaign creation flows for B2B SaaS tools and know how to design for user trust during high-stakes actions (CSV upload, email launch).

---

#### TASK & OBJECTIVE

Build a 3-step campaign creation modal (campaign basics → CSV upload + mapping → review + launch) as a typed React state machine without a form library — achieving all 9 manual test cases passing and zero TypeScript errors.

---

#### MY SITUATION

Phase 5A is complete — the campaigns page and shell are built. The "New Campaign" button exists but has no handler yet. The `uploadLeads`, `fetchCampaigns`, and `patchCampaignStatus` API functions exist in `api.ts`. `react-dropzone` is installed. shadcn/ui `Dialog`, `Select`, `Toast` are available.

---

#### CONSTRAINTS

- **CSV parsing is browser-side** — use `FileReader` + manual parsing. Do not send the file to an API just to preview it.
- **No form library** — the multi-step form is a controlled `useState` state machine.
- **3 API calls in Step 3 must be sequential**: create campaign → upload leads → activate. On partial failure, do NOT leave a broken campaign in "active" state.
- **No `console.log`**.
- Step 2 column mapping must **auto-detect** obvious column name matches (`"email"`, `"Email"`, `"email_address"` etc.) before the user selects.
- Modal state must **reset to Step 1** when closed mid-way — no leftover state on reopen.

---

#### AUDIENCE FOR THE OUTPUT

This modal is the primary user action — it's used every time a new campaign starts. Any friction, state bugs, or confusing validation messages directly reduces product value. The launch button is a commitment — make the user feel confident before they click it (Step 3 review is the trust-builder).

---

#### PRIOR ATTEMPTS / WHAT FAILED

- Do not use `useReducer` for the form state — `useState` with a typed `CampaignFormData` object is sufficient and easier to read.
- Do not validate the CSV immediately on file drop — wait until the column mapping is set in Part B before computing `validRows` / `invalidRows`.
- Do not call all 3 API endpoints in parallel in Step 3 — they are sequential by design (upload requires the campaign ID from step 1).
- Do not use a third-party CSV library — `FileReader` + `split('\n')` + `split(',')` is sufficient for this MVP.

---

#### FORMAT

Deliver files in this order:
1. `/frontend/src/components/campaigns/create/types.ts` — `Step`, `CampaignFormData`, `ParsedRow`, `InvalidRow`
2. `/frontend/src/components/campaigns/CreateCampaignModal.tsx` — Dialog wrapper + step indicator + navigation buttons
3. `/frontend/src/components/campaigns/create/Step1Basics.tsx` — campaign fields + tone selector
4. `/frontend/src/components/campaigns/create/Step2Upload.tsx` — dropzone + column mapping + validation preview
5. `/frontend/src/components/campaigns/create/Step3Review.tsx` — summary + launch sequence
6. `/frontend/src/app/campaigns/page.tsx` update — wire modal open/close + query invalidation
7. Verify steps (9 manual test cases).

---

#### TONE & EXPERTISE LEVEL

Expert. shadcn/ui Dialog API, react-dropzone, and TypeScript discriminated unions assumed known.

---

#### THINKING INSTRUCTION

Before writing Step 2, think through the CSV parsing edge cases: headers with trailing whitespace, emails with commas inside quotes, files with Windows line endings (`\r\n`). State which edge cases you will handle and which you will defer to "valid CSV only" for this MVP.

---

#### DETAILED SPEC

**Types:**
```typescript
type Step = 1 | 2 | 3

interface CampaignFormData {
  name: string
  product: string
  valueProp: string           // max 100 words — enforce with word counter
  caseStudy: string
  tone: "professional_friendly" | "direct" | "warm"
  file: File | null
  columnMapping: {
    company_name: string
    email: string
    website: string | null
    contact_name: string | null
  }
  parsedRows: ParsedRow[]     // first 20 rows after mapping
  validRows: number
  invalidRows: InvalidRow[]   // { rowIndex, reason }
}

interface ParsedRow {
  company_name: string
  email: string
  website?: string
  contact_name?: string
  isValid: boolean
}
```

**`CreateCampaignModal.tsx`** — shadcn/ui Dialog. State: `step` (1|2|3), `formData`. Step indicators: 3 numbered circles at top (current filled). "Back" except step 1. "Next"/"Launch" bottom right. "Next" disabled when required fields for current step are empty.

**`Step1Basics.tsx`:**
- Campaign name: text input (max 80 chars, required).
- Product/service: text input (max 80 chars, required).
- Value proposition: textarea (required). Word counter below: amber at 90 words, red at 100+.
- Case study: textarea (placeholder: "Example: We helped LogiCorp reduce manual outreach by 40% in 3 months").
- Tone: 3-option segmented control (not a dropdown): Professional & Friendly | Direct | Warm.
- No asterisks for required — all fields are required.

**`Step2Upload.tsx`:**

Part A — react-dropzone (`.csv` only). Dashed border, cloud icon, "Drop your CSV here or click to browse". Shows filename + size on selection. "Remove" button.

Part B — Column mapping (after file parsed): required fields `company_name` + `email` → Select from CSV columns. Optional fields `website` + `contact_name` → Select + "Not in CSV" option. Auto-detect: pre-select if column name closely matches.

Part C — Validation preview: first 5 rows in a table. Invalid email rows: red background + warning icon. Below: "X valid rows, Y will be skipped" summary.

**`Step3Review.tsx`:**
Summary box:
- Campaign: [name], Product: [product], Tone: [tone]
- Leads: [validRows] valid, [invalidRows.length] skipped
- Estimated send time: `[validRows * 30 / 60]` minutes
- Gmail status: connected ✓ or ⚠ Not connected (link to /settings)

Launch sequence (sequential, not parallel):
1. `POST /api/campaigns` → get `campaign.id`
2. `POST /api/leads/upload` with file + `campaign_id`
3. `PATCH /api/campaigns/{id}/status` → `"active"`
4. On success: close modal, navigate to `/campaigns/{id}`, show toast.
5. On error: show inline error alert inside modal (do NOT close).
6. Loading: button shows spinner + "Launching...".

**Wire into campaigns page:** `useState(false)` for open/close. On successful creation: `invalidateQueries(["campaigns"])`.

**Verify:**
```bash
cd frontend && npm run dev

# Golden path:
# 1. Click "New Campaign" → modal opens at Step 1
# 2. Fill all fields → "Next" becomes enabled
# 3. Click Next → Step 2
# 4. Upload 5-row CSV with 1 bad email → preview shows 4 valid / 1 skipped
# 5. Click Next → Step 3 shows correct counts
# 6. Click "Launch Campaign" → campaign created, redirect to /campaigns/[id]

# Edge cases:
# 7. Advance Step 1 with empty name → Next stays disabled
# 8. Upload CSV with no "email" column → column mapping shows all CSV headers
# 9. Close modal mid-way → reopen → Step 1 resets (no leftover state)

cd frontend && npx tsc --noEmit
# Expected: Zero type errors
```

---

## After Phase 5

1. Screenshot the dashboard, campaigns list, and campaign creation modal.
2. Update `CLAUDE.md`: Phase 5 → ✅ complete.
3. Note in `scratchpad.md`: any shadcn/ui component quirks, react-dropzone config notes.
4. Commit. Open Phase 6 in a new session.
