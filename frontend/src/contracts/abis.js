// MockERC20 ABI (minimal interface)
export const MOCK_ERC20_ABI = [
  "function balanceOf(address owner) view returns (uint256)",
  "function transfer(address to, uint256 amount) returns (bool)",
  "function approve(address spender, uint256 amount) returns (bool)",
  "function allowance(address owner, address spender) view returns (uint256)",
  "function decimals() view returns (uint8)",
  "function symbol() view returns (string)",
  "event Transfer(address indexed from, address indexed to, uint256 value)",
];

// LendingPool ABI
export const LENDING_POOL_ABI = [
  "function deposit(uint256 amount) external",
  "function withdraw(uint256 amount) external",
  "function borrow(uint256 amount) external",
  "function repay(uint256 amount) external",
  "function setCreditData(address user, uint256 score, bool fraud) external",
  "function collateral(address) view returns (uint256)",
  "function debt(address) view returns (uint256)",
  "function creditScore(address) view returns (uint256)",
  "function isFraud(address) view returns (bool)",
  "function getBorrowLimit(address user) external view returns (uint256)",
  "function collateralRatioForScore(uint256 score) public pure returns (uint256)",
  "function token() view returns (address)",
  "event Deposit(address indexed user, uint256 amount)",
  "event Withdraw(address indexed user, uint256 amount)",
  "event Borrow(address indexed user, uint256 amount)",
  "event Repay(address indexed user, uint256 amount)",
  "event CreditUpdated(address indexed user, uint256 score, bool fraud)",
];
