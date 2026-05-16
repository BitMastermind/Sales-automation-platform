# ⚡ AI Sales Outreach Automation

**Hyper-personalized B2B outreach — researched, written, and sent by AI agents**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.1-1C3C3C?style=flat-square)
![n8n](https://img.shields.io/badge/n8n-self--hosted-EA4B71?style=flat-square&logo=n8n&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-81%20passing-3fb950?style=flat-square)

Upload a CSV of leads. AI agents research each company, write a personalized email referencing their actual news and strategy, send it via Gmail, classify replies, and schedule follow-ups — automatically.

---

## 😤 Cold outreach is broken

Generic *"Hi {FirstName}, I noticed you work at {Company}"* emails get a **~1% reply rate**. Sales teams spend hours manually researching leads just to write emails that still feel templated.

The bottleneck isn't sending — it's the **research + personalization loop** that doesn't scale. Humans can't do deep company research at scale.

That's exactly what this platform automates.

---

## ✨ Let AI agents do the research

This platform ingests a list of leads, then runs a **LangGraph agent pipeline** for each lead: web research → company intelligence → hyper-personalized email → send via Gmail → reply classification → follow-up scheduling.

The product bet: **personalization quality beats volume**. One email that references a prospect's recent funding round, their job postings, or a pain point buried in their blog outperforms 100 generic blasts.
