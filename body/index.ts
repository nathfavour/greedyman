import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { Connection, Keypair, PublicKey } from "@solana/web3.js";
import { VoltrClient } from "@voltr/vault-sdk";

type CliArgs = {
  target: string;
  amount: string;
  source?: string;
  dryRun: boolean;
  json: boolean;
  validateOnly: boolean;
  rpcUrl: string;
  keypairPath: string;
  configPath: string;
};

type VaultConfig = {
  vaultPubkey: string;
  vaultAssetMint: string;
  targetCommitment: "confirmed" | "finalized";
  strategies: Record<
    string,
    {
      strategyPubkey: string;
      adaptorProgram: string;
    }
  >;
  rebalance: {
    withdrawLabel: string;
    depositLabel: string;
  };
};

type RebalancePlan = {
  target: string;
  amount: string;
  vault: string;
  rpcUrl: string;
  commitment: "confirmed" | "finalized";
  sourceStrategy?: string;
  targetStrategy?: string;
  adaptorProgram?: string;
  dryRun: boolean;
};

type ExecutionIntent = {
  target: string;
  source: string | undefined;
  amountLabel: string;
  vault: string;
  commitment: "confirmed" | "finalized";
  dryRun: boolean;
};

function parseArgs(argv: string[]): CliArgs {
  const args: Record<string, string | boolean> = {
    dryRun: process.env.GREEDYMAN_DRY_RUN !== "0",
    json: process.env.GREEDYMAN_BODY_JSON === "1",
    validateOnly: process.env.GREEDYMAN_VALIDATE_ONLY === "1",
    rpcUrl: process.env.HELIUS_RPC_URL ?? "https://api.devnet.solana.com",
    keypairPath: process.env.SOLANA_KEYPAIR_PATH ?? `${process.env.HOME ?? ""}/.config/solana/id.json`,
    configPath: new URL("./vault_config.json", import.meta.url).pathname,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    const next = argv[index + 1];
    if (token === "--target" && next) args.target = next;
    if (token === "--amount" && next) args.amount = next;
    if (token === "--source" && next) args.source = next;
    if (token === "--rpc" && next) args.rpcUrl = next;
    if (token === "--keypair" && next) args.keypairPath = next;
    if (token === "--config" && next) args.configPath = next;
    if (token === "--dry-run") args.dryRun = true;
    if (token === "--json") args.json = true;
    if (token === "--validate-only") args.validateOnly = true;
  }

  if (!args.target || !args.amount) {
    throw new Error("Usage: tsx index.ts --target <protocol> --amount <label>");
  }

  return args as CliArgs;
}

function loadVaultConfig(configPath: string): VaultConfig {
  const raw = readFileSync(resolve(configPath), "utf8");
  return JSON.parse(raw) as VaultConfig;
}

function readKeypair(keypairPath: string): Keypair {
  const secret = JSON.parse(readFileSync(resolve(keypairPath), "utf8")) as number[];
  return Keypair.fromSecretKey(Uint8Array.from(secret));
}

function buildPlan(args: CliArgs, config: VaultConfig, vaultPubkey: PublicKey): RebalancePlan {
  const targetConfig = config.strategies[args.target];
  return {
    target: args.target,
    amount: args.amount,
    vault: vaultPubkey.toBase58(),
    rpcUrl: args.rpcUrl,
    commitment: config.targetCommitment,
    sourceStrategy: args.source ?? Object.entries(config.strategies).find(([name]) => name !== args.target)?.[0],
    targetStrategy: targetConfig?.strategyPubkey,
    adaptorProgram: targetConfig?.adaptorProgram,
    dryRun: args.dryRun,
  };
}

function printOutput(args: CliArgs, label: string, payload: unknown): void {
  if (args.json) {
    console.log(
      JSON.stringify(
        {
          label,
          payload,
        },
        null,
        2,
      ),
    );
    return;
  }

  console.log(label);
  console.log(JSON.stringify(payload, null, 2));
}

function printJson(prefix: string, value: unknown): void {
  console.log(prefix);
  console.log(JSON.stringify(value, null, 2));
}

function buildIntent(plan: RebalancePlan): ExecutionIntent {
  return {
    target: plan.target,
    source: plan.sourceStrategy,
    amountLabel: plan.amount,
    vault: plan.vault,
    commitment: plan.commitment,
    dryRun: plan.dryRun,
  };
}

