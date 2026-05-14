# This package is the ONLY interface through which backend code may invoke agents.
# Backend services MUST NOT import from /agents directly.
# All LLM/agent calls must be routed through functions defined in this package.
# This enforces the plane separation described in docs/00-ARCHITECTURE.md.
