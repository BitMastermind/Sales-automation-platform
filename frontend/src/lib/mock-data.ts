import type { Campaign, CampaignDetail, Lead, LeadDetail, Meta, Template, Integration } from "@/lib/types"

const now = new Date("2026-06-06T10:00:00Z")
function daysAgo(n: number) {
  const d = new Date(now)
  d.setDate(d.getDate() - n)
  return d.toISOString()
}

export const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: "camp-001",
    name: "SaaS Founders — Q2 Outreach",
    status: "active",
    created_at: daysAgo(18),
    stats: {
      leads_count: 142,
      emails_sent: 138,
      open_rate: 0.61,
      reply_rate: 0.27,
      meetings_booked: 9,
    },
  },
  {
    id: "camp-002",
    name: "Series A Startups — DevTools",
    status: "active",
    created_at: daysAgo(12),
    stats: {
      leads_count: 88,
      emails_sent: 74,
      open_rate: 0.54,
      reply_rate: 0.19,
      meetings_booked: 4,
    },
  },
  {
    id: "camp-003",
    name: "E-Commerce — Mid-Market",
    status: "paused",
    created_at: daysAgo(30),
    stats: {
      leads_count: 210,
      emails_sent: 210,
      open_rate: 0.48,
      reply_rate: 0.14,
      meetings_booked: 11,
    },
  },
  {
    id: "camp-004",
    name: "FinTech — Compliance Pain",
    status: "completed",
    created_at: daysAgo(55),
    stats: {
      leads_count: 64,
      emails_sent: 64,
      open_rate: 0.72,
      reply_rate: 0.34,
      meetings_booked: 7,
    },
  },
  {
    id: "camp-005",
    name: "Healthcare AI — Pilot",
    status: "draft",
    created_at: daysAgo(2),
    stats: {
      leads_count: 35,
      emails_sent: 0,
      open_rate: 0,
      reply_rate: 0,
      meetings_booked: 0,
    },
  },
]

export const MOCK_CAMPAIGN_DETAIL: Record<string, CampaignDetail> = {
  "camp-001": {
    ...MOCK_CAMPAIGNS[0],
    status: "active",
    stats: MOCK_CAMPAIGNS[0].stats!,
  },
  "camp-002": {
    ...MOCK_CAMPAIGNS[1],
    status: "active",
    stats: MOCK_CAMPAIGNS[1].stats!,
  },
  "camp-003": {
    ...MOCK_CAMPAIGNS[2],
    status: "paused",
    stats: MOCK_CAMPAIGNS[2].stats!,
  },
  "camp-004": {
    ...MOCK_CAMPAIGNS[3],
    status: "completed",
    stats: MOCK_CAMPAIGNS[3].stats!,
  },
  "camp-005": {
    ...MOCK_CAMPAIGNS[4],
    status: "draft",
    stats: MOCK_CAMPAIGNS[4].stats!,
  },
}

export const MOCK_LEADS: Record<string, Lead[]> = {
  "camp-001": [
    { id: "lead-001", campaign_id: "camp-001", company_name: "Notion", email: "james.wilkins@notion.so", contact_name: "James Wilkins", status: "replied", website: "https://notion.so", created_at: daysAgo(17) },
    { id: "lead-002", campaign_id: "camp-001", company_name: "Linear", email: "priya.nair@linear.app", contact_name: "Priya Nair", status: "meeting_booked", website: "https://linear.app", created_at: daysAgo(16) },
    { id: "lead-003", campaign_id: "camp-001", company_name: "Vercel", email: "tom.chen@vercel.com", contact_name: "Tom Chen", status: "email_sent", website: "https://vercel.com", created_at: daysAgo(15) },
    { id: "lead-004", campaign_id: "camp-001", company_name: "Loom", email: "sarah.oduya@loom.com", contact_name: "Sarah Oduya", status: "researched", website: "https://loom.com", created_at: daysAgo(14) },
    { id: "lead-005", campaign_id: "camp-001", company_name: "Retool", email: "dan.foster@retool.com", contact_name: "Dan Foster", status: "replied", website: "https://retool.com", created_at: daysAgo(13) },
    { id: "lead-006", campaign_id: "camp-001", company_name: "Coda", email: "alice.m@coda.io", contact_name: "Alice Mwangi", status: "email_sent", website: "https://coda.io", created_at: daysAgo(12) },
    { id: "lead-007", campaign_id: "camp-001", company_name: "Airtable", email: "brendan.k@airtable.com", contact_name: "Brendan Kim", status: "unsubscribed", website: "https://airtable.com", created_at: daysAgo(11) },
    { id: "lead-008", campaign_id: "camp-001", company_name: "Figma", email: "cleo.r@figma.com", contact_name: "Cleo Rivera", status: "meeting_booked", website: "https://figma.com", created_at: daysAgo(10) },
  ],
  "camp-002": [
    { id: "lead-101", campaign_id: "camp-002", company_name: "Stripe", email: "mark.j@stripe.com", contact_name: "Mark Jensen", status: "email_sent", website: "https://stripe.com", created_at: daysAgo(11) },
    { id: "lead-102", campaign_id: "camp-002", company_name: "Planetscale", email: "kim.l@planetscale.com", contact_name: "Kim Lee", status: "replied", website: "https://planetscale.com", created_at: daysAgo(10) },
    { id: "lead-103", campaign_id: "camp-002", company_name: "Neon", email: "omar.t@neon.tech", contact_name: "Omar Torres", status: "researched", website: "https://neon.tech", created_at: daysAgo(9) },
  ],
}

