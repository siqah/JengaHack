const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();

  // ── Load deployment addresses ───────────────────────────────────────
  const deploymentsPath = path.join(__dirname, "..", "deployments.json");
  if (!fs.existsSync(deploymentsPath)) {
    throw new Error("deployments.json not found. Run deploy.js first.");
  }
  const deployments = JSON.parse(fs.readFileSync(deploymentsPath, "utf-8"));

  console.log("Seeding liquidity pool on network:", deployments.network);
  console.log("Using deployer:", deployer.address);

  const usdcAddress = deployments.contracts.USDC;
  const liquidityPoolAddress = deployments.contracts.LiquidityPool;

  // ── Get contract instances ──────────────────────────────────────────
  const usdc = await hre.ethers.getContractAt("IERC20", usdcAddress);
  const liquidityPool = await hre.ethers.getContractAt(
    "LiquidityPool",
    liquidityPoolAddress,
  );

  // ── Seed amount (10,000 USDC — 6 decimal places) ───────────────────
  const SEED_AMOUNT = process.env.SEED_AMOUNT
    ? hre.ethers.parseUnits(process.env.SEED_AMOUNT, 6)
    : hre.ethers.parseUnits("10000", 6); // 10,000 USDC

  console.log("Seed amount:", hre.ethers.formatUnits(SEED_AMOUNT, 6), "USDC");

  // ── Check deployer USDC balance ─────────────────────────────────────
  const balance = await usdc.balanceOf(deployer.address);
  console.log(
    "Deployer USDC balance:",
    hre.ethers.formatUnits(balance, 6),
    "USDC",
  );

  if (balance < SEED_AMOUNT) {
    throw new Error(
      `Insufficient USDC. Have ${hre.ethers.formatUnits(
        balance,
        6,
      )}, need ${hre.ethers.formatUnits(SEED_AMOUNT, 6)}`,
    );
  }

  // ── Approve LiquidityPool to spend USDC ─────────────────────────────
  console.log("Approving LiquidityPool to spend USDC...");
  const approveTx = await usdc.approve(liquidityPoolAddress, SEED_AMOUNT);
  await approveTx.wait();
  console.log("Approved.");

  // ── Deposit into LiquidityPool ──────────────────────────────────────
  console.log("Depositing USDC into LiquidityPool...");
  const depositTx = await liquidityPool.depositPremium(SEED_AMOUNT);
  await depositTx.wait();
  console.log("Deposited.");

  // ── Verify ──────────────────────────────────────────────────────────
  const poolBalance = await liquidityPool.getPoolBalance();
  console.log(
    "LiquidityPool balance:",
    hre.ethers.formatUnits(poolBalance, 6),
    "USDC",
  );
  console.log("Seeding complete!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Seeding failed:", error);
    process.exit(1);
  });
