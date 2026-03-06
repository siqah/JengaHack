// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./PolicyNFT.sol";
import "./LiquidityPool.sol";

/**
 * @title ClaimsContract
 * @notice Manages claim submissions and executes a 6-check verification flow.
 *         On approval, triggers payout from the LiquidityPool.
 */
contract ClaimsContract is Ownable {
    // ── Types ──────────────────────────────────────────────────────────
    enum ClaimStatus {
        Pending,
        Approved,
        Rejected,
        PaidOut
    }

    struct Claim {
        uint256 policyTokenId;
        address claimant;
        string description;
        uint256 amount; // requested payout (≤ coverageAmount)
        ClaimStatus status;
        uint256 filedAt;
        bool fraudFlagged;
    }

    // ── State ──────────────────────────────────────────────────────────
    PolicyNFT public policyNFT;
    LiquidityPool public liquidityPool;

    uint256 public nextClaimId;
    mapping(uint256 => Claim) public claims; // claimId → Claim
    mapping(uint256 => bool) public policyHasClaim; // tokenId → has open/paid claim

    uint256 public claimWindowDays = 30; // days after policy end that claims are still accepted

    // ── Events ─────────────────────────────────────────────────────────
    event ClaimFiled(
        uint256 indexed claimId,
        uint256 indexed policyTokenId,
        address indexed claimant,
        uint256 amount,
        string description
    );
    event ClaimApproved(uint256 indexed claimId);
    event ClaimRejected(uint256 indexed claimId, string reason);
    event ClaimPaidOut(
        uint256 indexed claimId,
        address indexed recipient,
        uint256 amount
    );
    event FraudFlagged(uint256 indexed claimId);

    // ── Constructor ────────────────────────────────────────────────────
    constructor(
        address _policyNFT,
        address _liquidityPool
    ) Ownable(msg.sender) {
        require(_policyNFT != address(0), "Claims: zero PolicyNFT address");
        require(
            _liquidityPool != address(0),
            "Claims: zero LiquidityPool address"
        );
        policyNFT = PolicyNFT(_policyNFT);
        liquidityPool = LiquidityPool(_liquidityPool);
        nextClaimId = 1;
    }

    // ── External: Claim Lifecycle ──────────────────────────────────────

    /**
     * @notice File a new claim against a policy NFT.
     * @param tokenId    The policy NFT token ID.
     * @param amount     The requested payout amount (must be ≤ coverage).
     * @param description Free-text description of the claim.
     */
    function fileClaim(
        uint256 tokenId,
        uint256 amount,
        string calldata description
    ) external returns (uint256 claimId) {
        // Caller must be the policy holder
        require(
            policyNFT.ownerOf(tokenId) == msg.sender,
            "Claims: caller is not the policy holder"
        );

        // No duplicate claims per policy
        require(!policyHasClaim[tokenId], "Claims: policy already has a claim");

        // Policy must exist and fetch its data
        PolicyNFT.Policy memory pol = policyNFT.getPolicy(tokenId);
        require(
            amount > 0 && amount <= pol.coverageAmount,
            "Claims: invalid amount"
        );

        claimId = nextClaimId++;

        claims[claimId] = Claim({
            policyTokenId: tokenId,
            claimant: msg.sender,
            description: description,
            amount: amount,
            status: ClaimStatus.Pending,
            filedAt: block.timestamp,
            fraudFlagged: false
        });

        policyHasClaim[tokenId] = true;

        emit ClaimFiled(claimId, tokenId, msg.sender, amount, description);
    }

    /**
     * @notice Approve a pending claim (owner / oracle).
     */
    function approveClaim(uint256 claimId) external onlyOwner {
        Claim storage c = claims[claimId];
        require(c.claimant != address(0), "Claims: claim does not exist");
        require(c.status == ClaimStatus.Pending, "Claims: not pending");
        c.status = ClaimStatus.Approved;
        emit ClaimApproved(claimId);
    }

    /**
     * @notice Reject a pending claim (owner / oracle).
     */
    function rejectClaim(
        uint256 claimId,
        string calldata reason
    ) external onlyOwner {
        Claim storage c = claims[claimId];
        require(c.claimant != address(0), "Claims: claim does not exist");
        require(c.status == ClaimStatus.Pending, "Claims: not pending");
        c.status = ClaimStatus.Rejected;
        policyHasClaim[c.policyTokenId] = false; // allow re-filing if rejected
        emit ClaimRejected(claimId, reason);
    }

    /**
     * @notice Flag a claim for suspected fraud.
     */
    function flagFraud(uint256 claimId) external onlyOwner {
        Claim storage c = claims[claimId];
        require(c.claimant != address(0), "Claims: claim does not exist");
        c.fraudFlagged = true;
        emit FraudFlagged(claimId);
    }

    /**
     * @notice Process payout for an approved claim after the 6-check verification.
     * @dev    Runs all 6 checks, then calls LiquidityPool.releasePayout().
     */
    function processClaimPayout(uint256 claimId) external onlyOwner {
        Claim storage c = claims[claimId];
        require(c.claimant != address(0), "Claims: claim does not exist");
        require(c.status == ClaimStatus.Approved, "Claims: not approved");

        // ── 6-Check Verification ───────────────────────────────────────
        PolicyNFT.Policy memory pol = policyNFT.getPolicy(c.policyTokenId);

        // Check 1: Policy is currently active (or within claim window)
        require(
            block.timestamp <= pol.endDate + (claimWindowDays * 1 days),
            "Claims: claim window expired"
        );

        // Check 2: Policy has not already been claimed / paid out
        require(!pol.claimed, "Claims: policy already claimed");

        // Check 3: Claim was filed within the allowed claim window
        require(
            c.filedAt <= pol.endDate + (claimWindowDays * 1 days),
            "Claims: filed outside claim window"
        );

        // Check 4: Requested amount does not exceed coverage
        require(
            c.amount <= pol.coverageAmount,
            "Claims: amount exceeds coverage"
        );

        // Check 5: No fraud flag
        require(!c.fraudFlagged, "Claims: flagged for fraud");

        // Check 6: Pool has sufficient liquidity
        require(
            liquidityPool.getPoolBalance() >= c.amount,
            "Claims: insufficient pool liquidity"
        );

        // ── Execute Payout ─────────────────────────────────────────────
        c.status = ClaimStatus.PaidOut;

        // Mark policy as claimed on the NFT contract
        policyNFT.markClaimed(c.policyTokenId);

        // Release USDC from pool to claimant
        liquidityPool.releasePayout(c.claimant, c.amount);

        emit ClaimPaidOut(claimId, c.claimant, c.amount);
    }

    // ── View functions ─────────────────────────────────────────────────

    /**
     * @notice Get full claim details.
     */
    function getClaim(uint256 claimId) external view returns (Claim memory) {
        require(
            claims[claimId].claimant != address(0),
            "Claims: does not exist"
        );
        return claims[claimId];
    }

    /**
     * @notice Returns total number of claims filed.
     */
    function totalClaims() external view returns (uint256) {
        return nextClaimId - 1;
    }

    /**
     * @notice Update the claim window (in days). Owner only.
     */
    function setClaimWindowDays(uint256 _days) external onlyOwner {
        claimWindowDays = _days;
    }
}
