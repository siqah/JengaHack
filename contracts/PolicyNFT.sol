// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title PolicyNFT
 * @notice Mints insurance policy NFTs with all coverage terms encoded on-chain.
 *         Each policy is tagged with a tenantId for multi-tenant SaaS isolation.
 */
contract PolicyNFT is ERC721Enumerable, Ownable {
    // ──────────────────────────────────────────────
    //  Types
    // ──────────────────────────────────────────────

    enum PolicyStatus { Active, Expired, Claimed, Cancelled }

    struct Policy {
        string   tenantId;
        address  holder;
        string   coverageType;
        uint256  premiumAmount;
        uint256  coverageLimit;
        uint256  startDate;
        uint256  endDate;
        PolicyStatus status;
        string   metadataURI;     // off-chain details (IPFS hash, etc.)
    }

    // ──────────────────────────────────────────────
    //  State
    // ──────────────────────────────────────────────

    uint256 private _nextTokenId;

    /// @dev policyId → Policy
    mapping(uint256 => Policy) public policies;

    /// @dev tenantId → list of policy IDs
    mapping(string => uint256[]) public tenantPolicies;

    /// @dev address → tenantId → authorized to mint
    mapping(address => mapping(string => bool)) public authorizedMinters;

    // ──────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────

    event PolicyMinted(
        uint256 indexed policyId,
        string  tenantId,
        address indexed holder,
        string  coverageType,
        uint256 premiumAmount,
        uint256 coverageLimit,
        uint256 startDate,
        uint256 endDate
    );

    event PolicyStatusUpdated(uint256 indexed policyId, PolicyStatus newStatus);
    event MinterAuthorized(address indexed minter, string tenantId);
    event MinterRevoked(address indexed minter, string tenantId);

    // ──────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────

    constructor() ERC721("ChainSure Policy", "CSPOL") Ownable(msg.sender) {}

    // ──────────────────────────────────────────────
    //  Admin
    // ──────────────────────────────────────────────

    function authorizeMinter(address minter, string calldata tenantId) external onlyOwner {
        authorizedMinters[minter][tenantId] = true;
        emit MinterAuthorized(minter, tenantId);
    }

    function revokeMinter(address minter, string calldata tenantId) external onlyOwner {
        authorizedMinters[minter][tenantId] = false;
        emit MinterRevoked(minter, tenantId);
    }

    // ──────────────────────────────────────────────
    //  Core
    // ──────────────────────────────────────────────

    /**
     * @notice Mint a new policy NFT.
     * @dev Caller must be an authorized minter for the given tenantId, or the owner.
     */
    function mintPolicy(
        string   calldata tenantId,
        address  holder,
        string   calldata coverageType,
        uint256  premiumAmount,
        uint256  coverageLimit,
        uint256  startDate,
        uint256  endDate,
        string   calldata metadataURI
    ) external returns (uint256) {
        require(
            authorizedMinters[msg.sender][tenantId] || msg.sender == owner(),
            "PolicyNFT: not authorized for tenant"
        );
        require(endDate > startDate, "PolicyNFT: invalid date range");
        require(holder != address(0), "PolicyNFT: zero address holder");

        uint256 policyId = _nextTokenId++;

        policies[policyId] = Policy({
            tenantId:     tenantId,
            holder:       holder,
            coverageType: coverageType,
            premiumAmount: premiumAmount,
            coverageLimit: coverageLimit,
            startDate:    startDate,
            endDate:      endDate,
            status:       PolicyStatus.Active,
            metadataURI:  metadataURI
        });

        tenantPolicies[tenantId].push(policyId);

        _safeMint(holder, policyId);

        emit PolicyMinted(
            policyId, tenantId, holder, coverageType,
            premiumAmount, coverageLimit, startDate, endDate
        );

        return policyId;
    }

    // ──────────────────────────────────────────────
    //  Status Management
    // ──────────────────────────────────────────────

    function updatePolicyStatus(uint256 policyId, PolicyStatus newStatus) external {
        require(
            msg.sender == owner() ||
            authorizedMinters[msg.sender][policies[policyId].tenantId],
            "PolicyNFT: not authorized"
        );
        policies[policyId].status = newStatus;
        emit PolicyStatusUpdated(policyId, newStatus);
    }

    // ──────────────────────────────────────────────
    //  Views
    // ──────────────────────────────────────────────

    function getPolicy(uint256 policyId) external view returns (Policy memory) {
        return policies[policyId];
    }

    function getTenantPolicyCount(string calldata tenantId) external view returns (uint256) {
        return tenantPolicies[tenantId].length;
    }

    function getTenantPolicies(string calldata tenantId) external view returns (uint256[] memory) {
        return tenantPolicies[tenantId];
    }

    function isActive(uint256 policyId) public view returns (bool) {
        Policy storage p = policies[policyId];
        return p.status == PolicyStatus.Active && block.timestamp <= p.endDate;
    }
}
