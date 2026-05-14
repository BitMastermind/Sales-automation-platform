# /frontend — Next.js 14 Dashboard

The web dashboard. Where users create campaigns, upload leads, view analytics, and connect integrations.

## Stack
- Next.js 14 (App Router, TypeScript, `src/` dir)
- Tailwind CSS + shadcn/ui
- TanStack Query (the **only** data layer — no Redux/Zustand)
- Recharts for analytics
- react-dropzone for CSV upload

## Init Command
```bash
npx create-next-app@latest . --typescript --tailwind --app --src-dir
```

## Pages
| Path | Purpose |
|------|---------|
| `/dashboard` | Stats overview: emails sent, open rate, reply rate, meetings booked |
| `/campaigns` | List + create campaigns |
| `/campaigns/[id]` | Campaign detail with leads table + slide-out email thread |
| `/settings` | Gmail OAuth, API keys |

Full UX spec: [../docs/06-FRONTEND.md](../docs/06-FRONTEND.md)

## Rules
- Functional components only — no classes.
- All API calls via TanStack Query (`useQuery`/`useMutation`).
- No `console.log` in committed code.
- Mobile responsive is **not** required for MVP.