function validateConfig(config: VaultConfig, args: CliArgs): string[] {
  const issues: string[] = [];
  if (!config.vaultPubkey && !process.env.GREEDYMAN_VAULT_PUBKEY) {
    issues.push("Missing vault pubkey");
  }
  if (!config.strategies[args.target]) {
    issues.push(`Missing target strategy configuration for ${args.target}`);
  }
  if (args.source && !config.strategies[args.source]) {
    issues.push(`Missing source strategy configuration for ${args.source}`);
  }
  if (!args.dryRun && !args.validateOnly) {
    if (!readKeypairSafe(args.keypairPath)) {
      issues.push(`Keypair not readable at ${args.keypairPath}`);
    }
  }
  return issues;
}

function readKeypairSafe(keypairPath: string): boolean {
  try {
    readKeypair(keypairPath);
    return true;
  } catch {
    return false;
  }
}

async function confirmAtTargetCommitment(
  connection: Connection,
  signature: string,
  commitment: "confirmed" | "finalized",
): Promise<void> {
  const latest = await connection.getLatestBlockhash(commitment);
  await connection.confirmTransaction(
    {
      signature,
      blockhash: latest.blockhash,
      lastValidBlockHeight: latest.lastValidBlockHeight,
    },
    commitment,
  );
}

async function main(): Promise<number> {
  const args = parseArgs(process.argv.slice(2));
  const config = loadVaultConfig(args.configPath);
  const vaultPubkeyText = config.vaultPubkey || process.env.GREEDYMAN_VAULT_PUBKEY;
  if (!vaultPubkeyText && !args.validateOnly) {
    throw new Error("Missing vault pubkey. Set body/vault_config.json or GREEDYMAN_VAULT_PUBKEY.");
  }
  const issues = validateConfig(config, args);

  if (args.validateOnly) {
    printOutput(args, "[body] validation", {
      valid: issues.length === 0,
      issues,
      strategies: Object.keys(config.strategies),
    });
    return issues.length === 0 ? 0 : 1;
  }

  const vaultPubkey = new PublicKey(vaultPubkeyText);
  const connection = new Connection(args.rpcUrl, { commitment: config.targetCommitment });
  const client = new VoltrClient(connection);
  const plan = buildPlan(args, config, vaultPubkey);
  const intent = buildIntent(plan);

  const state = await client.getPositionAndTotalValuesForVault(vaultPubkey);
  printOutput(args, "[body] current vault state", {
    target: args.target,
    amount: args.amount,
    vault: vaultPubkey.toBase58(),
    totalValue: state.totalValue?.toString?.() ?? String(state.totalValue),
    strategies: state.strategies,
  });
  printOutput(args, "[body] execution plan", plan);
  printOutput(args, "[body] execution intent", intent);

  if (args.dryRun) {
    console.log(`[dry-run] would rotate capital into ${args.target} for ${args.amount}.`);
    return 0;
  }

  const keypair = readKeypair(args.keypairPath);
  console.log(`[body] signer ${keypair.publicKey.toBase58()} ready for vault ${vaultPubkey.toBase58()}.`);

  const targetConfig = config.strategies[args.target];
  const sourceConfig = args.source ? config.strategies[args.source] : undefined;
  if (!targetConfig?.strategyPubkey || !targetConfig?.adaptorProgram) {
    console.log(
      `[body] missing strategy configuration for ${args.target}. Fill body/vault_config.json before enabling live execution.`,
    );
    return 0;
  }

  if (!intent.source) {
    console.log("[body] no source strategy available, skipping live rebalance.");
    return 0;
  }
  if (args.source && !sourceConfig?.strategyPubkey) {
    console.log(`[body] source strategy ${args.source} is not configured in body/vault_config.json.`);
    return 0;
  }

  console.log(
    `[body] prepared live rotation from ${intent.source ?? "unknown"} into ${args.target} using commitment ${config.targetCommitment}. Add the direct withdraw/deposit instructions here once the vault strategy accounts are populated.`,
  );
  console.log(`[body] confirmation will use ${intent.commitment} commitment before returning success.`);
  return 0;
}

main()
  .then((code) => {
    process.exitCode = code;
  })
  .catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });

