# Greedyman Agent Guide

This repository is for a headless Solana USDC yield allocator. Agents working here should optimize for speed, low overhead, and clear separation between off-chain decision logic and on-chain execution.

## Operating Principles

- Work only within this project directory unless the user explicitly asks otherwise.
- Keep the stack CLI-first and daemon-oriented. Do not introduce web UI frameworks.
- Preserve the split between the Python "brain" and the TypeScript "body".
- Prefer small, focused changes that fit the existing flat, system-style layout.
- Use ASCII by default unless an existing file clearly requires otherwise.
- Avoid destructive git operations and never rewrite history unless explicitly requested.

## Architecture Split

- `brain/` owns scraping, APY comparison, cooldown logic, and subprocess orchestration.
- `body/` owns Solana execution through `@voltr/vault-sdk` and `@solana/web3.js`.
- `scripts/` owns startup, automation, and watchdog helpers.
- `README.md` should explain the hackathon demo, runtime model, and deployment path.

## Expected Repository Layout

- `brain/requirements.txt`
- `brain/main.py`
- `brain/scraper.py`
- `brain/engine.py`
- `body/package.json`
- `body/index.ts`
- `body/vault_config.json`
- `scripts/run_greedyman.sh`
- `scripts/monitor.sh`
- `.env.example`
- `README.md`

## Implementation Rules

- Python code should use `httpx`, `asyncio`, `rich`, and `python-dotenv` where appropriate.
- TypeScript code should use modern async patterns and keep Solana transaction handling explicit.
- The Python layer should trigger the TypeScript layer through `subprocess.run()` with clear CLI arguments.
- The TypeScript layer should verify vault state before moving funds and confirm transactions at `confirmed` or `finalized`.
- Keep cooldown logic in the engine to reduce churn from micro-fluctuations.

## Workflow Expectations

- Build and validate in small phases: environment, scraper, engine, adapter, dashboard, automation.
- Prefer Devnet for early testing and simulation.
- Do not switch to Mainnet logic or keys until the project is ready for that phase.
- When adding files, keep naming simple and consistent with the existing structure.

## Security and Secrets

- Never commit private keys, `.env` files, or RPC credentials.
- Keep secrets only in local environment files and document them in `.env.example`.
- Treat wallet paths and RPC URLs as configuration, not code.

## Quality Bar

- Keep daemon entry points robust and easy to restart.
- Favor explicit logging so terminal output is useful during long runs.
- Add tests when they materially reduce risk, especially around yield threshold logic and command invocation.

