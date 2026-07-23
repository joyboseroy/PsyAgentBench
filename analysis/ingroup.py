"""Compute the in-group favoritism index: mean (points_ingroup - points_outgroup)
/ total_pool, per cell. Ranges -1 (all to out-group) to +1 (all to in-group)."""

import argparse
import json
from collections import defaultdict

TOTAL_POOL = 20

_REFUSAL_MARKERS = ("i'm sorry", "i cannot", "i can't", "i can not",
                    "i won't", "i will not", "unable to comply",
                    "cannot comply", "can't comply", "cannot help",
                    "can't help")


def is_refusal(raw: str) -> bool:
    low = raw.lower().replace("\u2019", "'").replace("\u2018", "'")
    return any(marker in low for marker in _REFUSAL_MARKERS)


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def stats(rows):
    cells = defaultdict(list)
    fails = defaultdict(int)
    refused = defaultdict(int)
    for r in rows:
        cell = (r["domain"], r["condition_label"], r.get("personality", "none"))
        # Re-check agent_response directly rather than trusting final_decision
        # alone -- rows generated before the quote-normalization fix may
        # still say PARSE_FAIL for what was actually a refusal.
        if r["final_decision"] == "REFUSED" or is_refusal(r.get("agent_response", "")):
            refused[cell] += 1
            continue
        if r["final_decision"] == "PARSE_FAIL":
            fails[cell] += 1
            continue
        pts_in = float(r["final_decision"])
        index = (pts_in - (TOTAL_POOL - pts_in)) / TOTAL_POOL
        cells[cell].append(index)
    out = {}
    all_cells = set(cells) | set(fails) | set(refused)
    for cell in all_cells:
        indices = cells.get(cell, [])
        out[cell] = {
            "favoritism_index": round(sum(indices) / len(indices), 4) if indices else None,
            "n": len(indices),
            "fails": fails.get(cell, 0),
            "refused": refused.get(cell, 0),
        }
    return out


def prs(index, human=0.35):
    direction = 1 if (index > 0) == (human > 0) and index != 0 else 0
    magnitude = 0
    if index > 0:
        ratio = index / human
        magnitude = 1 if 0.5 <= ratio <= 2.0 else 0
    return 0.5 * direction + 0.5 * magnitude


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    args = ap.parse_args()
    s = stats(load(args.jsonl))
    print(f"{'domain':<15}{'label':<8}{'persona':<22}{'index':>8}{'PRS':>6}   "
          f"n (fails, refused)")
    for key in sorted(s):
        v = s[key]
        idx_str = f"{v['favoritism_index']:>8.3f}" if v['favoritism_index'] is not None else f"{'--':>8}"
        prs_val = prs(v['favoritism_index']) if v['favoritism_index'] is not None else 0.0
        print(f"{key[0]:<15}{key[1]:<8}{key[2]:<22}"
              f"{idx_str}{prs_val:>6.2f}   "
              f"n={v['n']}, fails={v['fails']}, refused={v['refused']}")


if __name__ == "__main__":
    main()
