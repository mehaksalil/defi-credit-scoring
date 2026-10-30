import unittest
from app.services.combined_scoring import combine_credit_scores


class CombinedScoringTests(unittest.TestCase):
    def test_current_30_70_blend(self):
        result = combine_credit_scores(1.53, 60.0)
        self.assertEqual(result["combined_credit_score"], 42.46)
        self.assertEqual(result["combined_risk_level"], "Medium")
        self.assertEqual(result["weights"], {"behavioral": 0.30, "lending": 0.70})
        self.assertEqual(result["formula"], "combined=0.30*behavioral_score+0.70*lending_behavior_score")

    def test_no_lending_history_falls_back_to_behavioral_score(self):
        result = combine_credit_scores(51.25, None)
        self.assertEqual(result["combined_credit_score"], 51.25)
        self.assertEqual(result["combined_risk_level"], "Medium")
        self.assertEqual(result["weights"], {"behavioral": 1.0, "lending": 0.0})

    def test_rejects_score_above_range(self):
        with self.assertRaises(ValueError):
            combine_credit_scores(110, 60)

    def test_rejects_negative_score(self):
        with self.assertRaises(ValueError):
            combine_credit_scores(50, -1)

    def test_rejects_non_finite_score(self):
        with self.assertRaises(ValueError):
            combine_credit_scores(float("nan"), 60)


if __name__ == "__main__":
    unittest.main()
