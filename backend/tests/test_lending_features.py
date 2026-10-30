import unittest

from app.services.lending_features import compute_lending_features


class LendingFeatureTests(unittest.TestCase):
    def test_repaid_borrow_history(self):
        history = {
            "counts": {"deposit": 1, "withdraw": 0, "borrow": 1, "repay": 1},
            "totals": {"deposited": 2.0, "withdrawn": 0.0, "borrowed": 0.1, "repaid": 0.1},
            "current_state": {"collateral": 2.0, "debt": 0.0},
        }
        result = compute_lending_features(history)
        self.assertEqual(result["lending_event_count"], 3)
        self.assertEqual(result["net_deposited"], 2.0)
        self.assertEqual(result["repayment_coverage_ratio"], 1.0)
        self.assertEqual(result["remaining_debt_ratio"], 0.0)
        self.assertEqual(result["has_borrow_history"], 1)
        self.assertEqual(result["has_repayment_history"], 1)
        self.assertEqual(result["has_open_debt"], 0)

    def test_no_lending_history(self):
        result = compute_lending_features({
            "counts": {"deposit": 0, "withdraw": 0, "borrow": 0, "repay": 0},
            "totals": {"deposited": 0, "withdrawn": 0, "borrowed": 0, "repaid": 0},
            "current_state": {"collateral": 0, "debt": 0},
        })
        self.assertEqual(result["lending_event_count"], 0)
        self.assertEqual(result["repayment_coverage_ratio"], 0.0)
        self.assertEqual(result["has_borrow_history"], 0)
        self.assertEqual(result["has_open_debt"], 0)

    def test_invalid_negative_amount_rejected(self):
        with self.assertRaises(ValueError):
            compute_lending_features({
                "counts": {},
                "totals": {"deposited": -1},
                "current_state": {},
            })


if __name__ == "__main__":
    unittest.main()
