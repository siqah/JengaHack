// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title LiquidityPool
 * @notice Holds premium funds (USDC) per tenant and releases payouts
 *         on approved claims. Only the ClaimsContract can trigger payouts.
 */
contract LiquidityPool is Ownable {
    // ──────────────────────────────────────────────
    //  State
    // ──────────────────────────────────────────────

    IERC20 public usdc;

    /// @dev tenantId → total USDC balance
    mapping(string => uint256) public tenantBalances;

    /// @dev tenantId → total premiums collected
    mapping(string => uint256) public totalPremiums;

    /// @dev tenantId → total payouts released
    mapping(string => uint256) public totalPayouts;

    /// @dev address allowed to call releasePayout (ClaimsContract)
    address public claimsContract;

    // ──────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────

    event PremiumDeposited(string tenantId, address indexed depositor, uint256 amount);
    event PayoutReleased(string tenantId, address indexed recipient, uint256 amount);
    event ClaimsContractSet(address indexed claimsContract);

    // ──────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────

    constructor(address _usdcAddress) Ownable(msg.sender) {
        usdc = IERC20(_usdcAddress);
    }

    // ──────────────────────────────────────────────
    //  Admin
    // ──────────────────────────────────────────────

    /**
     * @notice Set the ClaimsContract address that is authorized to release payouts.
     */
    function setClaimsContract(address _claimsContract) external onlyOwner {
        claimsContract = _claimsContract;
        emit ClaimsContractSet(_claimsContract);
    }

    // ──────────────────────────────────────────────
    //  Deposits
    // ──────────────────────────────────────────────

    /**
     * @notice Deposit USDC premium into a tenant's pool.
     * @dev Caller must have approved this contract to spend `amount` USDC.
     */
    function depositPremium(string calldata tenantId, uint256 amount) external {
        require(amount > 0, "Pool: zero amount");
        require(
            usdc.transferFrom(msg.sender, address(this), amount),
            "Pool: USDC transfer failed"
        );

        tenantBalances[tenantId] += amount;
        totalPremiums[tenantId] += amount;

        emit PremiumDeposited(tenantId, msg.sender, amount);
    }

    // ──────────────────────────────────────────────
    //  Payouts
    // ──────────────────────────────────────────────

    /**
     * @notice Release a payout from the tenant's pool to a recipient.
     * @dev Only callable by the ClaimsContract.
     */
    function releasePayout(
        string calldata tenantId,
        address recipient,
        uint256 amount
    ) external {
        require(msg.sender == claimsContract, "Pool: only ClaimsContract");
        require(tenantBalances[tenantId] >= amount, "Pool: insufficient balance");
        require(recipient != address(0), "Pool: zero address recipient");

        tenantBalances[tenantId] -= amount;
        totalPayouts[tenantId]  += amount;

        require(usdc.transfer(recipient, amount), "Pool: USDC transfer failed");

        emit PayoutReleased(tenantId, recipient, amount);
    }

    // ──────────────────────────────────────────────
    //  Views
    // ──────────────────────────────────────────────

    function getPoolBalance(string calldata tenantId) external view returns (uint256) {
        return tenantBalances[tenantId];
    }

    function getPoolStats(string calldata tenantId)
        external
        view
        returns (uint256 balance, uint256 premiums, uint256 payouts)
    {
        return (tenantBalances[tenantId], totalPremiums[tenantId], totalPayouts[tenantId]);
    }
}
