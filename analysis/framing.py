"""Compute the framing effect (P(sure|gain) - P(sure|loss)) per cell and PRS.

Wilson CIs are computed on each frame's sure-rate proportion for reference,
though the headline statistic is the difference between them, matching the
comparison test specified in EFFECTS.md (difference in proportions vs the
~50 percentage-point human gap).
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


def framing_stats(rows):
    cells = defaultdict(lambda: {"gain_n": 0, "gain_sure": 0,
                                 "loss_n": 0, "loss_sure": 0,
                                 "parse_fail": 0})
    for r in rows:
        cell = (r["domain"], r["condition_label"], r.get("personality", "none"))
        c = cells[cell]
        if r["final_decision"] == "PARSE_FAIL":
            c["parse_fail"] += 1
            continue
        is_sure = r["final_decision"] == "A"
        if r["condition"] == "gain_frame":
            c["gain_n"] += 1
            if is_sure:
                c["gain_sure"] += 1
        elif r["condition"] == "loss_frame":
            c["loss_n"] += 1
            if is_sure:
                c["loss_sure"] += 1
    out = {}
    for cell, c in cells.items():
        if c["gain_n"] == 0 or c["loss_n"] == 0:
            continue
        gain_rate = c["gain_sure"] / c["gain_n"]
        loss_rate = c["loss_sure"] / c["loss_n"]
        gain_lo, gain_hi = wilson(gain_rate, c["gain_n"])
        loss_lo, loss_hi = wilson(loss_rate, c["loss_n"])
        out[cell] = {
            "gain_sure_rate": round(gain_rate, 4),
            "loss_sure_rate": round(loss_rate, 4),
            "gain_ci95": (round(gain_lo, 4), round(gain_hi, 4)),
            "loss_ci95": (round(loss_lo, 4), round(loss_hi, 4)),
            "framing_effect": round(gain_rate - loss_rate, 4),
            "n_gain": c["gain_n"],
            "n_loss": c["loss_n"],
            "parse_fail": c["parse_fail"],
        }
    return out


def prs_components(effect: float, human_effect: float = 0.50):
    direction = 1 if (effect > 0) == (human_effect > 0) and effect != 0 else 0
    if human_effect == 0 or effect <= 0:
        magnitude = 0
    else:
        ratio = effect / human_effect
        magnitude = 1 if 0.5 <= ratio <= 2.0 else 0
    return {"direction_match": direction, "magnitude_match": magnitude,
            "prs": 0.5 * direction + 0.5 * magnitude}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    args = ap.parse_args()
    rows = load(args.jsonl)
    stats = framing_stats(rows)
    print(f"{'domain':<15}{'label':<8}{'persona':<22}{'gain%':>7}{'loss%':>7}"
          f"{'effect':>8}{'PRS':>6}   n (fails)")
    for key in sorted(stats):
        s = stats[key]
        p = prs_components(s["framing_effect"])
        print(f"{key[0]:<15}{key[1]:<8}{key[2]:<22}"
              f"{100*s['gain_sure_rate']:>6.1f}{100*s['loss_sure_rate']:>7.1f}"
              f"{s['framing_effect']:>8.3f}{p['prs']:>6.2f}   "
              f"n_gain={s['n_gain']}, n_loss={s['n_loss']}, fails={s['parse_fail']}")


if __name__ == "__main__":
    main()
