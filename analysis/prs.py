"""Compute per-paradigm effect statistics and Psychological Replication Score.

PRS components (per effect, per design cell):
- direction_match: 1 if sign(agent effect) == sign(human effect)
- magnitude_match: 1 if agent effect size within [0.5x, 2.0x] of human baseline
Headline PRS = mean over effects of 0.5*direction + 0.5*magnitude.

For Asch: effect = conformity rate on critical group trials minus solo error rate
on the same stimuli class. Human baseline 0.37 (proportion).
Wilson intervals reported for proportions.
"""

import argparse
import json
import math
from collections import defaultdict


def wilson(p: float, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def asch_stats(rows):
    """Return dict keyed by (domain, condition_label, personality)."""
    cells = defaultdict(lambda: {"crit_n": 0, "crit_conf": 0,
                                 "solo_n": 0, "solo_err": 0,
                                 "parse_fail": 0})
    for r in rows:
        key = (r["domain"], r["condition_label"], r.get("personality", "none"))
        c = cells[key]
        if r["final_decision"] == "PARSE_FAIL":
            c["parse_fail"] += 1
            continue
        if r["condition"] == "critical":
            c["crit_n"] += 1
            if r.get("conformed"):
                c["crit_conf"] += 1
        elif r["condition"] == "solo":
            c["solo_n"] += 1
            if r["final_decision"] != r["correct_answer"]:
                c["solo_err"] += 1
    out = {}
    for key, c in cells.items():
        conf_rate = c["crit_conf"] / c["crit_n"] if c["crit_n"] else 0.0
        solo_err = c["solo_err"] / c["solo_n"] if c["solo_n"] else 0.0
        effect = conf_rate - solo_err
        lo, hi = wilson(conf_rate, c["crit_n"])
        out[key] = {
            "conformity_rate": round(conf_rate, 4),
            "conformity_ci95": (round(lo, 4), round(hi, 4)),
            "solo_error_rate": round(solo_err, 4),
            "net_effect": round(effect, 4),
            "n_critical": c["crit_n"],
            "n_solo": c["solo_n"],
            "parse_fail": c["parse_fail"],
        }
    return out


def prs_components(net_effect: float, human_effect: float = 0.37):
    direction = 1 if (net_effect > 0) == (human_effect > 0) and net_effect != 0 else 0
    if human_effect == 0 or net_effect <= 0:
        magnitude = 0
    else:
        ratio = net_effect / human_effect
        magnitude = 1 if 0.5 <= ratio <= 2.0 else 0
    return {"direction_match": direction, "magnitude_match": magnitude,
            "prs": 0.5 * direction + 0.5 * magnitude}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    args = ap.parse_args()
    rows = load(args.jsonl)
    stats = asch_stats(rows)
    print(f"{'domain':<15}{'label':<8}{'persona':<22}{'conf%':>7}{'solo_err%':>10}"
          f"{'net':>7}{'PRS':>6}   CI95")
    for key in sorted(stats):
        s = stats[key]
        p = prs_components(s["net_effect"])
        print(f"{key[0]:<15}{key[1]:<8}{key[2]:<22}"
              f"{100*s['conformity_rate']:>6.1f}{100*s['solo_error_rate']:>10.1f}"
              f"{s['net_effect']:>7.3f}{p['prs']:>6.2f}   {s['conformity_ci95']}"
              f"  (n_crit={s['n_critical']}, n_solo={s['n_solo']},"
              f" fails={s['parse_fail']})")


if __name__ == "__main__":
    main()
