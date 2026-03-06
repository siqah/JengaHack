# 🛡️ ChainSure — Blockchain Insurance SaaS

> Multi-tenant blockchain micro-insurance platform on **Base**. Licensed insurers plug into the platform via a dashboard, and end-users buy policies & file claims through **WhatsApp** — all gasless, all on-chain.

[![Solidity](https://img.shields.io/badge/Solidity-0.8.24-363636?logo=solidity)](https://soliditylang.org/)
[![Base](https://img.shields.io/badge/Base-Sepolia-0052FF?logo=coinbase)](https://base.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Layer 3: OpenClaw Agent                                  │
│  WhatsApp ↔ Orchestrator ↔ Contract Reader ↔ Claim Exec  │
├──────────────────────────────────────────────────────────┤
│  Layer 2: Coinbase Infrastructure                         │
│  Paymaster (gasless) · On-Ramp (fiat→USDC) · Smart Wallet│
├──────────────────────────────────────────────────────────┤
│  Layer 1: Base Blockchain                                 │
│  PolicyNFT · ClaimsContract · LiquidityPool · Factory     │
└──────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
contracts/
├── PolicyNFT.sol          # ERC-721 policy NFTs with coverage terms
├── ClaimsContract.sol     # 6-check claim verification + payout
├── LiquidityPool.sol      # Per-tenant USDC premium pool
└── TenantFactory.sol      # Deploys isolated contract sets per tenant

agent/
├── main.py                # Flask orchestrator + WhatsApp webhook
├── whatsapp.py            # Meta Cloud API message handler
├── contract_reader.py     # Web3 on-chain state reader
└── claim_executor.py      # Claim transaction builder

payments/
├── onramp.py              # Coinbase fiat → USDC conversion
└── paymaster.py           # ERC-4337 gas sponsorship

api/                        # SaaS Admin REST API
├── app.py                 # Flask entry point
├── auth.py                # API key middleware
├── models.py              # Pydantic schemas
└── routes/                # Tenant, policy, claim, analytics endpoints

dashboard/                  # Admin dashboard (HTML/CSS/JS)
├── index.html
├── css/styles.css
└── js/app.js

scripts/
├── deploy.js              # Deploy TenantFactory + demo tenant
└── seed.js                # Seed pool with USDC + mint sample policy

tests/
├── contracts/             # Hardhat tests (22 tests)
└── agent/                 # Pytest agent tests (17 tests)
```

## 🚀 Quick Start

### Prerequisites

- Node.js ≥ 18
- Python ≥ 3.10
- Git

### 1. Install dependencies

```bash
npm install
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env .env.local   # Edit .env with your keys
```

Required keys:
- `PRIVATE_KEY` — Deployer wallet private key
- `WHATSAPP_TOKEN` — Meta Cloud API token
- `COINBASE_API_KEY` — Coinbase Developer Platform key

### 3. Compile & test contracts

```bash
npm run compile
npm run test
```

### 4. Deploy to Base Sepolia

```bash
npm run deploy:sepolia
npm run seed
```

### 5. Start the agent

```bash
python -m agent.main
```

### 6. Start the dashboard API

```bash
python -m api.app
```

## 🧪 Testing

```bash
# Smart contract tests (22 tests)
npm run test

# Python agent tests (17 tests)
python -m pytest tests/agent/ -v
```

## 🔑 Key Features

| Feature | How |
|---------|-----|
| **Multi-tenant SaaS** | TenantFactory deploys isolated contract sets per insurer |
| **Gasless UX** | Coinbase Paymaster sponsors all gas fees |
| **Fiat on-ramp** | Users pay premiums in local fiat, auto-converted to USDC |
| **WhatsApp-first** | Full policy lifecycle via conversational AI |
| **6-check claims** | Automated verification: active, not expired, within limits, no duplicates, evidence present |
| **Policy NFTs** | Immutable coverage terms stored on-chain as ERC-721 |
| **Admin dashboard** | Real-time analytics, tenant management, claim approval |

## 📜 Smart Contract Flow

```
1. TenantFactory.deployTenantContracts("insurer-id")
   → Deploys PolicyNFT + ClaimsContract + LiquidityPool

2. LiquidityPool.depositPremium("insurer-id", amount)
   → User's fiat → USDC → pool

3. PolicyNFT.mintPolicy(tenantId, holder, terms...)
   → Mints policy NFT to user's wallet

4. ClaimsContract.fileClaim(policyId, evidenceHash, amount)
   → 6-check verification → approve/reject → payout from pool
```

## 🛠️ Tech Stack

- **Blockchain**: Solidity 0.8.24, Hardhat, OpenZeppelin v5, Base (Coinbase L2)
- **Backend**: Python, Flask, Web3.py, Pydantic
- **Payments**: Coinbase On-Ramp, Coinbase Paymaster (ERC-4337)
- **Messaging**: WhatsApp Business Cloud API (Meta)
- **Frontend**: Vanilla HTML/CSS/JS (dashboard)

## 📄 License

MIT
