# PsyAgentBench

Can societies of LLM agents replicate classic findings in experimental psychology?
A standardized benchmark comparing effect sizes in LLM-agent populations against
established human baselines, scored with a Psychological Replication Score (PRS).

## Repo layout

```
EFFECTS.md            # THE design document: 14 effects, human baselines,
                      # agent-analogous statistics, counterfactual domains
schema.py             # HF dataset row schema (joyboseroy/PsyAgentBench) + validator
llm.py                # backend abstraction: mock / openai-compatible / anthropic
paradigms/asch.py     # first paradigm, fully implemented (2x2x solo design)
run_asch.py           # grid runner -> JSONL
analysis/prs.py       # conformity stats, Wilson CIs, PRS components
data/                 # generated JSONL (gitignore for real runs)
```

## Quick start

```bash
# offline smoke test (mock backend, no API keys)
python run_asch.py --backend mock --seeds 20 --out data/asch_mock.jsonl
python analysis/prs.py data/asch_mock.jsonl

# real runs on Groq (primary; cheap Llama inference)
export GROQ_API_KEY=gsk_...

# pilot first: 3 seeds, check parse-fail column before scaling
python run_asch.py --backend groq:llama-3.1-8b-instant --seeds 3 \
    --out data/asch_pilot_8b.jsonl
python analysis/prs.py data/asch_pilot_8b.jsonl

# full grid, two model sizes for the cross-model axis
python run_asch.py --backend groq:llama-3.1-8b-instant --seeds 20 \
    --personalities none high-agreeableness low-agreeableness \
    --out data/asch_llama8b.jsonl
python run_asch.py --backend groq:llama-3.3-70b-versatile --seeds 20 \
    --personalities none high-agreeableness low-agreeableness \
    --out data/asch_llama70b.jsonl

# check console.groq.com/docs/models for the current catalog; qwen/llama-4
# variants there give you a third family for the cross-model comparison

# other providers also work
python run_asch.py --backend openai:gpt-4o-mini --seeds 20 --out data/asch_4omini.jsonl
python run_asch.py --backend anthropic:claude-haiku-4-5-20251001 --seeds 20 --out data/asch_haiku.jsonl
```

Cost note: one Asch grid cell = 12 trials = 12 short calls. Default grid
(2 domains x 2 labels x {group, solo} x P personalities x S seeds) x 12 calls.
With 3 personalities and 20 seeds: 5,760 calls per model — cheap on small models.

## Design decisions already locked (see EFFECTS.md for full table)

1. Every paradigm runs 2x2: {named, blind} x {canonical, counterfactual}.
   The named-vs-blind gap and canonical-vs-counterfactual gap are headline
   contamination analyses, not nuisance checks.
2. Confederates are scripted, not model calls (matches Asch, removes variance).
3. PRS = 0.5 * direction_match + 0.5 * magnitude_match, magnitude band
   [0.5x, 2.0x] of human baseline on the natural scale of each effect.
4. Obedience paradigm uses a harmless-costly analog (no harm content generated).
5. 14 effects, not 20: Stanford Prison and induced-compliance dissonance excluded
   with reasons documented.

## Roadmap

- [x] Effect -> metric mapping table (EFFECTS.md)
- [x] Schema + validator
- [x] Backend abstraction with offline mock
- [x] Asch end-to-end (stimuli, prompts, runner, analysis) — smoke-tested
- [ ] Real-model pilot: 2 small models x Asch grid; sanity-check parse rates
- [ ] Paradigm 2: anchoring (single-agent, cheapest; validates the non-group path)
- [ ] Paradigm 3: bystander (first true multi-agent shared-channel paradigm;
      build the shared-transcript harness here, reuse for polarization/groupthink)
- [ ] Persistent-memory harness (needed for pluralistic ignorance, groupthink)
- [ ] Remaining paradigms per EFFECTS.md
- [ ] Aggregate PRS across effects x models; cross-model comparison figures
- [ ] HF dataset card + upload script for joyboseroy/PsyAgentBench
- [ ] Paper draft

## Statistical notes

- Group paradigms need >= 30 groups/cell for stable proportions; report Wilson CIs.
- Preregister the magnitude band and effect definitions (EFFECTS.md serves as the
  preregistration draft; freeze it before real runs and log its git hash into rows).
- Parse failures are reported per cell and must stay < 2%; otherwise fix prompts,
  don't filter silently.
