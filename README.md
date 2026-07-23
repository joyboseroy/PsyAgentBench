# PsyAgentBench

**Can societies of LLM agents replicate classic findings in experimental psychology?**

A standardized benchmark comparing effect sizes in LLM-agent populations against
established human psychological baselines, using a Psychological Replication
Score (PRS) and a named/blind x canonical/counterfactual design built to
separate genuine emergent social behavior from training-data recall of the
paradigm itself.

Dataset: [`joyboseroy/PsyAgentBench`](https://huggingface.co/datasets/joyboseroy/PsyAgentBench) (HF)
Medium: https://joyboseroy.medium.com/i-told-an-ai-it-was-in-a-conformity-experiment-it-conformed-470b0105fcef

## Headline findings so far (Asch conformity, anchoring, and framing paradigms)

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

4. **Anchoring shows a strikingly different profile from conformity, in the
   same model (gpt-oss-120B).** Anchoring on real-world facts is exactly
   0.000 (zero, not just small) in every persona/framing cell, while
   anchoring on invented quantities with no ground truth is near-total
   (0.90-1.01, essentially just returning the anchor). Unlike Asch,
   personality only mildly dampens this effect rather than eliminating it,
   and naming the paradigm doesn't reduce it at all. Read together with the
   conformity results: conformity in this model looks *recognition-gated*
   (needs the model to identify the paradigm to appear at all), while
   anchoring looks more *mechanical* (fires regardless of whether the model
   is aware it's being tested).

5. **Framing effect adds a third, distinct profile, and personality doesn't
   just gate it -- it can flip its sign.** With no persona, framing is ~0
   when blind and strong when named (0.62 canonical, 0.79 counterfactual --
   the effect is *larger* on invented content than the textbook scenario,
   arguing against simple statistic-recall). A stated low-agreeableness
   persona doesn't dampen this effect the way it did anchoring -- it
   reverses it entirely (-0.32 canonical, -0.46 counterfactual), the only
   condition in the whole dataset where the model prefers the risky option
   under gain framing. Across all three paradigms, personality's
   relationship to induced bias turns out to be three different things:
   elimination (conformity), mild dampening (anchoring), and reversal
   (framing) -- not one dial with varying strength.

6. **Sunk cost is a clean, fully robust null** -- 0.000 across every
   persona, domain, and framing (n=160/cell). The stimulus states plainly
   that continuing has poor prospects; the model weighs that consistently
   regardless of whether prior investment is mentioned, in clear contrast
   to the human ~35pp effect. Not induced, not domain-dependent, not
   persona-gated -- just absent.

7. **In-group favoritism's real story is refusal, not the favoritism
   index.** The model explicitly declines the allocation task ("I'm sorry,
   but I can't comply with that") 5-12x more often with no stated
   personality than with either an agreeable or disagreeable persona
   (e.g. 23.8% vs 2.5%/1.9% refusal, canonical-named). Any stated
   personality, regardless of direction, makes the model far more willing
   to engage with the task at all. The favoritism index itself (computed
   only on non-refusing responses) shows low-agreeableness dampening but
   not eliminating favoritism -- but should be read cautiously given the
   refusal-driven selection effect on the sample.

## Repo layout

```
EFFECTS.md             # Design document: 14 effects, human baselines,
                       # agent-analogous statistics, counterfactual domains
RESULTS.md             # Findings, tables, caveats (Asch + anchoring + framing)
schema.py              # HF dataset row schema (joyboseroy/PsyAgentBench) + validator
llm.py                 # Backend abstraction: mock / openai-compatible / groq / anthropic
paradigms/asch.py      # Asch conformity, fully implemented (2x2 x solo x persona)
paradigms/anchoring.py # Anchoring, fully implemented (2x2 x persona, single-agent)
paradigms/framing.py   # Framing effect, fully implemented (2x2 x persona, single-agent)
paradigms/sunk_cost.py     # Sunk cost, single-agent, paired sunk/nosunk condition
paradigms/ingroup.py       # In-group favoritism, single-agent, minimal-group design
run_paradigm.py            # Generic runner for sunk_cost/reciprocity/false_consensus/ingroup
analysis/sunk_cost.py      # Sunk cost effect (proportion difference), PRS
analysis/ingroup.py        # Favoritism index, refusal-rate tracking (distinct from parse fails), PRS
run_asch.py            # Asch grid runner -> JSONL (concurrent, resumable)
run_anchoring.py       # Anchoring grid runner -> JSONL (concurrent, resumable)
run_framing.py         # Framing grid runner -> JSONL (concurrent, resumable)
analysis/prs.py        # Asch conformity stats, Wilson CIs, PRS components
analysis/anchoring.py  # Anchoring index (median-based), outlier rate, PRS
analysis/framing.py    # Framing effect (sure-rate gap), Wilson CIs, PRS
hf/                    # Dataset prep + upload scripts for joyboseroy/PsyAgentBench
data/                  # Generated JSONL (not tracked in git -- see .gitignore)
```

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
- [x] Anchoring paradigm: full 2x2xpersona grid (gpt-oss-120B), results in RESULTS.md
- [x] Framing effect paradigm: full 2x2xpersona grid (gpt-oss-120B), results in RESULTS.md
- [x] Framing effect paradigm: full 2x2xpersona grid (gpt-oss-120B), results in RESULTS.md
- [x] Sunk cost paradigm: full 2x2xpersona grid (gpt-oss-120B), results in RESULTS.md
- [x] In-group favoritism paradigm: full 2x2xpersona grid (gpt-oss-120B), refusal-rate finding, results in RESULTS.md
- [ ] Reciprocity, false consensus: implemented but need design fixes before results are meaningful (see RESULTS.md caveats)
- [ ] Anchoring and framing on Llama 8B/70B (currently gpt-oss-120B only)
- [ ] Persona-wording ablation (behavioral phrasing, no lexical overlap with outcome)
- [ ] Paradigm 4: bystander effect (first true multi-agent shared-channel
      paradigm; shared-transcript harness reused for polarization/groupthink)
- [ ] Persistent-memory harness (needed for pluralistic ignorance, groupthink)
- [ ] Remaining paradigms per EFFECTS.md
- [ ] Aggregate PRS across effects x models; cross-model comparison figures
- [x] HF dataset card + upload for joyboseroy/PsyAgentBench (Asch + anchoring; framing pending)
- [ ] arXiv paper
- [x] Medium write-up

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
