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


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent smoke tests against real APIs.")
    parser.add_argument("agent", choices=["research", "all"])
    args = parser.parse_args()

    if args.agent in ("research", "all"):
        return asyncio.run(smoke_research())
    return 1


if __name__ == "__main__":
    sys.exit(main())
