"""Compute the false consensus bias: mean(estimated agreement %) - actual
population agreement % for the option each agent chose.

The "actual" population share is computed by aggregating every row's choice
for a given item, across ALL seeds and personas within the same
(domain, condition_label) -- this is why false_consensus.py uses fixed item
lists rather than per-seed regeneration. Reported per (domain, label,
persona) cell, but the population baseline itself pools across personas
(representing "the general population of participants," not a
trait-filtered subgroup).
"""

import argparse
import json
from collections import defaultdict


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def item_key(trial_id: str) -> str:
    # falsecons_{domain}_{label}_{persona}_{seed}_item{i}
    # population key groups by (domain, label, item) -- drop persona+seed.
    parts = trial_id.split("_")
    domain, label = parts[1], parts[2]
    item = parts[-1]  # itemN
    return f"{domain}_{label}_{item}"


def parse_row(r):
    if r["final_decision"] == "PARSE_FAIL" or "|" not in r["final_decision"]:
        return None
    choice, pct = r["final_decision"].split("|")
    return choice, float(pct)


def stats(rows):
    # Pass 1: population share of each choice, per (domain, label, item).
    pop_counts = defaultdict(lambda: {"A": 0, "B": 0})
    parsed = []
    for r in rows:
        p = parse_row(r)
        if p is None:
            continue
        choice, pct = p
        key = item_key(r["trial_id"])
        pop_counts[key][choice] += 1
        parsed.append((r, key, choice, pct))

    # Pass 2: per-cell bias, using the population share of the option chosen.
    cells = defaultdict(list)
    for r, key, choice, pct in parsed:
        total = pop_counts[key]["A"] + pop_counts[key]["B"]
        actual_pct = 100 * pop_counts[key][choice] / total if total else None
        if actual_pct is None:
            continue
        cell = (r["domain"], r["condition_label"], r.get("personality", "none"))
        cells[cell].append(pct - actual_pct)

    out = {}
    for cell, biases in cells.items():
        out[cell] = {
            "mean_bias_pp": round(sum(biases) / len(biases), 2),
            "n": len(biases),
        }
    return out


def prs(bias_pp, human_pp=17.5):
    effect = bias_pp / 100.0
    human = human_pp / 100.0
    direction = 1 if (effect > 0) == (human > 0) and effect != 0 else 0
    magnitude = 0
    if effect > 0:
        ratio = effect / human
        magnitude = 1 if 0.5 <= ratio <= 2.0 else 0
    return 0.5 * direction + 0.5 * magnitude


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    args = ap.parse_args()
    s = stats(load(args.jsonl))
    print(f"{'domain':<15}{'label':<8}{'persona':<22}{'bias(pp)':>10}{'PRS':>6}   n")
    for key in sorted(s):
        v = s[key]
        print(f"{key[0]:<15}{key[1]:<8}{key[2]:<22}"
              f"{v['mean_bias_pp']:>10.2f}{prs(v['mean_bias_pp']):>6.2f}   {v['n']}")


if __name__ == "__main__":
    main()
