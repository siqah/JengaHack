require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

// Only include accounts if PRIVATE_KEY is a valid 64-char hex string
const privateKey = process.env.PRIVATE_KEY;
const accounts =
  privateKey && /^(0x)?[0-9a-fA-F]{64}$/.test(privateKey)
    ? [privateKey.startsWith("0x") ? privateKey : `0x${privateKey}`]
    : [];

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      evmVersion: "cancun",
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    hardhat: {
      chainId: 31337,
      allowUnlimitedContractSize: true,
    },
    base_sepolia: {
      url: process.env.BASE_SEPOLIA_RPC || "https://sepolia.base.org",
      accounts: accounts,
      chainId: 84532,
    },
    base_mainnet: {
      url: process.env.BASE_MAINNET_RPC || "https://mainnet.base.org",
      accounts: accounts,
      chainId: 8453,
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./tests/contracts",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};
