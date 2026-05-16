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


async def smoke_followup() -> int:
    _bootstrap_env_and_paths()
    from agents.followup_agent import run_followup_agent

    original = {"subject": "Quick question about Stripe", "body": "Hi there, wanted to ask about your outbound stack."}
    research = {"research_summary": "Stripe is a global fintech company.", "pain_points": ["outbound at scale"]}

    scenarios = [
        ("day_3_bump",       3,  []),
        ("day_7_value_add",  7,  []),
        ("day_14_breakup",  14,  []),
        ("stop",            15,  []),
    ]

    all_ok = True
    for expected_strategy, days, prior in scenarios:
        print(f"\n--- days={days} (expected: {expected_strategy}) ---")
        result = await run_followup_agent(
            lead_id="smoke-lead-1",
            days_since_last_touch=days,
            original_email=original,
            prior_followups=prior,
            research=research,
        )
        print(f"strategy={result.strategy}, should_send={result.should_send}")
        if result.strategy != expected_strategy:
            print(f"FAIL: expected strategy={expected_strategy}, got {result.strategy}", file=sys.stderr)
            all_ok = False
        if result.should_send and result.body:
            word_count = len(result.body.split())
            print(f"body ({word_count} words): {result.body[:120]}")
            if expected_strategy == "day_3_bump" and word_count > 40:
                print(f"FAIL: day_3_bump body exceeds 40 words ({word_count})", file=sys.stderr)
                all_ok = False
            if expected_strategy == "day_14_breakup" and word_count > 30:
                print(f"FAIL: day_14_breakup body exceeds 30 words ({word_count})", file=sys.stderr)
                all_ok = False

    if all_ok:
        print("\nOK — all 4 strategies produced correct output")
    return 0 if all_ok else 1


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
