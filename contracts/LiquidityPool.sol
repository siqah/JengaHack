// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title LiquidityPool
 * @notice Holds USDC premium funds and releases payouts on approved claims.
 *         Only the authorised ClaimsContract can trigger payouts.
 */
contract LiquidityPool is Ownable {
    // ── State ──────────────────────────────────────────────────────────
    IERC20 public usdc;
    address public claimsContract;

    // ── Events ─────────────────────────────────────────────────────────
    event PremiumDeposited(address indexed from, uint256 amount);
    event PayoutReleased(address indexed to, uint256 amount);
    event ClaimsContractUpdated(address indexed newClaimsContract);

    // ── Modifiers ──────────────────────────────────────────────────────
    modifier onlyClaimsContract() {
        require(
            msg.sender == claimsContract,
            "LiquidityPool: caller is not ClaimsContract"
        );
        _;
    }

    // ── Constructor ────────────────────────────────────────────────────
    constructor(address _usdcAddress) Ownable(msg.sender) {
        require(_usdcAddress != address(0), "LiquidityPool: zero USDC address");
        usdc = IERC20(_usdcAddress);
    }

    // ── Admin functions ────────────────────────────────────────────────

    /**
     * @notice Set the authorised ClaimsContract address.
     * @dev    Only the owner can update this.
     */
    function setClaimsContract(address _claimsContract) external onlyOwner {
        require(_claimsContract != address(0), "LiquidityPool: zero address");
        claimsContract = _claimsContract;
        emit ClaimsContractUpdated(_claimsContract);
    }

    // ── External functions ─────────────────────────────────────────────

    /**
     * @notice Deposit USDC premiums into the pool.
     * @dev    Caller must have approved this contract to spend `amount` USDC first.
     */
    function depositPremium(uint256 amount) external {
        require(amount > 0, "LiquidityPool: zero amount");
        bool success = usdc.transferFrom(msg.sender, address(this), amount);
        require(success, "LiquidityPool: USDC transfer failed");
        emit PremiumDeposited(msg.sender, amount);
    }

    /**
     * @notice Release a payout to an approved claim recipient.
     * @dev    Only callable by the authorised ClaimsContract.
     */
    function releasePayout(
        address recipient,
        uint256 amount
    ) external onlyClaimsContract {
        require(recipient != address(0), "LiquidityPool: zero recipient");
        require(amount > 0, "LiquidityPool: zero amount");
        require(
            usdc.balanceOf(address(this)) >= amount,
            "LiquidityPool: insufficient liquidity"
        );

        bool success = usdc.transfer(recipient, amount);
        require(success, "LiquidityPool: USDC transfer failed");
        emit PayoutReleased(recipient, amount);
    }

    // ── View functions ─────────────────────────────────────────────────

    /**
     * @notice Returns current USDC balance held in the pool.
     */
    function getPoolBalance() external view returns (uint256) {
        return usdc.balanceOf(address(this));
    }
}
