// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./PolicyNFT.sol";
import "./LiquidityPool.sol";

/**
 * @title ClaimsContract
 * @notice Executes a 6-check verification on insurance claims and triggers
 *         payouts from the LiquidityPool when all checks pass.
 */
contract ClaimsContract is Ownable {
    // ──────────────────────────────────────────────
    //  Types
    // ──────────────────────────────────────────────

    enum ClaimStatus { Filed, UnderReview, Approved, Rejected, PaidOut }

    struct Claim {
        uint256     policyId;
        address     claimant;
        string      tenantId;
        bytes32     evidenceHash;
        uint256     amount;
        uint256     filedAt;
        ClaimStatus status;
        string      rejectionReason;
    }

    // ──────────────────────────────────────────────
    //  State
    // ──────────────────────────────────────────────

    PolicyNFT     public policyNFT;
    LiquidityPool public liquidityPool;

    uint256 private _nextClaimId;

    /// @dev claimId → Claim
    mapping(uint256 => Claim) public claims;

    /// @dev policyId → list of claim IDs
    mapping(uint256 => uint256[]) public policyClaims;

    /// @dev tenantId → list of claim IDs
    mapping(string => uint256[]) public tenantClaims;

    /// @dev tenantId → authorized reviewer
    mapping(string => mapping(address => bool)) public authorizedReviewers;

    // ──────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────

    event ClaimFiled(uint256 indexed claimId, uint256 indexed policyId, address claimant, bytes32 evidenceHash);
    event ClaimApproved(uint256 indexed claimId, uint256 amount);
    event ClaimRejected(uint256 indexed claimId, string reason);
    event ClaimPaidOut(uint256 indexed claimId, address recipient, uint256 amount);
    event ReviewerAuthorized(address indexed reviewer, string tenantId);

    // ──────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────

    constructor(
        address _policyNFT,
        address _liquidityPool
    ) Ownable(msg.sender) {
        policyNFT     = PolicyNFT(_policyNFT);
        liquidityPool = LiquidityPool(_liquidityPool);
    }

    // ──────────────────────────────────────────────
    //  Admin
    // ──────────────────────────────────────────────

    function authorizeReviewer(address reviewer, string calldata tenantId) external onlyOwner {
        authorizedReviewers[tenantId][reviewer] = true;
        emit ReviewerAuthorized(reviewer, tenantId);
    }

    // ──────────────────────────────────────────────
    //  File a Claim
    // ──────────────────────────────────────────────

    /**
     * @notice File a claim against a policy.
     * @param policyId  The NFT policy ID.
     * @param evidenceHash  Keccak256 hash of the supporting evidence (IPFS CID, etc.)
     * @param amount  Requested payout amount.
     */
    function fileClaim(
        uint256 policyId,
        bytes32 evidenceHash,
        uint256 amount
    ) external returns (uint256) {
        PolicyNFT.Policy memory policy = policyNFT.getPolicy(policyId);

        // Only the policy holder can file a claim
        require(policy.holder == msg.sender, "Claims: not policy holder");

        uint256 claimId = _nextClaimId++;

        claims[claimId] = Claim({
            policyId:        policyId,
            claimant:        msg.sender,
            tenantId:        policy.tenantId,
            evidenceHash:    evidenceHash,
            amount:          amount,
            filedAt:         block.timestamp,
            status:          ClaimStatus.Filed,
            rejectionReason: ""
        });

        policyClaims[policyId].push(claimId);
        tenantClaims[policy.tenantId].push(claimId);

        emit ClaimFiled(claimId, policyId, msg.sender, evidenceHash);
        return claimId;
    }

    // ──────────────────────────────────────────────
    //  6-Check Verification
    // ──────────────────────────────────────────────

    /**
     * @notice Run the 6-check automated verification.
     * @dev Checks: (1) policy exists, (2) policy active, (3) not expired,
     *      (4) amount within coverage limit, (5) no duplicate claims,
     *      (6) evidence hash is non-zero.
     *      Returns (passed, failReason).
     */
    function verifyClaim(uint256 claimId) public view returns (bool passed, string memory failReason) {
        Claim storage claim = claims[claimId];
        PolicyNFT.Policy memory policy = policyNFT.getPolicy(claim.policyId);

        // Check 1: Policy exists (holder != zero address)
        if (policy.holder == address(0)) {
            return (false, "Check 1: Policy does not exist");
        }

        // Check 2: Policy is active
        if (policy.status != PolicyNFT.PolicyStatus.Active) {
            return (false, "Check 2: Policy is not active");
        }

        // Check 3: Policy not expired
        if (block.timestamp > policy.endDate) {
            return (false, "Check 3: Policy has expired");
        }

        // Check 4: Claim amount within coverage limit
        if (claim.amount > policy.coverageLimit) {
            return (false, "Check 4: Amount exceeds coverage limit");
        }

        // Check 5: No existing approved/paid claim on this policy
        uint256[] storage existingClaims = policyClaims[claim.policyId];
        for (uint256 i = 0; i < existingClaims.length; i++) {
            if (existingClaims[i] != claimId) {
                ClaimStatus s = claims[existingClaims[i]].status;
                if (s == ClaimStatus.Approved || s == ClaimStatus.PaidOut) {
                    return (false, "Check 5: Duplicate - policy already has approved claim");
                }
            }
        }

        // Check 6: Evidence hash is non-zero
        if (claim.evidenceHash == bytes32(0)) {
            return (false, "Check 6: Missing evidence");
        }

        return (true, "");
    }

    // ──────────────────────────────────────────────
    //  Approve / Reject
    // ──────────────────────────────────────────────

    /**
     * @notice Approve a claim after verification passes.
     */
    function approveClaim(uint256 claimId) external {
        Claim storage claim = claims[claimId];
        require(
            msg.sender == owner() || authorizedReviewers[claim.tenantId][msg.sender],
            "Claims: not authorized reviewer"
        );
        require(claim.status == ClaimStatus.Filed, "Claims: invalid status");

        (bool passed, string memory reason) = verifyClaim(claimId);
        require(passed, reason);

        claim.status = ClaimStatus.Approved;
        emit ClaimApproved(claimId, claim.amount);
    }

    /**
     * @notice Reject a claim with a reason.
     */
    function rejectClaim(uint256 claimId, string calldata reason) external {
        Claim storage claim = claims[claimId];
        require(
            msg.sender == owner() || authorizedReviewers[claim.tenantId][msg.sender],
            "Claims: not authorized reviewer"
        );
        require(
            claim.status == ClaimStatus.Filed || claim.status == ClaimStatus.UnderReview,
            "Claims: invalid status"
        );

        claim.status = ClaimStatus.Rejected;
        claim.rejectionReason = reason;
        emit ClaimRejected(claimId, reason);
    }

    /**
     * @notice Execute payout for an approved claim via the LiquidityPool.
     */
    function executePayout(uint256 claimId) external {
        Claim storage claim = claims[claimId];
        require(claim.status == ClaimStatus.Approved, "Claims: not approved");
        require(
            msg.sender == owner() || authorizedReviewers[claim.tenantId][msg.sender],
            "Claims: not authorized"
        );

        claim.status = ClaimStatus.PaidOut;

        // Update policy status to Claimed
        policyNFT.updatePolicyStatus(claim.policyId, PolicyNFT.PolicyStatus.Claimed);

        // Release funds from pool
        liquidityPool.releasePayout(claim.tenantId, claim.claimant, claim.amount);

        emit ClaimPaidOut(claimId, claim.claimant, claim.amount);
    }

    // ──────────────────────────────────────────────
    //  Views
    // ──────────────────────────────────────────────

    function getClaim(uint256 claimId) external view returns (Claim memory) {
        return claims[claimId];
    }

    function getPolicyClaims(uint256 policyId) external view returns (uint256[] memory) {
        return policyClaims[policyId];
    }

    function getTenantClaims(string calldata tenantId) external view returns (uint256[] memory) {
        return tenantClaims[tenantId];
    }
}
