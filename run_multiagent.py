"""Generic grid runner for multi-agent, multi-round deliberation paradigms
(group polarization, risky shift, groupthink), sharing the same domain x
condition_label x personality x seed design as run_paradigm.py, but where
each cell is a TRIAL involving N agents across a pre-discussion baseline
round and one or more discussion rounds, rather than a handful of
independent single-agent items.

Each supported paradigm module must expose:
  - run_trial(backend, *, seed, domain, condition_label, personality,
              temperature, n_agents, n_rounds) -> list[ObservationRow]
    Returns ALL rows for one trial: n_agents * (n_rounds + 1) rows total
    (the +1 is the round-0 baseline before any discussion).
  - ROWS_PER_CELL(n_agents, n_rounds) -> int -- callable, since row count
    depends on the CLI-supplied --n-agents/--n-rounds, unlike single-agent
    paradigms where it's fixed.
  - STRIP_TOKENS (int) -- trailing underscore-tokens in trial_id to strip
    to get the cell-grouping key used for --resume. Multi-agent trial_ids
    end in _agent{i}_round{r}, so STRIP_TOKENS=2, matching the single-agent
    convention.
  - PARADIGM_PREFIX (str) -- literal prefix used in trial_id.

Cost warning: API calls per cell = n_agents * (n_rounds + 1), and this is
multiplied across the full domain x label x persona x seed grid, so this
scales much faster than the single-agent runner. Start with a small pilot
(--seeds 3, default --n-agents 4 --n-rounds 1) before committing to a full
20-seed grid.

Usage:
  python run_multiagent.py --paradigm risky_shift --backend mock --seeds 3 \
      --out data/risky_shift_mock.jsonl
  python run_multiagent.py --paradigm risky_shift \
      --backend groq:openai/gpt-oss-120b --seeds 10 --workers 4 \
      --personalities none high-agreeableness low-agreeableness \
      --n-agents 4 --n-rounds 1 \
      --out data/risky_shift_gptoss120b_pilot.jsonl
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

PARADIGMS = ("risky_shift", "polarization", "groupthink")


def load_paradigm(name):
    if name not in PARADIGMS:
        raise ValueError(f"unknown paradigm '{name}', choose from {PARADIGMS}")
    return importlib.import_module(f"paradigms_multiagent.{name}")


def cell_key(trial_id: str, strip_tokens: int) -> str:
    return "_".join(trial_id.split("_")[:-strip_tokens]) if strip_tokens else trial_id


def completed_cells(path, rows_per_cell, strip_tokens):
    """Same drop-incomplete-cell logic as run_paradigm.py: any cell that
    doesn't have exactly rows_per_cell rows on disk is dropped and will be
    regenerated cleanly, so a crashed run never leaves duplicate or partial
    trial_ids behind."""
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
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--out", default=None)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--personalities", nargs="*", default=["none"])
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--n-agents", type=int, default=4,
                     help="number of agents deliberating together per trial")
    ap.add_argument("--n-rounds", type=int, default=1,
                     help="number of discussion rounds after the round-0 "
                          "pre-discussion baseline")
    args = ap.parse_args()

    module = load_paradigm(args.paradigm)
    out_path = args.out or f"data/{args.paradigm}_out.jsonl"
    backend = get_backend(args.backend)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    rows_per_cell = module.ROWS_PER_CELL(args.n_agents, args.n_rounds)
    calls_per_cell = rows_per_cell  # one model call per row in this design

    def make_cell_key(domain, label, persona, seed):
        return f"{module.PARADIGM_PREFIX}_{domain}_{label}_{persona}_{seed}"

    grid = list(itertools.product(
        ["canonical", "counterfactual"],
        ["named", "blind"],
        args.personalities,
        range(args.seeds),
    ))

    print(f"Grid: {len(grid)} cells x {rows_per_cell} calls/cell = "
          f"{len(grid) * calls_per_cell} total model calls "
          f"({args.n_agents} agents x {args.n_rounds + 1} rounds)")

    existing_lines = []
    if args.resume:
        done_keys, existing_lines = completed_cells(
            out_path, rows_per_cell, module.STRIP_TOKENS)
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
        return module.run_trial(backend, seed=seed, domain=domain,
                                 condition_label=label, personality=persona,
                                 temperature=args.temperature,
                                 n_agents=args.n_agents, n_rounds=args.n_rounds)

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
                if i % 5 == 0 or i == total:
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
                        if done % 5 == 0 or done == total:
                            print(f"[{done}/{total}] cells done, {n_rows} rows")
    print(f"Wrote {n_rows} rows total -> {out_path}")


if __name__ == "__main__":
    main()
