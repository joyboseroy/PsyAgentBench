"""Run the Asch paradigm across the design grid and write JSONL rows.

Usage:
  python run_asch.py --backend mock --seeds 20 --out data/asch_mock.jsonl
  python run_asch.py --backend groq:llama-3.1-8b-instant --seeds 20 \
      --workers 16 --out data/asch_llama8b.jsonl
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
from paradigms.asch import run_block, TRIALS_PER_BLOCK


def cell_key(domain, label, solo, persona, seed):
    return f"asch_{domain}_{label}_{'solo' if solo else 'group'}_{persona}_{seed}"


def completed_cells(path):
    """Return (set of fully-complete cell keys, lines belonging only to those
    complete cells). Rows from any partially-written cell (e.g. truncated
    mid-block by a 429 failure) are dropped so the cell can be re-run cleanly
    without producing duplicate trial_ids."""
    if not os.path.exists(path):
        return set(), []
    rows_by_key = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            key = row["trial_id"].rsplit("_t", 1)[0]
            rows_by_key.setdefault(key, []).append(line)
    complete = {k for k, lines in rows_by_key.items()
               if len(lines) >= TRIALS_PER_BLOCK}
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
    ap.add_argument("--out", default="data/asch_out.jsonl")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--personalities", nargs="*", default=["none"])
    ap.add_argument("--workers", type=int, default=1,
                    help=("Concurrent grid cells in flight. Each cell makes "
                          "12 sequential API calls (one 12-trial block), so "
                          "workers=N gives you ~N calls in flight at once. "
                          "Paid Groq tiers can typically handle 10-20+; keep "
                          "at 1 for the mock backend (no benefit) and start "
                          "low (4-8) on a new key/tier to see how the rate "
                          "limit behaves before pushing higher."))
    ap.add_argument("--resume", action="store_true",
                    help=("If --out already has a partial run (e.g. some "
                          "cells failed with 429), skip cells that already "
                          "have a full 12-row block and only run the gaps. "
                          "Rewrites --out with existing rows preserved plus "
                          "the newly-filled cells."))
    args = ap.parse_args()

    backend = get_backend(args.backend)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    grid = list(itertools.product(
        ["canonical", "counterfactual"],       # domain
        ["named", "blind"],                    # condition_label
        [False, True],                         # solo control
        args.personalities,
        range(args.seeds),
    ))

    existing_lines = []
    if args.resume:
        done_keys, existing_lines = completed_cells(args.out)
        before = len(grid)
        grid = [c for c in grid
                if cell_key(c[0], c[1], c[2], c[3], c[4]) not in done_keys]
        print(f"--resume: {before - len(grid)} cells already complete, "
              f"{len(grid)} remaining")

    total = len(grid)
    n_rows = 0
    write_lock = threading.Lock()
    progress_lock = threading.Lock()
    done = 0

    def work(cell):
        domain, label, solo, persona, seed = cell
        return run_block(backend, seed=seed, domain=domain,
                         condition_label=label, solo=solo,
                         personality=persona, temperature=args.temperature)

    mode = "w"
    with open(args.out, mode, encoding="utf-8") as f:
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