export const MOCK_LEAD_DETAIL: Record<string, LeadDetail> = {
  "lead-001": {
    id: "lead-001",
    campaign_id: "camp-001",
    company_name: "Notion",
    email: "james.wilkins@notion.so",
    contact_name: "James Wilkins",
    status: "replied",
    website: "https://notion.so",
    created_at: daysAgo(17),
    emails: [
      {
        id: "email-001a",
        lead_id: "lead-001",
        subject: "Quick question about Notion's team onboarding",
        body: `Hi James,

I noticed Notion recently crossed 4M users and you've been scaling the self-serve onboarding flow. At that velocity, even a 5% improvement in activation rate translates to thousands of additional MAUs per month.

We've helped teams at Linear and Vercel automate the research & personalization layer of their outbound — cutting prospecting time by ~70% while doubling reply rates.

Would a 20-min call make sense to explore if there's a fit?

Best,
Ashit`,
        type: "outreach",
        sent_at: daysAgo(16),
        opened_at: daysAgo(15),
        replies: [
          {
            id: "reply-001a",
            email_id: "email-001a",
            content: "Hey Ashit, this is interesting timing — we're actually reviewing our outbound stack next week. Can you send over a brief on how the personalization engine works?",
            classified_as: "interested",
            received_at: daysAgo(14),
          },
        ],
      },
    ],
  },
  "lead-002": {
    id: "lead-002",
    campaign_id: "camp-001",
    company_name: "Linear",
    email: "priya.nair@linear.app",
    contact_name: "Priya Nair",
    status: "meeting_booked",
    website: "https://linear.app",
    created_at: daysAgo(16),
    emails: [
      {
        id: "email-002a",
        lead_id: "lead-002",
        subject: "Personalized outreach for Linear's growth motion",
        body: `Hi Priya,

Linear's issue tracker is beloved by devs — but growing beyond product-led often means adding a sales motion that doesn't feel spammy. That's the exact problem we solve.

Our LangGraph research agent reads your ICP, finds recent trigger events (funding, headcount growth, tech stack changes), and drafts emails that don't read like templates.

Worth a quick call?`,
        type: "outreach",
        sent_at: daysAgo(15),
        opened_at: daysAgo(14),
        replies: [
          {
            id: "reply-002a",
            email_id: "email-002a",
            content: "Hi! Yes let's chat. I have availability Thu 2–3pm PT or Fri morning. Does either work?",
            classified_as: "meeting_booked",
            received_at: daysAgo(12),
          },
        ],
      },
      {
        id: "email-002b",
        lead_id: "lead-002",
        subject: "Re: Personalized outreach for Linear's growth motion",
        body: "Thursday 2pm PT works great — sending a calendar invite now. Looking forward to it!",
        type: "followup",
        sent_at: daysAgo(11),
        replies: [],
      },
    ],
  },
  "lead-005": {
    id: "lead-005",
    campaign_id: "camp-001",
    company_name: "Retool",
    email: "dan.foster@retool.com",
    contact_name: "Dan Foster",
    status: "replied",
    website: "https://retool.com",
    created_at: daysAgo(13),
    emails: [
      {
        id: "email-005a",
        lead_id: "lead-005",
        subject: "Retool + AI-assisted sales outreach?",
        body: `Hi Dan,

Retool's internal-tools angle is perfect for teams building custom CRM views — which made me curious whether your sales team runs on Retool too or something off-the-shelf.

Either way, I thought you'd appreciate an AI-native alternative to generic outreach. Happy to share results from a similar dev-tools company we worked with (38% reply rate on a 90-lead campaign).`,
        type: "outreach",
        sent_at: daysAgo(12),
        opened_at: daysAgo(11),
        replies: [
          {
            id: "reply-005a",
            email_id: "email-005a",
            content: "Not the right time for us — we're mid-way through a different vendor evaluation. Reach back in Q3.",
            classified_as: "not_now",
            received_at: daysAgo(9),
          },
        ],
      },
    ],
  },
}

export function mockMeta(total: number, page: number, size: number): Meta {
  return { page, size, total }
}

