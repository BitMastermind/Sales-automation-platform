"""Real-API smoke tests for agents. Not run in CI.

Usage (from repo root, with backend/.venv activated):
    python agents/scripts/smoke.py research
    python agents/scripts/smoke.py all

Requires: TAVILY_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY in .env.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


def _bootstrap_env_and_paths() -> None:
    """Make `core.config` importable and load `.env` even when run standalone."""
    repo_root = Path(__file__).resolve().parents[2]
    backend = repo_root / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    # Best-effort .env load; production callers should already have env set
    env_path = repo_root / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


async def smoke_research() -> int:
    _bootstrap_env_and_paths()
    from agents.research_agent import run_research_agent

    lead = {"company_name": "Stripe", "website": "https://stripe.com"}
    print(f"Running research agent against {lead['company_name']}...")
    result = await run_research_agent(lead)
    print(json.dumps(result, indent=2))

    if not result.get("pain_points") or not result.get("research_summary"):
        print("FAIL: empty pain_points or research_summary", file=sys.stderr)
        return 1
    print("OK")
    return 0


async def smoke_followup() -> int:
    _bootstrap_env_and_paths()
    from agents.followup_agent import run_followup_agent

    original_email = {
        "subject": "Question about your sales motion",
        "body": "Hi, I wanted to ask about your outbound scaling challenges.",
    }
    research = {
        "industry": "Logistics SaaS",
        "company_size": "50-200",
        "pain_points": ["manual outbound", "scaling ops"],
        "research_summary": "Acme is a logistics SaaS expanding to Europe.",
    }

    scenarios = [
        ("day_3_bump (3 days)", 3),
        ("day_7_value_add (7 days)", 7),
        ("day_14_breakup (14 days)", 14),
        ("stop (15 days)", 15),
    ]

    all_ok = True
    for label, days in scenarios:
        print(f"\n--- {label} ---")
        result = await run_followup_agent(
            lead_id="smoke-lead",
            days_since_last_touch=days,
            original_email=original_email,
            prior_followups=[],
            research=research,
        )
        print(f"should_send: {result.should_send}")
        print(f"strategy:    {result.strategy}")
        if result.should_send:
            word_count = len(result.body.split()) if result.body else 0
            print(f"subject:     {result.subject}")
            print(f"body ({word_count} words): {result.body}")
            limit = 30 if result.strategy == "day_14_breakup" else 40 if result.strategy == "day_3_bump" else None
            if limit and word_count > limit:
                print(f"FAIL: body exceeds {limit}-word limit ({word_count} words)", file=sys.stderr)
                all_ok = False
    print("\nOK" if all_ok else "\nFAIL")
    return 0 if all_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent smoke tests against real APIs.")
    parser.add_argument("agent", choices=["research", "followup", "all"])
    args = parser.parse_args()

    if args.agent == "research":
        return asyncio.run(smoke_research())
    if args.agent == "followup":
        return asyncio.run(smoke_followup())
    if args.agent == "all":
        rc = asyncio.run(smoke_research())
        if rc != 0:
            return rc
        return asyncio.run(smoke_followup())
    return 1


if __name__ == "__main__":
    sys.exit(main())
