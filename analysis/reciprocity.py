"""Compute the reciprocity effect: compliance-rate ratio
(P(comply|favor) / P(comply|nofavor)), matching EFFECTS.md's specified
comparison test, plus the raw proportion difference for reference."""

import argparse
import json
from collections import defaultdict


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def stats(rows):
    cells = defaultdict(lambda: {"favor_n": 0, "favor_comply": 0,
                                 "nofavor_n": 0, "nofavor_comply": 0, "fails": 0})
    for r in rows:
        c = cells[(r["domain"], r["condition_label"], r.get("personality", "none"))]
        if r["final_decision"] == "PARSE_FAIL":
            c["fails"] += 1
            continue
        comply = r["final_decision"] == "A"
        if r["condition"] == "favor":
            c["favor_n"] += 1
            c["favor_comply"] += int(comply)
        elif r["condition"] == "nofavor":
            c["nofavor_n"] += 1
            c["nofavor_comply"] += int(comply)
    out = {}
    for cell, c in cells.items():
        if c["favor_n"] == 0 or c["nofavor_n"] == 0:
            continue
        favor_rate = c["favor_comply"] / c["favor_n"]
        nofavor_rate = c["nofavor_comply"] / c["nofavor_n"]
        ratio = (favor_rate / nofavor_rate) if nofavor_rate > 0 else float("inf")
        out[cell] = {
            "favor_rate": round(favor_rate, 4),
            "nofavor_rate": round(nofavor_rate, 4),
            "diff": round(favor_rate - nofavor_rate, 4),
            "ratio": ratio,
            "n_favor": c["favor_n"], "n_nofavor": c["nofavor_n"], "fails": c["fails"],
        }
    return out


def prs(ratio, human=2.0):
    if ratio == float("inf"):
        return 0.5  # direction clearly matches, magnitude undefined (div by 0)
    direction = 1 if ratio > 1 else 0
    magnitude = 0
    if ratio > 1:
        rel = ratio / human
        magnitude = 1 if 0.5 <= rel <= 2.0 else 0
    return 0.5 * direction + 0.5 * magnitude


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    args = ap.parse_args()
    s = stats(load(args.jsonl))
    print(f"{'domain':<15}{'label':<8}{'persona':<22}{'favor%':>7}{'nofavor%':>9}"
          f"{'ratio':>7}{'PRS':>6}   n (fails)")
    for key in sorted(s):
        v = s[key]
        ratio_str = "inf" if v["ratio"] == float("inf") else f"{v['ratio']:.2f}"
        print(f"{key[0]:<15}{key[1]:<8}{key[2]:<22}"
              f"{100*v['favor_rate']:>6.1f}{100*v['nofavor_rate']:>9.1f}"
              f"{ratio_str:>7}{prs(v['ratio']):>6.2f}   "
              f"n_favor={v['n_favor']}, n_nofavor={v['n_nofavor']}, fails={v['fails']}")


if __name__ == "__main__":
    main()

