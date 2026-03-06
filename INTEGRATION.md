# ChainSure Integration Guide

How the smart contracts connect to every other layer in the system.

---

## 1. Deployed Contract Addresses

After running `npm run deploy:sepolia`, a `deployments.json` file is created:

```json
{
  "network": "baseSepolia",
  "contracts": {
    "PolicyNFT":      "0x...",
    "ClaimsContract": "0x...",
    "LiquidityPool":  "0x...",
    "USDC":           "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
  }
}
```

**Every other layer reads this file** (or loads the addresses from `.env`) to know where the contracts live on Base.

---

## 2. Contract ABIs

After `npm run compile`, ABIs are generated in `artifacts/contracts/`:

| Contract | ABI Location |
|---|---|
| PolicyNFT | `artifacts/contracts/PolicyNFT.sol/PolicyNFT.json` |
| ClaimsContract | `artifacts/contracts/ClaimsContract.sol/ClaimsContract.json` |
| LiquidityPool | `artifacts/contracts/LiquidityPool.sol/LiquidityPool.json` |

Python layers load these ABIs via:
```python
import json
with open("artifacts/contracts/PolicyNFT.sol/PolicyNFT.json") as f:
    abi = json.load(f)["abi"]
```

---

## 3. Payments → Contracts

### `payments/onramp.py` → LiquidityPool

**Flow**: User pays fiat → Coinbase On-Ramp converts to USDC → USDC deposited into LiquidityPool.

```
User (fiat)
  │
  ▼
Coinbase On-Ramp API  ──→  USDC arrives in system wallet
  │
  ▼
onramp.py calls:
  1. usdc.approve(LiquidityPool.address, amount)
  2. LiquidityPool.depositPremium(amount)
```

**Key function**: `LiquidityPool.depositPremium(uint256 amount)`
- Requires prior USDC approval via `usdc.approve(poolAddress, amount)`
- Emits `PremiumDeposited(from, amount)` event

### `payments/paymaster.py` → Gas Sponsorship

**Flow**: User transactions are sent through Coinbase Paymaster so users never pay gas.

```
User action (via WhatsApp)
  │
  ▼
paymaster.py wraps the transaction with:
  - Coinbase Paymaster RPC endpoint
  - UserOperation with sponsored gas
  │
  ▼
Transaction executes on Base with zero gas cost to user
```

**No direct contract call** — the Paymaster sits at the RPC/bundler level. It wraps any contract call (mint policy, file claim) so gas is sponsored.

**Environment variables needed**:
- `COINBASE_PAYMASTER_URL` — Paymaster RPC endpoint from Coinbase Developer Platform

---

## 4. Agent → Contracts

### `agent/contract_reader.py` → PolicyNFT (Read-Only)

**Purpose**: Read live policy state from Base to answer user queries via WhatsApp.

```python
from web3 import Web3

w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
policy_nft = w3.eth.contract(address=POLICY_NFT_ADDR, abi=policy_abi)

# Read a user's policy
policy = policy_nft.functions.getPolicy(token_id).call()
# Returns: (policyType, coverageAmount, premiumPaid, startDate, endDate, holder, claimed)

is_active = policy_nft.functions.isActive(token_id).call()
# Returns: True/False
```

**Key read functions**:
| Function | Returns | Used For |
|---|---|---|
| `getPolicy(tokenId)` | Full policy struct | Displaying policy details to user |
| `isActive(tokenId)` | bool | Checking if user can file a claim |
| `totalPolicies()` | uint256 | Dashboard / stats |

### `agent/claim_executor.py` → ClaimsContract (Write)

**Purpose**: Build and broadcast claim transactions on behalf of the user.

```python
claims = w3.eth.contract(address=CLAIMS_ADDR, abi=claims_abi)

# 1. User files a claim via WhatsApp
tx = claims.functions.fileClaim(
    token_id,
    amount,          # requested payout in USDC (6 decimals)
    "Crop damage from drought"
).build_transaction({
    'from': user_wallet,
    'nonce': w3.eth.get_transaction_count(user_wallet),
    'gas': 300000,
})

# 2. Transaction is signed and sent (via Paymaster for gasless UX)
signed = w3.eth.account.sign_transaction(tx, private_key)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
```

**Key write functions**:
| Function | Caller | Action |
|---|---|---|
| `fileClaim(tokenId, amount, description)` | User (via agent) | Submits a new claim |
| `approveClaim(claimId)` | Owner/Oracle | Approves after off-chain checks |
| `processClaimPayout(claimId)` | Owner/Oracle | Runs 6-check verification + pays out |

### `agent/main.py` — Orchestrator

Ties everything together:

