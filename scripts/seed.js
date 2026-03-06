const { ethers } = require("hardhat");
require("dotenv").config();
const fs = require("fs");

/**
 * ChainSure SaaS — Seed Script
 *
 * Seeds the demo tenant's LiquidityPool with initial USDC reserves
 * and mints a sample policy NFT for testing.
 */
async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("  ChainSure SaaS — Seed Data");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

  // ── 1. Load deployed addresses ──
  if (!fs.existsSync("deployed-addresses.json")) {
    console.error("❌ deployed-addresses.json not found. Run deploy first.");
    process.exit(1);
  }

  const addresses = JSON.parse(
    fs.readFileSync("deployed-addresses.json", "utf8"),
  );
  const tenantId = "demo-tenant";
  const tenant = addresses.tenants[tenantId];

  console.log(`📌 Tenant: ${tenantId}`);
  console.log(`   PolicyNFT:      ${tenant.policyNFT}`);
  console.log(`   LiquidityPool:  ${tenant.liquidityPool}\n`);

  // ── 2. Get contract instances ──
  const PolicyNFT = await ethers.getContractAt("PolicyNFT", tenant.policyNFT);
  const LiquidityPool = await ethers.getContractAt(
    "LiquidityPool",
    tenant.liquidityPool,
  );

  // ── 3. Get USDC contract ──
  const usdcAddress =
    process.env.USDC_CONTRACT_ADDRESS ||
    "0x036CbD53842c5426634e7929541eC2318f3dCF7e";

  const usdcAbi = [
    "function approve(address spender, uint256 amount) returns (bool)",
    "function balanceOf(address account) view returns (uint256)",
    "function decimals() view returns (uint8)",
  ];
  const usdc = new ethers.Contract(usdcAddress, usdcAbi, deployer);

  // ── 4. Seed liquidity pool ──
  const seedAmount = ethers.parseUnits("1000", 6); // 1000 USDC

  console.log("💰 Seeding LiquidityPool with 1,000 USDC...");

  const balance = await usdc.balanceOf(deployer.address);
  console.log(
    `   Deployer USDC balance: ${ethers.formatUnits(balance, 6)} USDC`,
  );

  if (balance >= seedAmount) {
    // Approve pool to spend USDC
    const approveTx = await usdc.approve(tenant.liquidityPool, seedAmount);
    await approveTx.wait();
    console.log("   ✅ USDC approved for pool");

    // Deposit into pool
    const depositTx = await LiquidityPool.depositPremium(tenantId, seedAmount);
    await depositTx.wait();
    console.log("   ✅ 1,000 USDC deposited into pool\n");
  } else {
    console.log(
      "   ⚠️  Insufficient USDC balance. Skipping pool seed.\n" +
        "      Get testnet USDC from a faucet first.\n",
    );
  }

  // ── 5. Mint a sample policy ──
  console.log("📜 Minting sample policy NFT...");

  // Authorize deployer as minter
  try {
    const authTx = await PolicyNFT.authorizeMinter(deployer.address, tenantId);
    await authTx.wait();
    console.log("   ✅ Deployer authorized as minter");
  } catch (e) {
    console.log("   ℹ️  Deployer already authorized (or owner)");
  }

  const now = Math.floor(Date.now() / 1000);
  const oneYear = 365 * 24 * 60 * 60;

  const mintTx = await PolicyNFT.mintPolicy(
    tenantId,
    deployer.address,
    "Crop Insurance",
    ethers.parseUnits("50", 6), // $50 premium
    ethers.parseUnits("5000", 6), // $5000 coverage
    now,
    now + oneYear,
    "ipfs://QmSampleMetadataHash",
  );
  const mintReceipt = await mintTx.wait();
  console.log(`   ✅ Sample policy minted (tx: ${mintReceipt.hash})\n`);

  // ── 6. Summary ──
  const poolBalance = await LiquidityPool.getPoolBalance(tenantId);
  const policyCount = await PolicyNFT.getTenantPolicyCount(tenantId);

  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("  📊 Seed Summary");
  console.log(`  Pool Balance:  ${ethers.formatUnits(poolBalance, 6)} USDC`);
  console.log(`  Policies:      ${policyCount}`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Seed failed:", error);
    process.exit(1);
  });
