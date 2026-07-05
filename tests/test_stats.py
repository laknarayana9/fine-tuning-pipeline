from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finqa_ft.stats import (  # noqa: E402
    bootstrap_ci,
    cohen_kappa,
    mean,
    mcnemar_exact_pvalue,
    paired_delta,
)


class StatsTest(unittest.TestCase):
    def test_bootstrap_ci_is_bounded(self) -> None:
        lower, upper = bootstrap_ci([0.0, 1.0, 1.0, 1.0], statistic=mean, seed=1)
        self.assertGreaterEqual(lower, 0.0)
        self.assertLessEqual(upper, 1.0)
        self.assertLessEqual(lower, upper)

    def test_paired_delta(self) -> None:
        self.assertAlmostEqual(
            paired_delta([True, True, False, False], [True, False, True, True]),
            0.25,
        )

    def test_mcnemar_exact(self) -> None:
        pvalue = mcnemar_exact_pvalue(
            [True, True, True, True],
            [False, False, False, False],
        )
        self.assertAlmostEqual(pvalue, 0.125)

    def test_cohen_kappa(self) -> None:
        kappa = cohen_kappa(["win", "lose", "win", "tie"], ["win", "lose", "tie", "tie"])
        self.assertGreater(kappa, 0.0)
        self.assertLessEqual(kappa, 1.0)


if __name__ == "__main__":
    unittest.main()
