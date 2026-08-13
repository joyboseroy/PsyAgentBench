"""Re-run parse_choice over an existing pilot file's raw agent_response,
without spending any new API calls. Use this after a parse_choice fix
(e.g. the refusal-detection patch) to correct already-collected data.

Usage:
  python3 reclassify.py --paradigm authority_obedience \
      --in data/authority_obedience_gptoss120b_pilot.jsonl \
      --out data/authority_obedience_gptoss120b_pilot_fixed.jsonl
"""
import argparse
import importlib
import json

ap = argparse.ArgumentParser()
ap.add_argument("--paradigm", required=True)
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()

module = importlib.import_module(f"paradigms.{args.paradigm}")
changed = 0
total = 0
with open(args.inp, encoding="utf-8") as fin, open(args.out, "w", encoding="utf-8") as fout:
    for line in fin:
        if not line.strip():
            continue
        row = json.loads(line)
        total += 1
        new_decision = module.parse_choice(row["agent_response"])
        if new_decision != row["final_decision"]:
            changed += 1
            row["final_decision"] = new_decision
        fout.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"{args.paradigm}: {total} rows, {changed} reclassified -> {args.out}")
