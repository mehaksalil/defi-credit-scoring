const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const MockERC20 = await hre.ethers.getContractFactory("MockERC20");
  const token = await MockERC20.deploy();
  await token.deployed();
  const tokenAddr = token.address;
  console.log("MockERC20 deployed to:", tokenAddr);

  const LendingPool = await hre.ethers.getContractFactory("LendingPool");
  const pool = await LendingPool.deploy(tokenAddr);
  await pool.deployed();
  const poolAddr = pool.address;
  console.log("LendingPool deployed to:", poolAddr);

  // Mint tokens to deployer and to pool so there is liquidity
  const mintAmount = hre.ethers.utils.parseEther("1000000");
  await token.mint(deployer.address, mintAmount);
  await token.mint(poolAddr, hre.ethers.utils.parseEther("100000"));
  console.log("Minted 1M to deployer, 100k to pool");

  console.log("\nDone. Use these in the frontend:");
  console.log("TOKEN_ADDRESS=" + tokenAddr);
  console.log("LENDING_POOL_ADDRESS=" + poolAddr);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
