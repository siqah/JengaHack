const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("LiquidityPool", function () {
  let liquidityPool, mockUsdc;
  let owner, claimsCaller, depositor, recipient;
  const tenantId = "test-tenant";

  beforeEach(async function () {
    [owner, claimsCaller, depositor, recipient] = await ethers.getSigners();

    // For simplicity, use owner address as mock USDC — in full tests use a mock ERC20
    const LiquidityPool = await ethers.getContractFactory("LiquidityPool");
    liquidityPool = await LiquidityPool.deploy(owner.address);
    await liquidityPool.waitForDeployment();

    // Set claims contract
    await liquidityPool.setClaimsContract(claimsCaller.address);
  });

  describe("Admin", function () {
    it("should set claims contract", async function () {
      expect(await liquidityPool.claimsContract()).to.equal(
        claimsCaller.address,
      );
    });

    it("should reject non-owner setting claims contract", async function () {
      await expect(
        liquidityPool.connect(depositor).setClaimsContract(depositor.address),
      ).to.be.reverted;
    });
  });

  describe("Views", function () {
    it("should return zero balance for new tenant", async function () {
      const balance = await liquidityPool.getPoolBalance(tenantId);
      expect(balance).to.equal(0);
    });

    it("should return pool stats", async function () {
      const [balance, premiums, payouts] =
        await liquidityPool.getPoolStats(tenantId);
      expect(balance).to.equal(0);
      expect(premiums).to.equal(0);
      expect(payouts).to.equal(0);
    });
  });

  describe("Access Control", function () {
    it("should reject payout from non-claims contract", async function () {
      await expect(
        liquidityPool
          .connect(depositor)
          .releasePayout(tenantId, recipient.address, 100),
      ).to.be.revertedWith("Pool: only ClaimsContract");
    });
  });
});
