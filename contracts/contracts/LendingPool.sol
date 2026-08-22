// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * Lending pool: deposit collateral, borrow against it.
 * Credit score (set by oracle/backend) controls min score and collateral ratio.
 * - Score 70+: collateral ratio 50% (borrow up to 2x collateral)
 * - Score 40-69: collateral ratio 80% (borrow up to 1.25x collateral)
 * - Score < 40 or fraud: no borrow
 */
interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract LendingPool {
    IERC20 public token;

    address public poolOwner;
    address public creditOracle;  // only this address can set credit score and fraud flag

    uint256 public constant MIN_SCORE_TO_BORROW = 40;
    uint256 public constant SCORE_HIGH = 70;   // >= 70: 50% ratio
    uint256 public constant RATIO_LOW = 50;     // 50% = borrow up to 2x collateral
    uint256 public constant RATIO_MID = 80;     // 80% = borrow up to 1.25x collateral
    uint256 public constant RATIO_DENOM = 100;

    uint256 public interestRatePerSecond = 0;   // simple: 0 for demo; or e.g. 1e9 = 0.000000001 per second

    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debt;
    mapping(address => uint256) public creditScore;   // 0-100 set by oracle
    mapping(address => bool) public isFraud;

    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);
    event Borrow(address indexed user, uint256 amount);
    event Repay(address indexed user, uint256 amount);
    event CreditUpdated(address indexed user, uint256 score, bool fraud);

    error InsufficientCollateral();
    error ScoreTooLow();
    error FraudFlagged();
    error HasDebt();
    error TransferFailed();
    error InsufficientLiquidity();

    constructor(address _token) {
        token = IERC20(_token);
        poolOwner = msg.sender;
        creditOracle = msg.sender;
    }

    function setCreditOracle(address _oracle) external {
        require(msg.sender == poolOwner, "not owner");
        creditOracle = _oracle;
    }

    /// @notice Backend/oracle calls this after computing score and fraud from the API
    function setCreditData(address user, uint256 score, bool fraud) external {
        require(msg.sender == creditOracle, "not oracle");
        creditScore[user] = score;
        isFraud[user] = fraud;
        emit CreditUpdated(user, score, fraud);
    }

    /// @notice Collateral ratio in percent (e.g. 50 = must have 2x collateral for borrow)
    function collateralRatioForScore(uint256 score) public pure returns (uint256) {
        if (score >= SCORE_HIGH) return RATIO_LOW;   // 50%
        if (score >= MIN_SCORE_TO_BORROW) return RATIO_MID; // 80%
        return 100; // no borrow
    }

    function deposit(uint256 amount) external {
        if (amount == 0) return;
        if (!token.transferFrom(msg.sender, address(this), amount)) revert TransferFailed();
        collateral[msg.sender] += amount;
        emit Deposit(msg.sender, amount);
    }

    function withdraw(uint256 amount) external {
        if (amount == 0) return;
        uint256 d = debt[msg.sender];
        if (d > 0) {
            uint256 required = (d * 100) / collateralRatioForScore(creditScore[msg.sender]);
            if (collateral[msg.sender] - amount < required) revert HasDebt();
        }
        collateral[msg.sender] -= amount;
        if (!token.transfer(msg.sender, amount)) revert TransferFailed();
        emit Withdraw(msg.sender, amount);
    }

    function borrow(uint256 amount) external {
        if (amount == 0) return;
        if (isFraud[msg.sender]) revert FraudFlagged();
        uint256 score = creditScore[msg.sender];
        if (score < MIN_SCORE_TO_BORROW) revert ScoreTooLow();
        uint256 ratio = collateralRatioForScore(score);
        uint256 requiredCollateral = (amount * ratio) / RATIO_DENOM;
        if (collateral[msg.sender] < requiredCollateral) revert InsufficientCollateral();
        if (token.balanceOf(address(this)) < amount) revert InsufficientLiquidity();

        debt[msg.sender] += amount;
        if (!token.transfer(msg.sender, amount)) revert TransferFailed();
        emit Borrow(msg.sender, amount);
    }

    function repay(uint256 amount) external {
        if (amount == 0) return;
        uint256 d = debt[msg.sender];
        if (amount > d) amount = d;
        debt[msg.sender] -= amount;
        if (!token.transferFrom(msg.sender, address(this), amount)) revert TransferFailed();
        emit Repay(msg.sender, amount);
    }

    function getBorrowLimit(address user) external view returns (uint256) {
        if (isFraud[user] || creditScore[user] < MIN_SCORE_TO_BORROW) return 0;
        uint256 ratio = collateralRatioForScore(creditScore[user]);
        return (collateral[user] * RATIO_DENOM) / ratio;
    }
}
