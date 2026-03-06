// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./PolicyNFT.sol";
import "./ClaimsContract.sol";
import "./LiquidityPool.sol";

/**
 * @title TenantFactory
 * @notice Factory contract for the ChainSure SaaS platform.
 *         Deploys a new set of (PolicyNFT, ClaimsContract, LiquidityPool)
 *         for each insurance tenant onboarded to the platform.
 */
contract TenantFactory is Ownable {
    // ──────────────────────────────────────────────
    //  Types
    // ──────────────────────────────────────────────

    struct TenantContracts {
        address policyNFT;
        address claimsContract;
        address liquidityPool;
        bool    exists;
    }

    // ──────────────────────────────────────────────
    //  State
    // ──────────────────────────────────────────────

    /// @dev USDC token address on Base
    address public usdcAddress;

    /// @dev tenantId → deployed contract addresses
    mapping(string => TenantContracts) public tenants;

    /// @dev list of all tenant IDs
    string[] public tenantIds;

    // ──────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────

    event TenantDeployed(
        string  tenantId,
        address policyNFT,
        address claimsContract,
        address liquidityPool
    );

    // ──────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────

    constructor(address _usdcAddress) Ownable(msg.sender) {
        usdcAddress = _usdcAddress;
    }

    // ──────────────────────────────────────────────
    //  Deploy
    // ──────────────────────────────────────────────

    /**
     * @notice Deploy a full contract set for a new insurance tenant.
     * @param tenantId  Unique identifier for the tenant.
     */
    function deployTenantContracts(string calldata tenantId) external onlyOwner {
        require(!tenants[tenantId].exists, "Factory: tenant already exists");

        // 1. Deploy PolicyNFT
        PolicyNFT policyNFT = new PolicyNFT();

        // 2. Deploy LiquidityPool (needs USDC address)
        LiquidityPool liquidityPool = new LiquidityPool(usdcAddress);

        // 3. Deploy ClaimsContract (needs references to PolicyNFT + LiquidityPool)
        ClaimsContract claimsContract = new ClaimsContract(
            address(policyNFT),
            address(liquidityPool)
        );

        // 4. Wire permissions:
        //    - LiquidityPool allows ClaimsContract to release payouts
        liquidityPool.setClaimsContract(address(claimsContract));

        //    - PolicyNFT authorizes ClaimsContract to update policy status
        policyNFT.authorizeMinter(address(claimsContract), tenantId);

        // 5. Transfer ownership to the factory owner (platform admin)
        policyNFT.transferOwnership(msg.sender);
        liquidityPool.transferOwnership(msg.sender);
        claimsContract.transferOwnership(msg.sender);

        // 6. Store tenant record
        tenants[tenantId] = TenantContracts({
            policyNFT:       address(policyNFT),
            claimsContract:  address(claimsContract),
            liquidityPool:   address(liquidityPool),
            exists:          true
        });

        tenantIds.push(tenantId);

        emit TenantDeployed(
            tenantId,
            address(policyNFT),
            address(claimsContract),
            address(liquidityPool)
        );
    }

    // ──────────────────────────────────────────────
    //  Views
    // ──────────────────────────────────────────────

    function getTenantContracts(string calldata tenantId)
        external
        view
        returns (address policyNFT, address claimsContract, address liquidityPool)
    {
        TenantContracts storage tc = tenants[tenantId];
        require(tc.exists, "Factory: tenant not found");
        return (tc.policyNFT, tc.claimsContract, tc.liquidityPool);
    }

    function getTenantCount() external view returns (uint256) {
        return tenantIds.length;
    }

    function getAllTenantIds() external view returns (string[] memory) {
        return tenantIds;
    }
}
