import unittest

from app.services.lending_scoring import compute_lending_behavior_score


class LendingBehaviorScoringTests(unittest.TestCase):
    def test_no_borrow_history_returns_no_score(self):
        result = compute_lending_behavior_score({
            "borrow_event_count": 0,
            "total_borrowed": 0,
            "total_repaid": 0,
            "current_collateral": 2,
            "current_debt": 0,
        })
        self.assertIsNone(result["lending_behavior_score"])
        self.assertEqual(result["status"], "insufficient_history")

    def test_one_fully_repaid_small_borrow_is_shrunk_toward_neutral(self):
        result = compute_lending_behavior_score({
            "borrow_event_count": 1,
            "total_borrowed": 0.1,
            "total_repaid": 0.1,
            "current_collateral": 2,
            "current_debt": 0,
        })
        self.assertEqual(result["raw_component_score"], 100.0)
        self.assertEqual(result["evidence_factor"], 0.2)
        self.assertEqual(result["lending_behavior_score"], 60.0)
        self.assertEqual(result["evidence_level"], "low")

    def test_unrepaid_debt_reduces_components(self):
        result = compute_lending_behavior_score({
            "borrow_event_count": 1,
            "total_borrowed": 0.1,
            "total_repaid": 0,
            "current_collateral": 2,
            "current_debt": 0.1,
        })
        self.assertEqual(result["components"]["repayment_coverage_ratio"], 0.0)
        self.assertEqual(result["components"]["debt_to_collateral_ratio"], 0.05)
        self.assertLess(result["raw_component_score"], 50.0)

    def test_repayment_coverage_is_capped_at_one(self):
        result = compute_lending_behavior_score({
            "borrow_event_count": 5,
            "total_borrowed": 1,
            "total_repaid": 1.5,
            "current_collateral": 2,
            "current_debt": 0,
        })
        self.assertEqual(result["components"]["repayment_coverage_ratio"], 1.0)
        self.assertEqual(result["lending_behavior_score"], 100.0)

    def test_negative_features_rejected(self):
        with self.assertRaises(ValueError):
            compute_lending_behavior_score({
                "borrow_event_count": 1,
                "total_borrowed": -1,
                "total_repaid": 0,
                "current_collateral": 1,
                "current_debt": 0,
            })


if __name__ == "__main__":
    unittest.main()
