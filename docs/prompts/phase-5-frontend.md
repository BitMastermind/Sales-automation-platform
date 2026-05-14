# Phase 5 — Next.js Frontend

> Build a SaaS dashboard — not a chatbot. Two sub-sessions. Use the frontend-design skill.

---

## Session Setup

| | |
|---|---|
| **Model** | `claude-opus-4-7` |
| **Skills** | Invoke `frontend-design` before writing any UI code. Invoke `brainstorming` before Phase 5B. |
| **Depends on** | Phase 2 complete (FastAPI running, `/api/campaigns` returns data). Phase 0 complete (Next.js initialized with shadcn/ui). |
| **Estimated time** | 2–3 hours across 2 sub-sessions |

> The goal is a polished, production-feel SaaS dashboard — not generic AI output.
> Invoke `/skill frontend-design` first in every Phase 5 session. It will guide design decisions.

---

## Phase 5A — Dashboard Layout + Pages

### Prompt

```
Read CLAUDE.md before starting.

Invoke the frontend-design skill before writing any component code.

## Context
Phase 5A of the AI Sales Outreach Automation project.
The Next.js app is already initialized in /frontend with shadcn/ui, Tailwind, and TanStack Query installed.
The FastAPI backend is at http://localhost:8000. Set up in .env.local:
  NEXT_PUBLIC_API_BASE=http://localhost:8000

## Task: Build the shell + 4 pages

### Step 0 — API client: /frontend/src/lib/api.ts
Create a typed API client using the native fetch API (no axios).
Base URL from process.env.NEXT_PUBLIC_API_BASE.
Generic request function that handles the { data, error, meta } response shape.
If error is non-null: throw with error.code and error.message.

Export typed functions:
  fetchCampaigns(page: number, size: number): Promise<{ data: Campaign[], meta: Meta }>
  fetchCampaign(id: string): Promise<{ data: CampaignDetail }>
  patchCampaignStatus(id: string, status: string): Promise<void>
  uploadLeads(campaignId: string, file: File): Promise<UploadResult>
  fetchLeads(campaignId: string, page: number): Promise<{ data: Lead[], meta: Meta }>
  fetchLead(id: string): Promise<{ data: LeadDetail }>

### Step 1 — Types: /frontend/src/lib/types.ts
Mirror the backend Pydantic schemas:
  Campaign, CampaignDetail (with stats), Lead, LeadDetail (with emails + replies),
  Email, Reply, Meta, UploadResult

### Step 2 — TanStack Query setup: /frontend/src/app/providers.tsx
Wrap with QueryClientProvider (staleTime: 30s, retry: 1).
Import in /frontend/src/app/layout.tsx.

### Step 3 — Layout shell: /frontend/src/app/layout.tsx
Build the application shell. Design direction:
  - Left sidebar, fixed, ~240px wide. Dark slate background (slate-900).
  - Logo / product name at top of sidebar.
  - Nav items with icons: Dashboard, Campaigns, Leads, Templates (link only, no page yet), 
    Integrations (link only), Settings.
  - Active item: white text + subtle accent highlight.
  - Main content area: white/slate-50 background, generous padding.
  - Top header bar: breadcrumb (current page name) on left, 
    Gmail connection status pill (green if connected, red if not) on right.
  - Use Geist font (next/font/google).
  - Use shadcn/ui NavigationMenu or just plain nav links — don't over-engineer.

### Step 4 — /dashboard page: /frontend/src/app/dashboard/page.tsx

Top row: 5 stat cards in a responsive grid.
  Cards: Total Leads, Emails Sent, Open Rate, Reply Rate, Meetings Booked.
  Each card: big number, label, trend indicator (up/down % vs last week — can be mocked).
  Use shadcn/ui Card component. Numbers in a large, bold font. Keep it clean.

Charts row:
  Left chart (60% width): Line chart — "Emails Sent Per Day" (last 30 days).
    X axis: date. Y axis: count. Use Recharts LineChart.
  Right chart (40% width): Bar chart — "Reply Rate by Campaign".
    X axis: campaign name (truncated to 12 chars). Y axis: percentage.
    Use Recharts BarChart with green bars.

Data: useQuery(["dashboard-stats"]) → GET /api/campaigns (aggregate client-side for MVP).

Empty state: If no campaigns exist, show a centered illustration area (just a large muted icon + 
  "No campaigns yet. Create your first one." + a "Create Campaign" button).

### Step 5 — /campaigns page: /frontend/src/app/campaigns/page.tsx

Table of campaigns using shadcn/ui Table.
Columns: Name, Status (badge), Leads, Sent, Opened %, Replied %, Created.
Status badges: draft=gray, active=green, paused=amber, completed=blue.

Row hover: subtle highlight. Clicking a row → navigate to /campaigns/[id].
Row actions dropdown (3-dot menu on hover): View, Pause/Resume, Archive.
Pause = PATCH status to "paused". Resume = PATCH to "active".

Top right: "New Campaign" button (primary, filled). Opens the campaign creation modal.
Pagination at the bottom: Previous / page numbers / Next.
Loading state: Skeleton rows (3 of them) while data loads.
Empty state: "No campaigns yet" with a "New Campaign" button centered.

### Step 6 — /campaigns/[id] page: /frontend/src/app/campaigns/[id]/page.tsx

Top section: Campaign name (heading), status badge, and the 5 stats inline.
  Also show: "Launched [date]" and an action button (Pause/Resume based on status).

Leads table (same shadcn/ui Table):
  Columns: Company, Contact, Email, Status (badge), Last Touched, Actions.
  Lead status badges: new=gray, researched=blue, email_sent=purple, 
    replied=amber, meeting_booked=green, unsubscribed=slate.
  Click a row → open a slide-out drawer panel (Radix Sheet or shadcn/ui Sheet).

Slide-out drawer — Email Thread:
  Shows the company name + contact as the drawer title.
  Below: a timeline-style email thread. Each email:
    - "Outreach" or "Follow-up" tag.
    - Date sent.
    - Subject in bold.
    - Body text (truncated to 3 lines, expandable).
    - If replied: the reply shown beneath with a different background (slate-50).
    - Reply classification badge (Interested/Not Interested/etc).
  If no emails yet: "Research in progress..." placeholder.

### Step 7 — /settings page: /frontend/src/app/settings/page.tsx

Two sections:

Gmail Integration:
  Status: connected (green pill with email address) or not connected (red pill).
  Button: "Connect Gmail" → fetch /api/auth/gmail, redirect to auth_url.
  URL param ?gmail=connected → show a success toast (shadcn/ui Toast).

API Keys (read-only display, no editing in MVP):
  Show which services are configured (non-empty env vars from /api/settings/status).
  Just green/red indicators — no actual key values.

### Step 8 — shared components: /frontend/src/components/

StatCard.tsx: the metric card used on /dashboard and /campaigns/[id].
StatusBadge.tsx: colored badge from status string. Used in leads and campaigns tables.
EmptyState.tsx: reusable centered empty state with icon + message + optional button.
PageHeader.tsx: page title + optional subtitle + optional action button (top of each page).

## Constraints
- All data fetching through TanStack Query (useQuery, useMutation). No raw fetch() in components.
- No class components.
- No Redux, no Zustand, no Context API for server data.
- Do NOT make the layout responsive for mobile — desktop only for MVP.
- Do NOT add animations unless shadcn/ui provides them out of the box.
- Do NOT use console.log — no logging in frontend committed code.

## Verify
Run: cd frontend && npm run dev (starts on localhost:3000)
Manually verify:
  1. /dashboard renders stat cards and chart containers (charts can be empty — no real data yet is OK)
  2. /campaigns renders an empty state (no campaigns exist yet)
  3. /settings renders with "Not Connected" Gmail status
  4. /campaigns/[id] with a fake UUID in the URL shows a 404-style empty state, not a crash
  5. Sidebar navigation works — clicking items changes the page without full reload

Run: cd frontend && npx tsc --noEmit
Expected: Zero type errors.
```

