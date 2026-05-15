"""Real-API smoke tests for agents. Not run in CI.

Usage:
    python agents/scripts/smoke.py research
    python agents/scripts/smoke.py all
"""
import argparse
import asyncio
import json
import sys


async def smoke_research() -> int:
    """Stub. Real implementation in Task 14."""
    raise NotImplementedError("Implemented in Task 14")


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent smoke tests against real APIs.")
    parser.add_argument("agent", choices=["research", "all"])
    args = parser.parse_args()

    if args.agent == "research":
        return asyncio.run(smoke_research())
    if args.agent == "all":
        return asyncio.run(smoke_research())
    return 1


if __name__ == "__main__":
    sys.exit(main())
