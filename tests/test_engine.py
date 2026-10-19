from copy import deepcopy
import json
import math
from pathlib import Path
import unittest

from fab_discovery.engine import OUTCOMES, analyze, benchmark, entropy, likelihood, observe, posterior, simulated_outcome

ROOT = Path(__file__).resolve().parent.parent


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((ROOT / "fab_discovery/examples/process-window.json").read_text())

    def test_predictive_probabilities_are_distributions(self):
        for h in self.case["hypotheses"]:
            for d in self.case["designs"]:
                p = likelihood(h, d)
                self.assertAlmostEqual(sum(p.values()), 1)
                self.assertTrue(all(0 < x < 1 for x in p.values()))

    def test_information_gain_matches_expected_kl_oracle(self):
        result = analyze(self.case)
        weights = posterior(self.case)
        for row in result["candidates"]:
            design = next(d for d in self.case["designs"] if d["id"] == row["id"])
            value = 0
            for h, w in zip(self.case["hypotheses"], weights):
                p = likelihood(h, design)
                value += sum(w * p[o] * math.log2(p[o] / row["prediction"][o]) for o in OUTCOMES)
            self.assertAlmostEqual(value, row["information_bits"], places=10)

    def test_observation_updates_hypotheses_and_accounts_budget(self):
        state = observe(self.case, "p1-d5", "underfused", "measurement-1")
        self.assertAlmostEqual(state["remaining_budget"], 21)
        p = analyze(state)["posterior"]
        self.assertGreater(next(x["probability"] for x in p if x["id"] == "high-fusion-threshold"), 1/3)
        self.assertEqual(self.case["observations"], [])

    def test_retried_measurement_is_not_double_counted(self):
        state = observe(self.case, "p1-d5", "underfused", "measurement-1")
        self.assertEqual(observe(state, "p1-d5", "underfused", "measurement-1"), state)
        with self.assertRaisesRegex(ValueError, "invalid_evidence_conflict"):
            observe(state, "p1-d5", "good", "measurement-1")

    def test_unknown_capability_is_excluded(self):
        row = next(x for x in analyze(self.case)["candidates"] if x["id"] == "metrology-unavailable")
        self.assertFalse(row["eligible"])
        self.assertIn("capability_missing", row["exclusions"])

    def test_pending_is_excluded_and_completed_observation_clears_it(self):
        self.case["pending"] = ["p1-d5"]
        row = next(x for x in analyze(self.case)["candidates"] if x["id"] == "p1-d5")
        self.assertIn("already_pending", row["exclusions"])
        self.assertEqual(observe(self.case, "p1-d5", "good")["pending"], [])

    def test_no_budget_produces_no_experiment(self):
        self.case["remaining_budget"] = 0
        result = analyze(self.case)
        self.assertIsNone(result["recommendation"])
        self.assertFalse(result["hardware_executed"])

    def test_zero_risk_has_no_false_safe_choice(self):
        self.case["max_damage_probability"] = 0
        self.assertIsNone(analyze(self.case)["recommendation"])

    def test_machine_limit_is_not_overruled_by_information_gain(self):
        self.case["machine"]["max_power"] = 1
        result = analyze(self.case)
        eligible = [r["id"] for r in result["candidates"] if r["eligible"]]
        self.assertTrue(set(eligible) <= {"p1-d2", "p1-d5"})

    def test_fingerprint_includes_measurements(self):
        other = observe(self.case, "p1-d5", "good")
        self.assertNotEqual(analyze(self.case)["input_sha256"], analyze(other)["input_sha256"])

    def test_many_observations_stay_numerically_stable(self):
        self.case["observations"] = [{"design": "p1-d5", "outcome": "underfused"}] * 1000
        p = posterior(self.case)
        self.assertAlmostEqual(sum(p), 1)
        self.assertTrue(math.isfinite(entropy(p)))

    def test_benchmark_reproducibility_and_all_strategies_disclosed(self):
        first = benchmark(self.case, seeds=range(2), max_steps=3)
        self.assertEqual(first, benchmark(self.case, seeds=range(2), max_steps=3))
        self.assertEqual(set(first["summary"]), {"information", "yield", "cheapest"})
        self.assertEqual(len(first["runs"]), 18)
        self.assertTrue(first["synthetic"])
        for run in first["runs"]:
            self.assertLessEqual(run["cost"], self.case["remaining_budget"])

    def test_simulation_draw_is_shared_by_strategy(self):
        a = simulated_outcome(self.case, "p1-d5", "fragile-material", 7, 0)
        self.assertEqual(a, simulated_outcome(self.case, "p1-d5", "fragile-material", 7, 0))

    def test_malformed_and_nonfinite_values_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze([])
        for value in (float("nan"), -1, 0, True):
            case = deepcopy(self.case)
            case["hypotheses"][0]["prior"] = value
            with self.assertRaises(ValueError):
                analyze(case)


if __name__ == "__main__":
    unittest.main()
