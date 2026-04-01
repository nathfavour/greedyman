# Greedyman Agent Guide

Greedyman is now a chain-agnostic, hexagonal intelligence platform for crypto and adjacent markets. Agents should protect the domain core, keep infrastructure replaceable, and treat AI/realtime data as pluggable capabilities rather than business logic.

## Operating Principles

- Work only inside this repository unless the user explicitly asks otherwise.
- Keep the system terminal-first and automation-friendly. Avoid web UI assumptions.
- Prefer small, reviewable changes that preserve a clear domain/adapter boundary.
- Use ASCII by default unless an existing file clearly requires otherwise.
- Do not use destructive git commands or rewrite history unless explicitly requested.

## Architecture Rules

- `core/` or equivalent domain code owns strategy, policy, risk, portfolio state, and decision rules.
- `ports/` define the contracts for market data, execution, storage, messaging, AI, and observability.
- `adapters/` or equivalent integration layers implement ports for specific chains, venues, LLMs, databases, and transports.
- Keep protocol-specific code out of the domain core.
- Keep chain-specific execution, wallet handling, and RPC details behind adapters.
- New features should be added as a port first, then implemented by one or more adapters.

## Intelligence Rules

- Treat AI as an external advisor, classifier, summarizer, or planner. It must not become a hidden source of truth.
- Real-time intelligence should be event-driven or poll-driven through a dedicated data adapter.
- All AI outputs should be explainable, logged, and safe to ignore if unavailable.
- Favor deterministic fallbacks for every AI-assisted decision.

## Runtime Rules

- Keep the main loop resilient, restartable, and observable.
- All long-running processes should emit structured logs and concise human-readable output.
- Store runtime state in explicit persistence layers, not scattered globals.
- If a workflow needs chain access, keep the chain details in the adapter layer only.

## Implementation Rules

- Use the best language for the boundary, but keep domain concepts consistent across languages.
- CLI contracts should be explicit and versioned when possible.
- Validation, dry-run, and simulation paths should exist for every execution path.
- Add tests around decision logic, adapter contracts, and persistence boundaries whenever they materially reduce risk.

## Security and Secrets

- Never commit private keys, `.env` files, API secrets, or credentials.
- Keep secrets in local environment files and document required values in `.env.example`.
- Treat RPC URLs, API endpoints, model keys, and wallet paths as configuration.

## Change Workflow

- Before adding new code, identify which domain concept, port, or adapter it belongs to.
- Prefer introducing new abstractions only when they reduce coupling or make a new integration possible.
- Keep documentation aligned with the actual architecture and execution path.
- If a change affects the operating model, update `README.md` and relevant tests in the same pass.