export const MOCK_TEMPLATES: Template[] = [
  {
    id: "tmpl-001",
    name: "SaaS Founder Cold Intro",
    type: "intro",
    subject: "Quick question about {{company}}'s growth motion",
    body: `Hi {{first_name}},

I noticed {{company}} recently {{trigger_event}}. At that velocity, even a 5% improvement in {{metric}} translates to meaningful impact.

We've helped teams at Linear and Vercel automate the research & personalization layer of their outbound — cutting prospecting time by ~70% while doubling reply rates.

Would a 20-min call make sense?

Best,
{{sender_name}}`,
    tags: ["SaaS", "Founder", "Growth"],
    used_count: 142,
    created_at: daysAgo(45),
  },
  {
    id: "tmpl-002",
    name: "DevTools Pain-Point Opener",
    type: "intro",
    subject: "{{company}} + AI-assisted outreach?",
    body: `Hi {{first_name}},

{{company}}'s {{product_angle}} is beloved by devs — which made me curious whether your sales team runs the same level of craft on outbound.

Our LangGraph research agent reads your ICP, finds recent trigger events (funding, headcount growth, tech stack changes), and drafts emails that don't read like templates.

Worth a quick call?`,
    tags: ["DevTools", "PLG", "Developer"],
    used_count: 88,
    created_at: daysAgo(30),
  },
  {
    id: "tmpl-003",
    name: "7-Day Follow-Up (No Reply)",
    type: "followup",
    subject: "Re: {{original_subject}}",
    body: `Hi {{first_name}},

Just bumping this up in case it got buried. Totally understand if the timing isn't right — happy to reconnect in Q3 if that works better.

If it's relevant: we recently helped a {{industry}} team generate {{result}} in 90 days with a 120-lead pilot.

Still worth 15 minutes?`,
    tags: ["Follow-up", "Nurture"],
    used_count: 214,
    created_at: daysAgo(60),
  },
  {
    id: "tmpl-004",
    name: "Meeting Confirmation + Value Add",
    type: "followup",
    subject: "Confirmed: {{meeting_time}} — one thing to skim beforehand",
    body: `Hi {{first_name}},

Looking forward to our call {{meeting_time}}. I've put together a 2-page brief on how the personalization engine works for companies like {{company}} — sharing it so we can skip the basics and get into what matters.

[Brief link]

See you then!`,
    tags: ["Meeting", "Confirmation"],
    used_count: 67,
    created_at: daysAgo(25),
  },
  {
    id: "tmpl-005",
    name: "90-Day Re-Engagement",
    type: "re_engagement",
    subject: "Still thinking about {{company}}",
    body: `Hi {{first_name}},

It's been a few months since we last spoke — hope things are going well at {{company}}.

I'm reaching back because we've since added {{new_feature}} which directly addresses the {{pain_point}} you mentioned. A few teams in {{industry}} are seeing strong early results.

Worth a quick catch-up?`,
    tags: ["Re-engagement", "Win-back"],
    used_count: 43,
    created_at: daysAgo(15),
  },
  {
    id: "tmpl-006",
    name: "FinTech Compliance Angle",
    type: "intro",
    subject: "How {{company}} handles {{compliance_topic}}",
    body: `Hi {{first_name}},

The compliance landscape for {{industry}} changed significantly in the last 12 months — and I've noticed {{company}} has been navigating it thoughtfully.

We work with FinTech teams to automate the research layer of sales outreach, so your reps spend time on high-intent conversations, not manual prospecting.

Open to a 15-min intro?`,
    tags: ["FinTech", "Compliance", "Enterprise"],
    used_count: 29,
    created_at: daysAgo(8),
  },
]

export const MOCK_INTEGRATIONS: Integration[] = [
  {
    id: "int-gmail",
    name: "Gmail",
    description: "Send and track outbound emails directly from your Gmail account. Replies sync automatically.",
    category: "email",
    status: "connected",
    connected_email: "ashitverma56@gmail.com",
    connected_at: daysAgo(20),
  },
  {
    id: "int-hubspot",
    name: "HubSpot",
    description: "Sync contacts, deals, and activity to your HubSpot CRM automatically after each email.",
    category: "crm",
    status: "disconnected",
  },
  {
    id: "int-slack",
    name: "Slack",
    description: "Get real-time notifications when a lead replies, books a meeting, or bounces.",
    category: "automation",
    status: "disconnected",
  },
  {
    id: "int-sheets",
    name: "Google Sheets",
    description: "Import leads from a Google Sheet and export campaign results back with one click.",
    category: "automation",
    status: "disconnected",
  },
  {
    id: "int-tavily",
    name: "Tavily",
    description: "Powers real-time web search in the research agent — finds trigger events and company news.",
    category: "enrichment",
    status: "connected",
    connected_at: daysAgo(45),
  },
  {
    id: "int-firecrawl",
    name: "Firecrawl",
    description: "Scrapes and structures company websites so the research agent can extract ICP signals.",
    category: "enrichment",
    status: "connected",
    connected_at: daysAgo(45),
  },
  {
    id: "int-salesforce",
    name: "Salesforce",
    description: "Bi-directional sync with Salesforce — push enriched leads and pull contact lists.",
    category: "crm",
    status: "coming_soon",
  },
]
