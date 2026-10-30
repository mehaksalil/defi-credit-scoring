const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("LendingPool", function () {
  let token, pool;
  let owner, oracle, alice, bob, other;

  const parse = (n) => ethers.parseEther(n.toString());

  beforeEach(async function () {
    [owner, oracle, alice, bob, other] = await ethers.getSigners();

    const MockERC20 = await ethers.getContractFactory("MockERC20");
    token = await MockERC20.deploy();
    await token.waitForDeployment();

    const LendingPool = await ethers.getContractFactory("LendingPool");
    pool = await LendingPool.deploy(await token.getAddress());
    await pool.waitForDeployment();

    // Give the pool liquidity to lend out
    await (await token.mint(await pool.getAddress(), parse(100000))).wait();

    // Give Alice and Bob some tokens to use as collateral
    await (await token.mint(alice.address, parse(10000))).wait();
    await (await token.mint(bob.address, parse(10000))).wait();
  });

  describe("Oracle access control", function () {
    it("only the credit oracle can call setCreditData", async function () {
      await expect(
        pool.connect(alice).setCreditData(alice.address, 80, false)
      ).to.be.revertedWith("not oracle");
    });

    it("the owner can repoint the oracle to a new address", async function () {
      await (await pool.connect(owner).setCreditOracle(oracle.address)).wait();
      await expect(pool.connect(oracle).setCreditData(alice.address, 80, false))
        .to.emit(pool, "CreditUpdated")
        .withArgs(alice.address, 80, false);
    });

    it("a non-owner cannot repoint the oracle", async function () {
      await expect(
        pool.connect(alice).setCreditOracle(alice.address)
      ).to.be.revertedWith("not owner");
    });

    it("rejects a score above 100", async function () {
      // owner is the default oracle at deploy time
      await expect(
        pool.connect(owner).setCreditData(alice.address, 101, false)
      ).to.be.revertedWith("score out of range");
    });

    it("accepts a score of exactly 100", async function () {
      await expect(pool.connect(owner).setCreditData(alice.address, 100, false))
        .to.emit(pool, "CreditUpdated")
        .withArgs(alice.address, 100, false);
    });
  });

  describe("Borrowing rules (score / fraud gating)", function () {
    it("blocks borrowing when score is below the minimum", async function () {
      await (await pool.connect(owner).setCreditData(alice.address, 39, false)).wait();
      await (await token.connect(alice).approve(await pool.getAddress(), parse(100))).wait();
      await (await pool.connect(alice).deposit(parse(100))).wait();

      await expect(pool.connect(alice).borrow(parse(1))).to.be.revertedWithCustomError(
        pool,
        "ScoreTooLow"
      );
    });

    it("blocks borrowing when flagged as fraud, regardless of score", async function () {
      await (await pool.connect(owner).setCreditData(alice.address, 90, true)).wait();
      await (await token.connect(alice).approve(await pool.getAddress(), parse(100))).wait();
      await (await pool.connect(alice).deposit(parse(100))).wait();

      await expect(pool.connect(alice).borrow(parse(1))).to.be.revertedWithCustomError(
        pool,
        "FraudFlagged"
      );
    });

    it("allows a single borrow within the limit for a high score (ratio 50%)", async function () {
      await (await pool.connect(owner).setCreditData(alice.address, 90, false)).wait();
      await (await token.connect(alice).approve(await pool.getAddress(), parse(100))).wait();
      await (await pool.connect(alice).deposit(parse(100))).wait();

      // score >= 70 -> ratio 50% -> can borrow up to 2x collateral = 200
      await expect(pool.connect(alice).borrow(parse(200))).to.not.be.reverted;
      expect(await pool.debt(alice.address)).to.equal(parse(200));
    });

    it("rejects a single borrow that exceeds the limit", async function () {
      await (await pool.connect(owner).setCreditData(alice.address, 90, false)).wait();
      await (await token.connect(alice).approve(await pool.getAddress(), parse(100))).wait();
      await (await pool.connect(alice).deposit(parse(100))).wait();

      await expect(
        pool.connect(alice).borrow(parse(200.0001))
      ).to.be.revertedWithCustomError(pool, "InsufficientCollateral");
    });

    it("rejects REPEATED borrows whose cumulative total exceeds the limit (regression test)", async function () {
      // This is the bug that was fixed: borrow() used to validate only the new
      // amount against collateral, not existing debt + new amount, so a user
      // could split one big over-limit borrow into many small ones that each
      // looked fine in isolation.
      await (await pool.connect(owner).setCreditData(alice.address, 90, false)).wait();
      await (await token.connect(alice).approve(await pool.getAddress(), parse(100))).wait();
      await (await pool.connect(alice).deposit(parse(100))).wait();

      // Limit is 200 total (score 90 -> ratio 50% -> 2x collateral of 100).
      await (await pool.connect(alice).borrow(parse(150))).wait();
      expect(await pool.debt(alice.address)).to.equal(parse(150));

      // A further 50 would bring total debt to exactly 200 - should succeed.
      await expect(pool.connect(alice).borrow(parse(50))).to.not.be.reverted;
      expect(await pool.debt(alice.address)).to.equal(parse(200));

      // Any further borrow at all must now fail, since debt is already at the limit.
      await expect(
        pool.connect(alice).borrow(parse(1))
      ).to.be.revertedWithCustomError(pool, "InsufficientCollateral");
    });

    it("reverts when the pool itself lacks liquidity even though the user is under their own collateral limit", async function () {
      // The pool starts with 100,000 MOCK (see top-level beforeEach). Give alice a very
      // large deposit so her personal borrow limit (2x collateral at score 90, ratio 50%)
      // comfortably exceeds the pool's total token balance. This isolates the
      // InsufficientLiquidity check from the InsufficientCollateral check.
      await (await pool.connect(owner).setCreditData(alice.address, 90, false)).wait();

      const bigDeposit = parse(1000000); // 1,000,000 MOCK
      await (await token.mint(alice.address, bigDeposit)).wait();
      await (await token.connect(alice).approve(await pool.getAddress(), bigDeposit)).wait();
      await (await pool.connect(alice).deposit(bigDeposit)).wait();

      // Pool balance is now 100,000 (initial) + 1,000,000 (alice's own deposit) = 1,100,000.
      // Alice's personal limit is 2 * 1,000,000 = 2,000,000, which is well above that.
      const poolBalance = await token.balanceOf(await pool.getAddress());
      expect(poolBalance).to.equal(parse(1100000));
      expect(await pool.getBorrowLimit(alice.address)).to.equal(parse(2000000));

      // Borrowing exactly what the pool holds should succeed (collateral allows far more).
      await expect(pool.connect(alice).borrow(poolBalance)).to.not.be.reverted;

      // But borrowing even 1 wei more must fail with InsufficientLiquidity, since the
      // pool itself is now empty even though alice's collateral would allow much more.
      await expect(pool.connect(alice).borrow(1)).to.be.revertedWithCustomError(
        pool,
        "InsufficientLiquidity"
      );
    });
  });

  describe("Deposit / repay / collateral-safe withdrawal", function () {
    beforeEach(async function () {
      await (await pool.connect(owner).setCreditData(alice.address, 90, false)).wait();
      await (await token.connect(alice).approve(await pool.getAddress(), parse(1000))).wait();
    });

    it("deposit increases collateral and pulls tokens from the user", async function () {
      await (await pool.connect(alice).deposit(parse(100))).wait();
      expect(await pool.collateral(alice.address)).to.equal(parse(100));
      expect(await token.balanceOf(alice.address)).to.equal(parse(9900));
    });

    it("repay reduces debt and pulls tokens back from the user", async function () {
      await (await pool.connect(alice).deposit(parse(100))).wait();
      await (await pool.connect(alice).borrow(parse(100))).wait();

      await (await token.connect(alice).approve(await pool.getAddress(), parse(50))).wait();
      await (await pool.connect(alice).repay(parse(50))).wait();

      expect(await pool.debt(alice.address)).to.equal(parse(50));
    });

    it("withdraw allows removing collateral down to (but not below) what current debt requires", async function () {
      await (await pool.connect(alice).deposit(parse(100))).wait();
      await (await pool.connect(alice).borrow(parse(100))).wait();
      // score 90 -> ratio 50% -> required collateral for 100 debt = 100 * 50 / 100 = 50
      // So alice should be able to withdraw down to 50 collateral remaining (i.e. withdraw 50),
      // but not withdraw 51.

      await expect(pool.connect(alice).withdraw(parse(51))).to.be.revertedWithCustomError(
        pool,
        "HasDebt"
      );

      await expect(pool.connect(alice).withdraw(parse(50))).to.not.be.reverted;
      expect(await pool.collateral(alice.address)).to.equal(parse(50));
    });

    it("withdraw with no debt allows removing all collateral", async function () {
      await (await pool.connect(alice).deposit(parse(100))).wait();
      await expect(pool.connect(alice).withdraw(parse(100))).to.not.be.reverted;
      expect(await pool.collateral(alice.address)).to.equal(0);
    });
  });

  describe("getBorrowLimit view", function () {
    it("returns 0 for fraud-flagged or below-minimum-score users", async function () {
      await (await pool.connect(owner).setCreditData(alice.address, 90, true)).wait();
      await (await token.connect(alice).approve(await pool.getAddress(), parse(100))).wait();
      await (await pool.connect(alice).deposit(parse(100))).wait();
      expect(await pool.getBorrowLimit(alice.address)).to.equal(0);
    });

    it("returns collateral * 2 for a score >= 70 (50% ratio)", async function () {
      await (await pool.connect(owner).setCreditData(bob.address, 70, false)).wait();
      await (await token.connect(bob).approve(await pool.getAddress(), parse(100))).wait();
      await (await pool.connect(bob).deposit(parse(100))).wait();
      expect(await pool.getBorrowLimit(bob.address)).to.equal(parse(200));
    });
  });
});
