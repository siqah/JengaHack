const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("TenantFactory", function () {
  let factory;
  let owner, other;

  beforeEach(async function () {
    [owner, other] = await ethers.getSigners();

    const TenantFactory = await ethers.getContractFactory("TenantFactory");
    factory = await TenantFactory.deploy(owner.address); // dummy USDC
    await factory.waitForDeployment();
  });

  it("should deploy tenant contracts", async function () {
    await factory.deployTenantContracts("tenant-1");

    const [policyNFT, claims, pool] =
      await factory.getTenantContracts("tenant-1");

    expect(policyNFT).to.not.equal(ethers.ZeroAddress);
    expect(claims).to.not.equal(ethers.ZeroAddress);
    expect(pool).to.not.equal(ethers.ZeroAddress);
  });

  it("should reject duplicate tenant IDs", async function () {
    await factory.deployTenantContracts("tenant-1");

    await expect(factory.deployTenantContracts("tenant-1")).to.be.revertedWith(
      "Factory: tenant already exists",
    );
  });

  it("should track tenant count", async function () {
    await factory.deployTenantContracts("a");
    await factory.deployTenantContracts("b");
    await factory.deployTenantContracts("c");

    expect(await factory.getTenantCount()).to.equal(3);
  });

  it("should only allow owner to deploy", async function () {
    await expect(factory.connect(other).deployTenantContracts("x")).to.be
      .reverted;
  });

  it("should return all tenant IDs", async function () {
    await factory.deployTenantContracts("alpha");
    await factory.deployTenantContracts("beta");

    const ids = await factory.getAllTenantIds();
    expect(ids).to.deep.equal(["alpha", "beta"]);
  });
});
