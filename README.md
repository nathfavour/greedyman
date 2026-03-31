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
2. Create a Python virtual environment in `brain/` and install dependencies.
3. Install Node dependencies in `body/`.
4. Run `scripts/run_greedyman.sh` to start the daemon loop.

## MVP Workflow

- Start with `GREEDYMAN_FIXTURE_FILE=brain/sample_quotes.json` for deterministic local runs.
- Use `GREEDYMAN_DRY_RUN=1` until the vault config is populated and the adapter is ready.
- The daemon persists cooldown and summary state to `GREEDYMAN_STATE_FILE`.
- Set `GREEDYMAN_JSON_LOGS=1` if you want structured terminal logs for demo capture or debugging.

## Design Notes

- The default mode should be safe for Devnet and dry-run local testing.
- Rebalance only when the APY spread crosses the configured threshold.
- Keep transaction confirmation explicit and wait for confirmed or finalized commits before reporting success.
- The project is intentionally terminal-first and should not grow a web UI.