```
WhatsApp message arrives
  │
  ▼
main.py (OpenClaw agent)
  ├── "What's my policy?"    → contract_reader.py → PolicyNFT.getPolicy()
  ├── "I want to file claim" → claim_executor.py  → ClaimsContract.fileClaim()
  ├── "Buy insurance"        → onramp.py          → Coinbase On-Ramp → LiquidityPool
  └── "Help / Explain"       → NLP response (no contract call)
```

---

## 5. Scripts → Contracts

### `scripts/deploy.js`

Deploys contracts in dependency order and wires them:

```
1. Deploy PolicyNFT
2. Deploy LiquidityPool(usdcAddress)
3. Deploy ClaimsContract(policyNFT, liquidityPool)
4. LiquidityPool.setClaimsContract(claimsContract)   ← authorises payouts
5. PolicyNFT.transferOwnership(claimsContract)        ← allows marking claimed
6. Save addresses → deployments.json
```

### `scripts/seed.js`

Seeds initial liquidity after deployment:

```
1. Read deployments.json
2. USDC.approve(liquidityPool, 10000 USDC)
3. LiquidityPool.depositPremium(10000 USDC)
```

---

## 6. Contract Interaction Map

```
┌─────────────────────────────────────────────────────────┐
│                    WhatsApp User                         │
│              (sends message via Meta API)                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  AGENT LAYER (Python)                                    │
│                                                          │
│  main.py ─── whatsapp.py (receive/send messages)         │
│     │                                                    │
│     ├── contract_reader.py ──READ──→ PolicyNFT           │
│     ├── claim_executor.py ──WRITE──→ ClaimsContract      │
│     └── (onramp.py / paymaster.py)                       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  PAYMENTS LAYER (Python)                                 │
│                                                          │
│  onramp.py ────── Coinbase On-Ramp ── USDC ──→ Pool      │
│  paymaster.py ─── Coinbase Paymaster ── sponsors gas      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  CONTRACTS (Solidity on Base)                            │
│                                                          │
│  PolicyNFT ◄──── owns ──── ClaimsContract                │
│      │                          │                        │
│      │  getPolicy()             │  fileClaim()           │
│      │  isActive()              │  approveClaim()        │
│      │  markClaimed()           │  processClaimPayout()  │
│      │                          │                        │
│      └──────────────────────────┼────→ LiquidityPool     │
│                                 │          │             │
│                                 │  releasePayout()       │
│                                 │  depositPremium()      │
│                                 │  getPoolBalance()      │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Environment Variables (`.env`)

| Variable | Used By | Purpose |
|---|---|---|
| `DEPLOYER_PRIVATE_KEY` | deploy.js, seed.js | Signs deployment transactions |
| `BASE_SEPOLIA_RPC_URL` | All layers | Connect to Base Sepolia |
| `BASE_MAINNET_RPC_URL` | All layers | Connect to Base Mainnet |
| `USDC_ADDRESS_SEPOLIA` | deploy.js, payments | USDC contract on testnet |
| `COINBASE_API_KEY` | onramp.py | Coinbase On-Ramp authentication |
| `COINBASE_PAYMASTER_URL` | paymaster.py | Gas sponsorship endpoint |
| `WHATSAPP_API_TOKEN` | whatsapp.py | Meta Cloud API authentication |
| `OPENCLAW_API_KEY` | main.py | AI agent API access |

---

## 8. End-to-End Flows

### Flow A: Buying a Policy

```
1. User sends "I want crop insurance" via WhatsApp
2. whatsapp.py receives → main.py parses intent
3. Agent explains options, user confirms
4. onramp.py initiates Coinbase On-Ramp (fiat → USDC)
5. onramp.py deposits premium → LiquidityPool.depositPremium()
6. main.py calls PolicyNFT.mintPolicy() → NFT minted to user
7. Agent sends confirmation + policy ID back via WhatsApp
```

### Flow B: Filing a Claim

```
1. User sends "My crops were damaged, I want to claim" via WhatsApp
2. whatsapp.py receives → main.py parses intent
3. contract_reader.py checks PolicyNFT.isActive(tokenId) → true
4. claim_executor.py calls ClaimsContract.fileClaim(tokenId, amount, description)
5. Transaction sent via paymaster.py (gasless for user)
6. Agent confirms claim filed, provides claim ID
```

### Flow C: Claim Payout

```
1. Oracle / admin reviews claim (off-chain verification if needed)
2. Admin calls ClaimsContract.approveClaim(claimId)
3. Admin calls ClaimsContract.processClaimPayout(claimId)
   → 6-check verification runs on-chain
   → PolicyNFT.markClaimed(tokenId) called
   → LiquidityPool.releasePayout(user, amount) sends USDC
4. Agent notifies user via WhatsApp: "Your claim has been paid!"
```
