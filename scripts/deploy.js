const { ethers } = require("hardhat");
require("dotenv").config();

/**
 * ChainSure SaaS — Deployment Script
 *
 * Deploys the TenantFactory contract and creates a demo tenant
 * with a full contract set (PolicyNFT, ClaimsContract, LiquidityPool).
 */
async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("  ChainSure SaaS — Contract Deployment");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log(`  Deployer:  ${deployer.address}`);
  console.log(`  Network:   ${hre.network.name}`);
  console.log(
    `  Balance:   ${ethers.formatEther(await ethers.provider.getBalance(deployer.address))} ETH`,
  );
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

  // ── 1. Get USDC address ──
  const usdcAddress =
    process.env.USDC_CONTRACT_ADDRESS ||
    "0x036CbD53842c5426634e7929541eC2318f3dCF7e"; // Base Sepolia USDC

  console.log(`📌 USDC Address: ${usdcAddress}\n`);

  // ── 2. Deploy TenantFactory ──
  console.log("🏭 Deploying TenantFactory...");
  const TenantFactory = await ethers.getContractFactory("TenantFactory");
  const factory = await TenantFactory.deploy(usdcAddress);
  await factory.waitForDeployment();
  const factoryAddress = await factory.getAddress();
  console.log(`   ✅ TenantFactory deployed at: ${factoryAddress}\n`);

  // ── 3. Deploy demo tenant contracts ──
  const demoTenantId = "demo-tenant";
  console.log(`🔧 Deploying contracts for tenant: "${demoTenantId}"...`);
  const tx = await factory.deployTenantContracts(demoTenantId);
  const receipt = await tx.wait();
  console.log(`   ✅ Tenant contracts deployed (tx: ${receipt.hash})\n`);

  // ── 4. Read deployed addresses ──
  const [policyNFT, claimsContract, liquidityPool] =
    await factory.getTenantContracts(demoTenantId);

  console.log("📋 Demo Tenant Contract Addresses:");
  console.log(`   PolicyNFT:       ${policyNFT}`);
  console.log(`   ClaimsContract:  ${claimsContract}`);
  console.log(`   LiquidityPool:   ${liquidityPool}`);
  console.log("");

  // ── 5. Save addresses to file ──
  const fs = require("fs");
  const addresses = {
    network: hre.network.name,
    deployer: deployer.address,
    factory: factoryAddress,
    tenants: {
      [demoTenantId]: {
        policyNFT,
        claimsContract,
        liquidityPool,
      },
    },
  };

  fs.writeFileSync(
    "deployed-addresses.json",
    JSON.stringify(addresses, null, 2),
  );
  console.log("💾 Addresses saved to deployed-addresses.json");

  console.log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("  ✅ Deployment complete!");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
