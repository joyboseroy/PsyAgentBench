"""Generic grid runner for single-agent (or single-scripted-peer) paradigms
that share the same domain x condition_label x personality x seed design.

Each supported paradigm module must expose:
  - run_block(backend, *, seed, domain, condition_label, personality, temperature)
  - ROWS_PER_CELL (int)
  - STRIP_TOKENS (int) -- trailing underscore-tokens in trial_id to strip to
    get the cell-grouping key used for --resume.
  - PARADIGM_PREFIX (str) -- the literal prefix used in trial_id, which may
    differ from --paradigm (e.g. sunk_cost's prefix is "sunkcost").

Usage:
  python run_paradigm.py --paradigm sunk_cost --backend mock --seeds 20 \
      --out data/sunkcost_mock.jsonl
  python run_paradigm.py --paradigm reciprocity \
      --backend groq:openai/gpt-oss-120b --seeds 20 --workers 8 \
      --personalities none high-agreeableness low-agreeableness \
      --out data/reciprocity_gptoss120b_full.jsonl
"""

import argparse
import importlib
import itertools
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from llm import get_backend
from schema import validate

PARADIGMS = ("sunk_cost", "reciprocity", "false_consensus", "ingroup")


def load_paradigm(name):
    if name not in PARADIGMS:
        raise ValueError(f"unknown paradigm '{name}', choose from {PARADIGMS}")
    return importlib.import_module(f"paradigms.{name}")


def cell_key(trial_id: str, strip_tokens: int) -> str:
    return "_".join(trial_id.split("_")[:-strip_tokens]) if strip_tokens else trial_id


def completed_cells(path, rows_per_cell, strip_tokens):
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
            key = cell_key(row["trial_id"], strip_tokens)
            rows_by_key.setdefault(key, []).append(line)
    complete = {k for k, lines in rows_by_key.items() if len(lines) >= rows_per_cell}
    kept_lines = [ln for k in complete for ln in rows_by_key[k]]
    dropped = sum(len(v) for k, v in rows_by_key.items() if k not in complete)
    if dropped:
        print(f"--resume: dropping {dropped} rows from incomplete cells "
              f"(will be regenerated)", file=sys.stderr)
    return complete, kept_lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paradigm", required=True, choices=PARADIGMS)
    ap.add_argument("--backend", default="mock")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default=None)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--personalities", nargs="*", default=["none"])
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    module = load_paradigm(args.paradigm)
    out_path = args.out or f"data/{args.paradigm}_out.jsonl"
    backend = get_backend(args.backend)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    def make_cell_key(domain, label, persona, seed):
        return f"{module.PARADIGM_PREFIX}_{domain}_{label}_{persona}_{seed}"

    grid = list(itertools.product(
        ["canonical", "counterfactual"],
        ["named", "blind"],
        args.personalities,
        range(args.seeds),
    ))

    existing_lines = []
    if args.resume:
        done_keys, existing_lines = completed_cells(
            out_path, module.ROWS_PER_CELL, module.STRIP_TOKENS)
        before = len(grid)
        grid = [c for c in grid
                if make_cell_key(c[0], c[1], c[2], c[3]) not in done_keys]
        print(f"--resume: {before - len(grid)} cells already complete, "
              f"{len(grid)} remaining")

    total = len(grid)
    n_rows = 0
    write_lock = threading.Lock()
    progress_lock = threading.Lock()
    done = 0

    def work(cell):
        domain, label, persona, seed = cell
        return module.run_block(backend, seed=seed, domain=domain,
                                condition_label=label, personality=persona,
                                temperature=args.temperature)

    with open(out_path, "w", encoding="utf-8") as f:
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
    print(f"Wrote {n_rows} rows total -> {out_path}")


if __name__ == "__main__":
    main()
