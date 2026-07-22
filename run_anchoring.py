"""Run the anchoring paradigm across the design grid and write JSONL rows.

Usage:
  python run_anchoring.py --backend mock --seeds 20 --out data/anchor_mock.jsonl
  python run_anchoring.py --backend groq:openai/gpt-oss-120b --seeds 20 \
      --workers 8 --personalities none high-agreeableness low-agreeableness \
      --out data/anchor_gptoss120b_full.jsonl
"""

import argparse
import itertools
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from llm import get_backend
from schema import validate
from paradigms.anchoring import run_block, ITEMS_PER_BLOCK

ROWS_PER_CELL = ITEMS_PER_BLOCK * 2  # each item run at both low and high anchor


def cell_key(domain, label, persona, seed):
    return f"anchor_{domain}_{label}_{persona}_{seed}"


def completed_cells(path):
    """Return (set of fully-complete cell keys, lines belonging only to those
    complete cells). Rows from any partially-written cell are dropped so the
    cell can be re-run cleanly without producing duplicate trial_ids."""
    if not os.path.exists(path):
        return set(), []
    rows_by_key = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            # trial_id format: anchor_{domain}_{label}_{persona}_{seed}_item{i}_{cond}
            key = "_".join(row["trial_id"].split("_")[:-2])
            rows_by_key.setdefault(key, []).append(line)
    complete = {k for k, lines in rows_by_key.items()
               if len(lines) >= ROWS_PER_CELL}
    kept_lines = [ln for k in complete for ln in rows_by_key[k]]
    dropped = sum(len(v) for k, v in rows_by_key.items() if k not in complete)
    if dropped:
        print(f"--resume: dropping {dropped} rows from incomplete cells "
              f"(will be regenerated)", file=sys.stderr)
    return complete, kept_lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="mock")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default="data/anchor_out.jsonl")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--personalities", nargs="*", default=["none"])
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    backend = get_backend(args.backend)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    grid = list(itertools.product(
        ["canonical", "counterfactual"],
        ["named", "blind"],
        args.personalities,
        range(args.seeds),
    ))

    existing_lines = []
    if args.resume:
        done_keys, existing_lines = completed_cells(args.out)
        before = len(grid)
        grid = [c for c in grid
                if cell_key(c[0], c[1], c[2], c[3]) not in done_keys]
        print(f"--resume: {before - len(grid)} cells already complete, "
              f"{len(grid)} remaining")

    total = len(grid)
    n_rows = 0
    write_lock = threading.Lock()
    progress_lock = threading.Lock()
    done = 0

    def work(cell):
        domain, label, persona, seed = cell
        return run_block(backend, seed=seed, domain=domain,
                         condition_label=label, personality=persona,
                         temperature=args.temperature)

    with open(args.out, "w", encoding="utf-8") as f:
        for line in existing_lines:
            f.write(line if line.endswith("\n") else line + "\n")
            n_rows += 1
        if args.workers <= 1:
            for i, cell in enumerate(grid, 1):
                rows = work(cell)
                with write_lock:
                    for r in rows:
                        problems = validate(r)
                        if problems:
                            print(f"  WARN {r.trial_id}: {problems}", file=sys.stderr)
                        f.write(r.to_json() + "\n")
                        n_rows += 1
                if i % 10 == 0 or i == total:
                    print(f"[{i}/{total}] cells done, {n_rows} rows")
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futures = {ex.submit(work, cell): cell for cell in grid}
                for fut in as_completed(futures):
                    cell = futures[fut]
                    try:
                        rows = fut.result()
                    except Exception as e:
                        print(f"  FAILED cell {cell}: {e}", file=sys.stderr)
                        continue
                    with write_lock:
                        for r in rows:
                            problems = validate(r)
                            if problems:
                                print(f"  WARN {r.trial_id}: {problems}", file=sys.stderr)
                            f.write(r.to_json() + "\n")
                            n_rows += 1
                    with progress_lock:
                        done += 1
                        if done % 10 == 0 or done == total:
                            print(f"[{done}/{total}] cells done, {n_rows} rows")
    print(f"Wrote {n_rows} rows total -> {args.out}")


if __name__ == "__main__":
    main()
