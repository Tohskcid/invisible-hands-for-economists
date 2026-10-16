#!/usr/bin/env python3
"""Compare computed estimates to withheld published targets without mixing samples."""

import hashlib
import json
from pathlib import Path


def main():
    base = Path(__file__).resolve().parents[1]
    result_file = base / "attempt/research/results.json"
    holdout_file = base / "holdout/aer-card-krueger-1994.json"
    result = json.loads(result_file.read_text())["results"]
    original = json.loads(holdout_file.read_text())["published_targets"]
    comparisons = []

    def compare(label, computed, published, note):
        error = abs(computed - published)
        comparisons.append({
            "target": label,
            "computed": computed,
            "published": published,
            "absolute_error": error,
            "tolerance": 0.05,
            "matches_protocol_tolerance": error <= 0.05,
            "matches_displayed_two_decimals": f"{computed:.2f}" == f"{published:.2f}",
            "note": note,
        })

    compare("Table 3 balanced employment contrast", result["primary"]["estimate"],
            original["table3"]["change_balanced"]["value"][2], "Same balanced-panel estimand.")
    compare("Table 3 balanced independent-group standard error",
            result["primary"]["se_separate_groups"],
            original["table3"]["change_balanced"]["se"][2],
            "Restaurant sampling uncertainty conditional on the two observed state paths.")
    for state, column in (("pa", 0), ("nj", 1)):
        compare(f"Table 3 balanced {state} mean change", result[state]["change"],
                original["table3"]["change_balanced"]["value"][column], "Same balanced panel.")
    compare("Table 3 all-available contrast", result["crosssection"]["estimate"],
            original["table3"]["change_all_available"]["value"][2],
            "Different from the balanced estimand; a displayed-rounding discrepancy is retained.")

    report = {
        "results_sha256": hashlib.sha256(result_file.read_bytes()).hexdigest(),
        "holdout_sha256": hashlib.sha256(holdout_file.read_bytes()).hexdigest(),
        "comparisons": comparisons,
        "matches": sum(item["matches_protocol_tolerance"] for item in comparisons),
        "published_regressions": {
            "published_table4_n": original["table4"]["N"],
            "worker_controlled_n": result["controlled"]["n"],
            "worker_gap_n": result["gap"]["n"],
            "verdict": "not exact reconstruction: different samples/specifications",
            "reason": "These valid alternative estimates cannot be treated as the original Table 4 estimates.",
        },
        "full_article_verdict": "partial reconstruction",
        "unrecovered_blocks": [
            "Exact Table 4 and Table 5 original sample/specification set",
            "Exact ZIP-based geographic robustness",
            "Original state entry analysis and separate CPS evidence",
        ],
        "independent_verification": "research/reviews/empirical-execution.json",
        "interpretation": "Matching these core quantities does not establish causal identification or complete original-paper recovery.",
    }
    destination = base / "research/empirical-comparison.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"compared": len(comparisons), "matched": report["matches"],
                      "full_article_verdict": report["full_article_verdict"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
