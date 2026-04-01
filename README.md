# Greedyman

Greedyman is a headless USDC yield allocator for Solana. The project is split into two layers:

- `brain/` for scraping APY data, deciding when to rebalance, and orchestrating execution.
- `body/` for the on-chain adapter that moves capital between vault strategies.

## Layout

```text
greedyman/
├── brain/
├── body/
├── scripts/
├── .env.example
└── README.md
```

## Quick Start

1. Copy `.env.example` to `.env` and fill in RPC and wallet values.
2. Run `scripts/bootstrap.sh` to create the Python venv and install the brain dependencies.
3. Install Node dependencies in `body/` with `pnpm install`.
4. Run `scripts/run_greedyman.sh` to start the daemon loop.

## MVP Workflow

- Start with `GREEDYMAN_FIXTURE_FILE=brain/sample_quotes.json` for deterministic local runs.
- Add `GREEDYMAN_DEMO_PROFILE_FILE=brain/sample_demo_profile.json` to force visible APY spikes on specific cycles.
- Use `GREEDYMAN_DRY_RUN=1` until the vault config is populated and the adapter is ready.
- The daemon persists cooldown and summary state to `GREEDYMAN_STATE_FILE`.
- Set `GREEDYMAN_JSON_LOGS=1` if you want structured terminal logs for demo capture or debugging.
- `GREEDYMAN_SWITCHBACK_BUFFER_APY` adds a small buffer so the bot does not thrash between nearly equal yields.
- Run `python3 -m unittest discover -s brain/tests -t .` from the repo root to verify the core decision logic.
- Set `GREEDYMAN_BODY_JSON=1` when you want the TypeScript adapter to emit machine-readable JSON instead of plain terminal output.
- Run `pnpm exec tsx index.ts --validate-only` in `body/` to check strategy config without touching the chain.
- Run `pnpm exec tsx index.ts --target Drift --source Kamino --amount 100%` in `body/` to execute a live rebalance once the vault and strategy pubkeys are configured.
- Run `scripts/report.sh --fixture-file brain/sample_quotes.json` to generate a quick markdown status report from the persisted daemon state.

## Design Notes

- The default mode should be safe for Devnet and dry-run local testing.
- Rebalance only when the APY spread crosses the configured threshold.
- Keep transaction confirmation explicit and wait for confirmed or finalized commits before reporting success.
- The project is intentionally terminal-first and should not grow a web UI.

