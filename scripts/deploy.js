const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log(
    "Account balance:",
    (await hre.ethers.provider.getBalance(deployer.address)).toString(),
  );

  // ── 1. Get USDC address for the target network ──────────────────────
  const networkName = hre.network.name;
  let usdcAddress;

  if (networkName === "baseSepolia") {
    // Base Sepolia USDC (Circle's testnet USDC)
    usdcAddress =
      process.env.USDC_ADDRESS_SEPOLIA ||
      "0x036CbD53842c5426634e7929541eC2318f3dCF7e";
  } else if (networkName === "baseMainnet") {
    // Base Mainnet native USDC
    usdcAddress =
      process.env.USDC_ADDRESS_MAINNET ||
      "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
  } else {
    // Local hardhat — deploy a mock ERC20 for testing
    console.log("Deploying Mock USDC for local testing...");
    const MockERC20 = await hre.ethers.getContractFactory("MockUSDC");
    // If no MockUSDC contract exists, use a placeholder address
    usdcAddress = "0x0000000000000000000000000000000000000001";
    console.log(
      "Using placeholder USDC address for local network:",
      usdcAddress,
    );
  }

  console.log("Using USDC address:", usdcAddress);
  console.log("---");

  // ── 2. Deploy PolicyNFT ─────────────────────────────────────────────
  console.log("Deploying PolicyNFT...");
  const PolicyNFT = await hre.ethers.getContractFactory("PolicyNFT");
  const policyNFT = await PolicyNFT.deploy();
  await policyNFT.waitForDeployment();
  const policyNFTAddress = await policyNFT.getAddress();
  console.log("PolicyNFT deployed to:", policyNFTAddress);

  // ── 3. Deploy LiquidityPool ─────────────────────────────────────────
  console.log("Deploying LiquidityPool...");
  const LiquidityPool = await hre.ethers.getContractFactory("LiquidityPool");
  const liquidityPool = await LiquidityPool.deploy(usdcAddress);
  await liquidityPool.waitForDeployment();
  const liquidityPoolAddress = await liquidityPool.getAddress();
  console.log("LiquidityPool deployed to:", liquidityPoolAddress);

  // ── 4. Deploy ClaimsContract ────────────────────────────────────────
  console.log("Deploying ClaimsContract...");
  const ClaimsContract = await hre.ethers.getContractFactory("ClaimsContract");
  const claimsContract = await ClaimsContract.deploy(
    policyNFTAddress,
    liquidityPoolAddress,
  );
  await claimsContract.waitForDeployment();
  const claimsContractAddress = await claimsContract.getAddress();
  console.log("ClaimsContract deployed to:", claimsContractAddress);

  // ── 5. Wire contracts together ──────────────────────────────────────
  console.log("---");
  console.log("Wiring contracts...");

  // Allow ClaimsContract to call LiquidityPool.releasePayout()
  const txPool = await liquidityPool.setClaimsContract(claimsContractAddress);
  await txPool.wait();
  console.log("LiquidityPool.claimsContract set to:", claimsContractAddress);

  // Transfer PolicyNFT ownership to ClaimsContract so it can call markClaimed()
  // NOTE: The deployer first owns PolicyNFT. We transfer ownership so ClaimsContract
  // can mark policies as claimed. The deployer retains ClaimsContract ownership.
  const txNFT = await policyNFT.transferOwnership(claimsContractAddress);
  await txNFT.wait();
  console.log(
    "PolicyNFT ownership transferred to ClaimsContract:",
    claimsContractAddress,
  );

  // ── 6. Save deployment addresses ────────────────────────────────────
  const deployments = {
    network: networkName,
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
    contracts: {
      PolicyNFT: policyNFTAddress,
      ClaimsContract: claimsContractAddress,
      LiquidityPool: liquidityPoolAddress,
      USDC: usdcAddress,
    },
  };

  const deploymentsPath = path.join(__dirname, "..", "deployments.json");
  fs.writeFileSync(deploymentsPath, JSON.stringify(deployments, null, 2));

  console.log("---");
  console.log("Deployment addresses saved to deployments.json");
  console.log("Deployment complete!");
  console.log(JSON.stringify(deployments.contracts, null, 2));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Deployment failed:", error);
    process.exit(1);
  });
