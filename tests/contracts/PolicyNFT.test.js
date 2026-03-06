const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("PolicyNFT", function () {
  let policyNFT;
  let owner, minter, user;
  const tenantId = "test-tenant";

  beforeEach(async function () {
    [owner, minter, user] = await ethers.getSigners();

    const PolicyNFT = await ethers.getContractFactory("PolicyNFT");
    policyNFT = await PolicyNFT.deploy();
    await policyNFT.waitForDeployment();

    // Authorize minter
    await policyNFT.authorizeMinter(minter.address, tenantId);
  });

  describe("Minting", function () {
    it("should mint a policy NFT with correct data", async function () {
      const now = Math.floor(Date.now() / 1000);
      const oneYear = 365 * 24 * 60 * 60;

      await policyNFT
        .connect(minter)
        .mintPolicy(
          tenantId,
          user.address,
          "Crop Insurance",
          ethers.parseUnits("50", 6),
          ethers.parseUnits("5000", 6),
          now,
          now + oneYear,
          "ipfs://QmTest",
        );

      const policy = await policyNFT.getPolicy(0);
      expect(policy.tenantId).to.equal(tenantId);
      expect(policy.holder).to.equal(user.address);
      expect(policy.coverageType).to.equal("Crop Insurance");
      expect(policy.status).to.equal(0); // Active
    });

    it("should reject unauthorized minters", async function () {
      const now = Math.floor(Date.now() / 1000);

      await expect(
        policyNFT
          .connect(user)
          .mintPolicy(
            tenantId,
            user.address,
            "Test",
            100,
            1000,
            now,
            now + 1000,
            "",
          ),
      ).to.be.revertedWith("PolicyNFT: not authorized for tenant");
    });

    it("should reject invalid date range", async function () {
      const now = Math.floor(Date.now() / 1000);

      await expect(
        policyNFT
          .connect(minter)
          .mintPolicy(
            tenantId,
            user.address,
            "Test",
            100,
            1000,
            now,
            now - 1000,
            "",
          ),
      ).to.be.revertedWith("PolicyNFT: invalid date range");
    });

    it("should track tenant policies", async function () {
      const now = Math.floor(Date.now() / 1000);
      const end = now + 365 * 24 * 60 * 60;

      await policyNFT
        .connect(minter)
        .mintPolicy(tenantId, user.address, "Type A", 100, 1000, now, end, "");
      await policyNFT
        .connect(minter)
        .mintPolicy(tenantId, user.address, "Type B", 200, 2000, now, end, "");

      const count = await policyNFT.getTenantPolicyCount(tenantId);
      expect(count).to.equal(2);
    });
  });

  describe("Status Management", function () {
    it("should allow authorized users to update policy status", async function () {
      const now = Math.floor(Date.now() / 1000);
      const end = now + 365 * 24 * 60 * 60;

      await policyNFT
        .connect(minter)
        .mintPolicy(tenantId, user.address, "Test", 100, 1000, now, end, "");

      await policyNFT.connect(minter).updatePolicyStatus(0, 2); // Claimed
      const policy = await policyNFT.getPolicy(0);
      expect(policy.status).to.equal(2);
    });
  });
});
