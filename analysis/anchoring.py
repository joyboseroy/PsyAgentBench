"""Compute anchoring index per design cell and PRS.

Anchoring index = (mean_high_estimate - mean_low_estimate) /
                  (mean_high_anchor - mean_low_anchor)

Since items have different anchor spans, we normalize per-item first (each
item's (high_est - low_est) / (high_anchor - low_anchor)).

We then take the MEDIAN of per-item indices within a cell, not the mean --
matching Jacowitz & Kahneman's own convention. This matters in practice: a
small number of items produce catastrophic outlier estimates (e.g. a model
given an implausibly small low-anchor for an invented quantity sometimes
answers with something like 9e15 instead of anchoring near it), and a plain
mean lets a single such row swing the whole cell's index by many orders of
magnitude. The median is robust to this; the outlier rate itself is reported
separately as a diagnostic, since it's a real and possibly interesting model
behavior in its own right, not just noise to discard silently.
"""

import argparse
import json
import re
import statistics
from collections import defaultdict

OUTLIER_THRESHOLD = 5.0  # |per-item index| beyond this is treated as a wild
                        # non-anchored response, reported separately


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def item_key_from_trial_id(trial_id: str) -> str:
    # anchor_{domain}_{label}_{persona}_{seed}_item{i}_{cond}
    # item key = everything up to and including itemN (drop the low/high suffix)
    parts = trial_id.split("_")
    return "_".join(parts[:-1])  # drop only the final low/high token


def extract_anchor_value(row) -> float | None:
    # anchor value isn't stored as its own column; recover it from the
    # stimulus text ("more or less than {anchor}?")
    m = re.search(r"more or less than ([\-\d\.]+)\?", row["stimulus"])
    return float(m.group(1)) if m else None


def anchoring_stats(rows):
    cells = defaultdict(lambda: defaultdict(dict))  # cell -> item_key -> {"low":est,"high":est,"low_anchor":x,"high_anchor":x}
    for r in rows:
        if r["final_decision"] == "PARSE_FAIL":
            continue
        cell = (r["domain"], r["condition_label"], r.get("personality", "none"))
        item_key = item_key_from_trial_id(r["trial_id"])
        cond = "high" if r["condition"] == "high_anchor" else "low"
        anchor_val = extract_anchor_value(r)
        try:
            est = float(r["final_decision"])
        except (TypeError, ValueError):
            continue
        cells[cell][item_key][cond] = est
        cells[cell][item_key][f"{cond}_anchor"] = anchor_val

    out = {}
    for cell, items in cells.items():
        indices = []
        for item_key, vals in items.items():
            if not all(k in vals for k in ("low", "high", "low_anchor", "high_anchor")):
                continue
            span = vals["high_anchor"] - vals["low_anchor"]
            if span == 0:
                continue
            idx = (vals["high"] - vals["low"]) / span
            indices.append(idx)
        if indices:
            n_outliers = sum(1 for i in indices if abs(i) > OUTLIER_THRESHOLD)
            out[cell] = {
                "anchoring_index_median": round(statistics.median(indices), 4),
                "n_items": len(indices),
                "n_outliers": n_outliers,
                "outlier_rate": round(n_outliers / len(indices), 3),
            }
    return out


def prs_components(index: float, human_index: float = 0.49):
    direction = 1 if (index > 0) == (human_index > 0) and index != 0 else 0
    if human_index == 0 or index <= 0:
        magnitude = 0
    else:
        ratio = index / human_index
        magnitude = 1 if 0.5 <= ratio <= 2.0 else 0
    return {"direction_match": direction, "magnitude_match": magnitude,
            "prs": 0.5 * direction + 0.5 * magnitude}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    args = ap.parse_args()
    rows = load(args.jsonl)
    stats = anchoring_stats(rows)
    print(f"{'domain':<15}{'label':<8}{'persona':<22}{'index':>8}{'PRS':>6}"
          f"{'outliers':>10}   n_items")
    for key in sorted(stats):
        s = stats[key]
        p = prs_components(s["anchoring_index_median"])
        print(f"{key[0]:<15}{key[1]:<8}{key[2]:<22}"
              f"{s['anchoring_index_median']:>8.3f}{p['prs']:>6.2f}"
              f"{s['n_outliers']:>6}/{s['n_items']:<3}  ({100*s['outlier_rate']:.0f}%)")


if __name__ == "__main__":
    main()