---

## Phase 5B — Campaign Creation Flow

### Prompt

```
Read CLAUDE.md before starting.

Invoke /skill brainstorming first — focus on the multi-step form UX and edge cases.
Then invoke /skill frontend-design for design guidance.

## Context
Phase 5B: the campaign creation modal.
This is the most user-facing feature and needs to feel polished.
No form library — use a typed React state machine.

## Task

### Step 1 — State machine types: /frontend/src/components/campaigns/create/types.ts
Define the form state:
  type Step = 1 | 2 | 3
  interface CampaignFormData {
    name: string
    product: string
    valueProp: string        // max 100 words — enforce with a counter
    caseStudy: string
    tone: "professional_friendly" | "direct" | "warm"
    file: File | null
    columnMapping: {
      company_name: string   // CSV column name that maps to company_name
      email: string
      website: string | null
      contact_name: string | null
    }
    parsedRows: ParsedRow[]  // first 20 rows of CSV after mapping
    validRows: number
    invalidRows: InvalidRow[]  // { rowIndex, reason }
  }

  interface ParsedRow {
    company_name: string
    email: string
    website?: string
    contact_name?: string
    isValid: boolean
  }

### Step 2 — Modal wrapper: /frontend/src/components/campaigns/CreateCampaignModal.tsx
Use shadcn/ui Dialog component.
State: step (1|2|3), formData (CampaignFormData).
Render the correct step component based on state.
Show step indicators at top (3 numbered circles, current one filled).
"Back" button (except on step 1). "Next" / "Launch" button at bottom right.
"Next" is disabled when required fields for the current step are empty.

### Step 3 — Step 1: /frontend/src/components/campaigns/create/Step1Basics.tsx
Fields:
  Campaign name: text input (required, max 80 chars).
  Product/service: text input (required, max 80 chars).
  Value proposition: textarea (required, soft limit 100 words — show word counter below field,
    amber warning at 90 words, red at 100+).
  Case study: textarea (required, placeholder: "Example: We helped LogiCorp reduce manual outreach by 40% in 3 months").
  Tone: 3-option segmented control (not a dropdown): Professional & Friendly | Direct | Warm.

Design: Clean form layout. Labels above inputs. Good spacing. No asterisks for required — everything is required.

### Step 4 — Step 2: /frontend/src/components/campaigns/create/Step2Upload.tsx
Part A — File upload:
  react-dropzone drop zone.
  Accept .csv only.
  Visual design: dashed border rectangle, cloud-upload icon, "Drop your CSV here or click to browse".
  On file selected: show file name + size.
  "Remove" button to clear and re-upload.
  Parse the CSV client-side using the browser FileReader API + manual CSV parsing (no csv-parse library).
  Extract: headers, first 20 rows.

Part B — Column mapping (shows after file parsed):
  For each required field (company_name, email): a Select dropdown showing CSV column names.
  For each optional field (website, contact_name): same, plus a "Not in CSV" option.
  Auto-detect: if a CSV column name closely matches ("email", "Email", "email_address" etc.) → pre-select it.

Part C — Validation preview table:
  Show the first 5 parsed+mapped rows in a small table.
  Columns: company name, email, website, contact.
  Rows with invalid email: red background, red warning icon.
  Below table: "X valid rows, Y will be skipped" summary line.

### Step 5 — Step 3: /frontend/src/components/campaigns/create/Step3Review.tsx
Summary box:
  Campaign: [name]
  Product: [product]
  Tone: [tone]
  Leads: [validRows] valid, [invalidRows.length] skipped
  Estimated send time: [validRows * 30 / 60] minutes (at 30s per lead)
  Gmail status: connected ✓ or ⚠ Not connected (linking to /settings)

"Launch Campaign" button (large, primary color):
  1. POST /api/campaigns with formData basics → get campaign ID.
  2. POST /api/leads/upload with file + campaign_id.
  3. PATCH /api/campaigns/{id}/status to "active".
  4. On success: close modal, navigate to /campaigns/{id}, show a toast.
  5. On any error: show an error alert inside the modal (don't close it).

Loading state: button shows spinner + "Launching..." during the 3 API calls.

### Step 6 — Wire modal into /campaigns page
In /frontend/src/app/campaigns/page.tsx:
  Import CreateCampaignModal.
  Manage open/closed state with useState.
  "New Campaign" button sets open=true.
  On successful creation: invalidate the ["campaigns"] query.

## Constraints
- CSV parsing must be browser-side (FileReader) — do NOT send the file to an API just to preview it.
- The multi-step form is a controlled state machine — no form library.
- The 3 API calls in Step 3 must happen sequentially (create → upload → activate). Handle partial failure:
  If upload fails, tell the user but do NOT create a broken campaign in "active" state.
- Do NOT use console.log.

## Verify
Run: cd frontend && npm run dev

Manual test — golden path:
  1. Click "New Campaign" → modal opens at Step 1.
  2. Fill in all fields → "Next" becomes enabled.
  3. Click Next → Step 2 opens.
  4. Upload a 5-row CSV with one bad email → preview table shows 4 valid / 1 skipped.
  5. Click Next → Step 3 shows correct counts.
  6. Click "Launch Campaign" → (backend must be running) campaign created, redirected to /campaigns/[id].

Manual test — edge cases:
  7. Try to advance Step 1 with empty name → Next stays disabled.
  8. Upload a CSV with no "email" column → verify the column mapping dropdown shows all CSV headers.
  9. Close the modal mid-way → reopen it → Step 1 resets (no leftover state).

Run: cd frontend && npx tsc --noEmit
Expected: Zero type errors.
```

---

## After Phase 5
1. Screenshot the dashboard, campaigns list, and campaign creation modal.
2. Update CLAUDE.md: Phase 5 → ✅ complete.
3. Note in `scratchpad.md`: any shadcn/ui component quirks, react-dropzone config notes.
4. Commit. Open Phase 6 in a new session.
