const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

// How many of Hardhat's default 20 local accounts get MOCK tokens minted to them
// directly, so you don't have to manually mint before testing in MetaMask.
// Account #0 is the deployer/oracle and already gets tokens minted below.
const NUM_TEST_ACCOUNTS_TO_FUND = 5;
const TEST_ACCOUNT_MINT_AMOUNT = "10000"; // MOCK tokens per test account

async function main() {
  const signers = await hre.ethers.getSigners();
  const deployer = signers[0];
  console.log("Deploying with account:", deployer.address);

  const MockERC20 = await hre.ethers.getContractFactory("MockERC20");
  const token = await MockERC20.deploy();
  await token.waitForDeployment();
  const tokenAddr = await token.getAddress();
  console.log("MockERC20 deployed to:", tokenAddr);

  const LendingPool = await hre.ethers.getContractFactory("LendingPool");
  const pool = await LendingPool.deploy(tokenAddr);
  await pool.waitForDeployment();
  const poolAddr = await pool.getAddress();
  console.log("LendingPool deployed to:", poolAddr);

  // Mint tokens to deployer and to pool so there is liquidity
  const mintAmount = hre.ethers.parseEther("1000000");
  await (await token.mint(deployer.address, mintAmount)).wait();
  await (await token.mint(poolAddr, hre.ethers.parseEther("100000"))).wait();
  console.log("Minted 1,000,000 MOCK to deployer, 100,000 MOCK to pool");

  // Fund a handful of the other local Hardhat accounts too, so whichever
  // private key you import into MetaMask already has test tokens to deposit.
  const fundedAccounts = [];
  const perAccountMint = hre.ethers.parseEther(TEST_ACCOUNT_MINT_AMOUNT);
  for (let i = 1; i < Math.min(NUM_TEST_ACCOUNTS_TO_FUND + 1, signers.length); i++) {
    const acct = signers[i];
    await (await token.mint(acct.address, perAccountMint)).wait();
    fundedAccounts.push(acct.address);
  }
  console.log(
    `Minted ${TEST_ACCOUNT_MINT_AMOUNT} MOCK each to ${fundedAccounts.length} local test accounts:`
  );
  fundedAccounts.forEach((a, i) => console.log(`  Account #${i + 1}: ${a}`));

  // The deployer is the initial creditOracle (set in the LendingPool constructor).
  // The backend oracle bridge signs transactions with ORACLE_PRIVATE_KEY, which for
  // local development should be Hardhat account #0's private key (the deployer),
  // OR you can repoint the oracle role with pool.setCreditOracle(newAddress) and use
  // that account's key in the backend .env instead. Never use a mainnet key here.
  console.log("\ncreditOracle is currently set to the deployer:", deployer.address);

  const network = await hre.ethers.provider.getNetwork();

  const deployedInfo = {
    network: network.name,
    chainId: Number(network.chainId),
    tokenAddress: tokenAddr,
    lendingPoolAddress: poolAddr,
    creditOracle: deployer.address,
    fundedTestAccounts: fundedAccounts,
    deployedAt: new Date().toISOString(),
  };
  const outFile = path.join(__dirname, "..", "deployed-addresses.json");
  fs.writeFileSync(outFile, JSON.stringify(deployedInfo, null, 2));
  console.log(`\nWrote deployment info to ${outFile}`);

  console.log("\nDone. Copy these into frontend/.env:");
  console.log(`VITE_TOKEN_ADDRESS=${tokenAddr}`);
  console.log(`VITE_LENDING_POOL_ADDRESS=${poolAddr}`);
  console.log(`VITE_CHAIN_ID=${Number(network.chainId)}`);
  console.log("\nAnd copy these into backend/.env:");
  console.log(`TOKEN_ADDRESS=${tokenAddr}`);
  console.log(`LENDING_POOL_ADDRESS=${poolAddr}`);
  console.log(`CHAIN_ID=${Number(network.chainId)}`);
  console.log("ETH_RPC_URL=http://127.0.0.1:8545");
  console.log(
    "ORACLE_PRIVATE_KEY=<private key of the creditOracle address printed above>"
  );
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
