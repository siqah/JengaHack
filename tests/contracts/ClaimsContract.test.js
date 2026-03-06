const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ClaimsContract", function () {
  let policyNFT, claimsContract, liquidityPool, mockUsdc;
  let owner, user;
  const tenantId = "test-tenant";

  beforeEach(async function () {
    [owner, user] = await ethers.getSigners();

    // Deploy mock USDC
    const MockERC20 = await ethers.getContractFactory("LiquidityPool");
    // For testing, we use a simple approach — deploy with a dummy address
    // In full tests, you'd deploy a mock ERC20

    // Deploy PolicyNFT
    const PolicyNFT = await ethers.getContractFactory("PolicyNFT");
    policyNFT = await PolicyNFT.deploy();
    await policyNFT.waitForDeployment();

    // Deploy LiquidityPool with a dummy USDC (owner address as placeholder)
    const LiquidityPool = await ethers.getContractFactory("LiquidityPool");
    liquidityPool = await LiquidityPool.deploy(owner.address);
    await liquidityPool.waitForDeployment();

    // Deploy ClaimsContract
    const ClaimsContract = await ethers.getContractFactory("ClaimsContract");
    claimsContract = await ClaimsContract.deploy(
      await policyNFT.getAddress(),
      await liquidityPool.getAddress(),
    );
    await claimsContract.waitForDeployment();

    // Wire permissions
    await liquidityPool.setClaimsContract(await claimsContract.getAddress());
    await policyNFT.authorizeMinter(owner.address, tenantId);
    await policyNFT.authorizeMinter(
      await claimsContract.getAddress(),
      tenantId,
    );

    // Mint a test policy
    const now = Math.floor(Date.now() / 1000);
    const oneYear = 365 * 24 * 60 * 60;
    await policyNFT.mintPolicy(
      tenantId,
      user.address,
      "Crop Insurance",
      ethers.parseUnits("50", 6),
      ethers.parseUnits("5000", 6),
      now,
      now + oneYear,
      "",
    );
  });

  describe("Filing Claims", function () {
    it("should allow policy holder to file a claim", async function () {
      const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence"));

      await claimsContract
        .connect(user)
        .fileClaim(0, evidenceHash, ethers.parseUnits("1000", 6));

      const claim = await claimsContract.getClaim(0);
      expect(claim.policyId).to.equal(0);
      expect(claim.claimant).to.equal(user.address);
      expect(claim.status).to.equal(0); // Filed
    });

    it("should reject claims from non-holders", async function () {
      const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence"));

      await expect(
        claimsContract
          .connect(owner)
          .fileClaim(0, evidenceHash, ethers.parseUnits("1000", 6)),
      ).to.be.revertedWith("Claims: not policy holder");
    });
  });

  describe("6-Check Verification", function () {
    it("should pass verification for valid claims", async function () {
      const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence"));

      await claimsContract
        .connect(user)
        .fileClaim(0, evidenceHash, ethers.parseUnits("1000", 6));

      const [passed, reason] = await claimsContract.verifyClaim(0);
      expect(passed).to.be.true;
      expect(reason).to.equal("");
    });

    it("should fail if amount exceeds coverage limit", async function () {
      const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence"));

      // File claim exceeding $5000 limit
      await claimsContract
        .connect(user)
        .fileClaim(0, evidenceHash, ethers.parseUnits("10000", 6));

      const [passed, reason] = await claimsContract.verifyClaim(0);
      expect(passed).to.be.false;
      expect(reason).to.include("Check 4");
    });

    it("should fail if evidence hash is zero", async function () {
      const zeroHash = ethers.ZeroHash;

      await claimsContract
        .connect(user)
        .fileClaim(0, zeroHash, ethers.parseUnits("100", 6));

      const [passed, reason] = await claimsContract.verifyClaim(0);
      expect(passed).to.be.false;
      expect(reason).to.include("Check 6");
    });
  });

  describe("Approval Flow", function () {
    it("should allow owner to approve a valid claim", async function () {
      const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence"));

      await claimsContract
        .connect(user)
        .fileClaim(0, evidenceHash, ethers.parseUnits("1000", 6));

      await claimsContract.connect(owner).approveClaim(0);

      const claim = await claimsContract.getClaim(0);
      expect(claim.status).to.equal(2); // Approved
    });

    it("should allow owner to reject a claim with reason", async function () {
      const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence"));

      await claimsContract
        .connect(user)
        .fileClaim(0, evidenceHash, ethers.parseUnits("1000", 6));

      await claimsContract
        .connect(owner)
        .rejectClaim(0, "Insufficient evidence");

      const claim = await claimsContract.getClaim(0);
      expect(claim.status).to.equal(3); // Rejected
      expect(claim.rejectionReason).to.equal("Insufficient evidence");
    });
  });
});
