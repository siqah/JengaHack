// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title PolicyNFT
 * @notice Mints insurance policy NFTs with all coverage terms encoded on-chain.
 *         Each NFT represents a unique insurance policy for a holder.
 */
contract PolicyNFT is ERC721, Ownable {
    // ── Types ──────────────────────────────────────────────────────────
    struct Policy {
        string policyType; // e.g. "crop", "health", "travel"
        uint256 coverageAmount; // max payout in USDC (6 decimals)
        uint256 premiumPaid; // premium amount in USDC (6 decimals)
        uint256 startDate; // policy start (unix timestamp)
        uint256 endDate; // policy expiry (unix timestamp)
        address holder; // wallet that owns this policy
        bool claimed; // whether a claim has been paid out
    }

    // ── State ──────────────────────────────────────────────────────────
    uint256 private _nextTokenId;
    mapping(uint256 => Policy) private _policies;

    // ── Events ─────────────────────────────────────────────────────────
    event PolicyMinted(
        uint256 indexed tokenId,
        address indexed holder,
        string policyType,
        uint256 coverageAmount,
        uint256 premiumPaid,
        uint256 startDate,
        uint256 endDate
    );

    event PolicyClaimed(uint256 indexed tokenId);

    // ── Constructor ────────────────────────────────────────────────────
    constructor() ERC721("ChainSure Policy", "CSPOL") Ownable(msg.sender) {
        _nextTokenId = 1;
    }

    // ── External functions ─────────────────────────────────────────────

    /**
     * @notice Mint a new policy NFT to the given holder.
     * @dev    Only the contract owner (deployer / system) can mint.
     */
    function mintPolicy(
        address holder,
        string calldata policyType,
        uint256 coverageAmount,
        uint256 premiumPaid,
        uint256 durationDays
    ) external onlyOwner returns (uint256 tokenId) {
        tokenId = _nextTokenId++;

        uint256 startDate = block.timestamp;
        uint256 endDate = startDate + (durationDays * 1 days);

        _policies[tokenId] = Policy({
            policyType: policyType,
            coverageAmount: coverageAmount,
            premiumPaid: premiumPaid,
            startDate: startDate,
            endDate: endDate,
            holder: holder,
            claimed: false
        });

        _safeMint(holder, tokenId);

        emit PolicyMinted(
            tokenId,
            holder,
            policyType,
            coverageAmount,
            premiumPaid,
            startDate,
            endDate
        );
    }

    // ── View functions ─────────────────────────────────────────────────

    /**
     * @notice Return full policy details for a given token ID.
     */
    function getPolicy(uint256 tokenId) external view returns (Policy memory) {
        require(
            _ownerOf(tokenId) != address(0),
            "PolicyNFT: policy does not exist"
        );
        return _policies[tokenId];
    }

    /**
     * @notice Check whether a policy is currently active (within its date range).
     */
    function isActive(uint256 tokenId) external view returns (bool) {
        require(
            _ownerOf(tokenId) != address(0),
            "PolicyNFT: policy does not exist"
        );
        Policy storage p = _policies[tokenId];
        return (block.timestamp >= p.startDate &&
            block.timestamp <= p.endDate &&
            !p.claimed);
    }

    /**
     * @notice Returns total number of policies minted.
     */
    function totalPolicies() external view returns (uint256) {
        return _nextTokenId - 1;
    }

    // ── Internal helpers (called by ClaimsContract via owner) ──────────

    /**
     * @notice Mark a policy as claimed. Only callable by the owner.
     */
    function markClaimed(uint256 tokenId) external onlyOwner {
        require(
            _ownerOf(tokenId) != address(0),
            "PolicyNFT: policy does not exist"
        );
        require(!_policies[tokenId].claimed, "PolicyNFT: already claimed");
        _policies[tokenId].claimed = true;
        emit PolicyClaimed(tokenId);
    }
}
