# PsyAgentBench

**Can societies of LLM agents replicate classic findings in experimental psychology?**

A standardized benchmark comparing effect sizes in LLM-agent populations against
established human psychological baselines, using a Psychological Replication
Score (PRS) and a named/blind x canonical/counterfactual design built to
separate genuine emergent social behavior from training-data recall of the
paradigm itself.

Dataset: [`joyboseroy/PsyAgentBench`](https://huggingface.co/datasets/joyboseroy/PsyAgentBench) (HF, in progress)
Paper: arXiv (in progress)
Write-up: Medium (in progress)

## Headline findings so far (Asch conformity paradigm)

Full methodology and numbers in [RESULTS.md](RESULTS.md). Summary:

1. **Conformity is not a standing disposition -- it's inducible.** Across three
   model families (Llama 3.1 8B, Llama 3.3 70B, gpt-oss-120B), conformity on
   an objectively unambiguous perceptual task is ~0% when the paradigm is
   framed as a routine task ("blind" condition), but rises sharply once the
   prompt identifies it as an Asch conformity replication ("named" condition).
   Raw model reasoning confirms this isn't confusion -- models compute the
   correct answer and explicitly override it: *"I follow the group's
   consensus despite the correct line being 15 units."*

2. **Conformity-inducibility scales with capability, but domain-generalization
   doesn't come for free.** Llama 8B shows almost nothing. Llama 70B shows a
   real effect (46.2%) but only on the literal textbook paradigm -- it
   collapses to near-zero (3.8%) on a structurally identical but surface-novel
   task, consistent with contamination/recall rather than a general
   mechanism. gpt-oss-120B is the only model tested where the effect
   substantially survives the domain shift (83-97% canonical vs 39-86%
   counterfactual), suggestive of something closer to a general induced
   social-conformity mechanism.

3. **A stated "low-agreeableness" persona eliminates conformity completely --
   0.0% in every model, every domain, every framing tested.** The single
   most robust finding in the pilot, precisely because everything else
   varies around it. (Caveat: the persona wording overlaps lexically with
   the outcome -- see RESULTS.md for the planned ablation.)

## Repo layout
EFFECTS.md # Design document: 14 effects, human baselines,
# agent-analogous statistics, counterfactual domains
RESULTS.md # Findings, tables, caveats (Asch paradigm so far)
schema.py # HF dataset row schema (joyboseroy/PsyAgentBench) + validator
llm.py # Backend abstraction: mock / openai-compatible / groq / anthropic
paradigms/asch.py # Asch conformity, fully implemented (2x2 x solo x persona)
run_asch.py # Grid runner -> JSONL (concurrent, resumable)
analysis/prs.py # Conformity stats, Wilson CIs, PRS components
data/ # Generated JSONL (not tracked in git -- see .gitignore)

## Quick start

```bash
# offline smoke test (mock backend, no API keys)
python run_asch.py --backend mock --seeds 20 --out data/asch_mock.jsonl
python analysis/prs.py data/asch_mock.jsonl

# real runs on Groq
export GROQ_API_KEY=gsk_...
python run_asch.py --backend groq:openai/gpt-oss-120b --seeds 20 --workers 8 \
    --personalities none high-agreeableness low-agreeableness \
    --out data/asch_gptoss120b_full.jsonl
python analysis/prs.py data/asch_gptoss120b_full.jsonl

# resume a run that hit rate limits partway through
python run_asch.py --backend groq:openai/gpt-oss-120b --seeds 20 --workers 8 \
    --personalities none high-agreeableness low-agreeableness \
    --out data/asch_gptoss120b_full.jsonl --resume
```

## Design decisions (full detail in EFFECTS.md)

1. Every paradigm runs 2x2: {named, blind} x {canonical, counterfactual}.
   The named-vs-blind gap and canonical-vs-counterfactual gap are headline
   contamination analyses, not nuisance checks.
2. Confederates are scripted, not model calls (matches Asch 1956, removes
   confederate-behavior variance).
3. PRS = 0.5 x direction_match + 0.5 x magnitude_match, magnitude band
   [0.5x, 2.0x] of the human baseline on the natural scale of each effect.
4. The obedience paradigm (planned) uses a harmless-costly analog -- no harm
   content is ever generated.
5. 14 effects targeted, not 20: Stanford Prison and induced-compliance
   dissonance excluded with reasons documented in EFFECTS.md.
6. Personality manipulation uses Big-Five-style persona prompts; an ablation
   with behaviorally-phrased (non-lexically-overlapping) personas is planned
   to separate trait simulation from simple instruction-following.

## Roadmap

- [x] Effect -> metric mapping table (EFFECTS.md)
- [x] Schema, validator, multi-backend runner (mock/OpenAI-compatible/Groq/Anthropic)
- [x] Asch paradigm: full 2x2xpersona grid, 3 model families, results in RESULTS.md
- [ ] Persona-wording ablation (behavioral phrasing, no lexical overlap with outcome)
- [ ] Paradigm 2: anchoring (single-agent, cheapest; validates non-group path)
- [ ] Paradigm 3: bystander effect (first true multi-agent shared-channel
      paradigm; shared-transcript harness reused for polarization/groupthink)
- [ ] Persistent-memory harness (needed for pluralistic ignorance, groupthink)
- [ ] Remaining paradigms per EFFECTS.md
- [ ] Aggregate PRS across effects x models; cross-model comparison figures
- [ ] HF dataset card + upload script for joyboseroy/PsyAgentBench
- [ ] arXiv paper
- [ ] Medium write-up

## Citation

If you use this benchmark or dataset, please cite:

```bibtex
@misc{psyagentbench2026,
  author = {Bose, Joy},
  title = {PsyAgentBench: Can Societies of Large Language Model Agents
           Replicate Classic Findings in Experimental Psychology?},
  year = {2026},
  howpublished = {\url{https://github.com/joyboseroy/psyagentbench}}
}
```

See [CITATION.cff](CITATION.cff) for machine-readable citation metadata.

## License

MIT -- see [LICENSE](LICENSE).
