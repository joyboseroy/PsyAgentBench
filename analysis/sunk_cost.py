"""Compute the sunk cost effect (P(continue|sunk) - P(continue|nosunk)) and PRS."""

import argparse
import json
import math
from collections import defaultdict


def wilson(p, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def stats(rows):
    cells = defaultdict(lambda: {"sunk_n": 0, "sunk_cont": 0,
                                 "nosunk_n": 0, "nosunk_cont": 0, "fails": 0})
    for r in rows:
        c = cells[(r["domain"], r["condition_label"], r.get("personality", "none"))]
        if r["final_decision"] == "PARSE_FAIL":
            c["fails"] += 1
            continue
        continues = r["final_decision"] == "A"
        if r["condition"] == "sunk":
            c["sunk_n"] += 1
            c["sunk_cont"] += int(continues)
        elif r["condition"] == "nosunk":
            c["nosunk_n"] += 1
            c["nosunk_cont"] += int(continues)
    out = {}
    for cell, c in cells.items():
        if c["sunk_n"] == 0 or c["nosunk_n"] == 0:
            continue
        sunk_rate = c["sunk_cont"] / c["sunk_n"]
        nosunk_rate = c["nosunk_cont"] / c["nosunk_n"]
        out[cell] = {
            "sunk_rate": round(sunk_rate, 4),
            "nosunk_rate": round(nosunk_rate, 4),
            "effect": round(sunk_rate - nosunk_rate, 4),
            "n_sunk": c["sunk_n"], "n_nosunk": c["nosunk_n"], "fails": c["fails"],
        }
    return out


def prs(effect, human=0.35):
    direction = 1 if (effect > 0) == (human > 0) and effect != 0 else 0
    magnitude = 0
    if effect > 0 and human != 0:
        ratio = effect / human
        magnitude = 1 if 0.5 <= ratio <= 2.0 else 0
    return 0.5 * direction + 0.5 * magnitude


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    args = ap.parse_args()
    s = stats(load(args.jsonl))
    print(f"{'domain':<15}{'label':<8}{'persona':<22}{'sunk%':>7}{'nosunk%':>9}"
          f"{'effect':>8}{'PRS':>6}   n (fails)")
    for key in sorted(s):
        v = s[key]
        print(f"{key[0]:<15}{key[1]:<8}{key[2]:<22}"
              f"{100*v['sunk_rate']:>6.1f}{100*v['nosunk_rate']:>9.1f}"
              f"{v['effect']:>8.3f}{prs(v['effect']):>6.2f}   "
              f"n_sunk={v['n_sunk']}, n_nosunk={v['n_nosunk']}, fails={v['fails']}")


if __name__ == "__main__":
    main()
