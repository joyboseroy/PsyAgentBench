# Results: Asch Conformity Paradigm

Status: pilot-scale (n=120 critical trials per cell for gpt-oss-120B and
Llama variants; see EFFECTS.md for the full design). All numbers below are
observed conformity rates on critical trials (agent matches the scripted
incorrect majority), with Wilson 95% CIs from `analysis/prs.py`.

## 1. Named vs blind framing (persona = none)

| Model | Domain | Blind | Named |
|---|---|---|---|
| Llama 3.1 8B | canonical | 0.0% | 0.0% |
| Llama 3.1 8B | counterfactual | 0.9% | 0.8% |
| Llama 3.3 70B | canonical | 0.0% | 0.4% |
| Llama 3.3 70B | counterfactual | 0.0% | 0.0% |
| gpt-oss-120B | canonical | 0.0% | **83.3%** |
| gpt-oss-120B | counterfactual | 0.0% | **39.2%** |

Only gpt-oss-120B shows a real effect of naming the paradigm, and it is
large: conformity goes from indistinguishable-from-zero to 39-83% purely
from telling the model it's participating in an Asch replication. Raw
reasoning traces from the named+canonical+critical+conformed cells show the
model computing the correct answer and explicitly stating it is
overriding it in favor of the majority, e.g.:

> "I follow the group's consensus despite the correct line being 15 units."
> "Following the group's consensus despite the correct line being 15 units"
> "I chose the same as the previous participants"

This rules out simple confusion or task difficulty as the explanation.

## 2. Personality moderation (named framing only)

| Model | Domain | low-agreeableness | none | high-agreeableness |
|---|---|---|---|---|
| Llama 3.1 8B | canonical | 0.0% | 0.0% | 10.0% |
| Llama 3.1 8B | counterfactual | 0.0% | 0.8% | 2.2% |
| Llama 3.3 70B | canonical | 0.0% | 0.4% | **46.2%** |
| Llama 3.3 70B | counterfactual | 0.0% | 0.0% | 3.8% |
| gpt-oss-120B | canonical | **0.0%** | 83.3% | **96.7%** |
| gpt-oss-120B | counterfactual | **0.0%** | 39.2% | **85.8%** |

Two consistent patterns:

- **low-agreeableness eliminates conformity completely** -- 0.0% in every
  cell, every model, every domain tested. This is the single most robust
  finding in the pilot: it replicates across three independent model
  families with no exceptions.
- **high-agreeableness amplifies conformity above the "none" baseline** in
  every model where a baseline effect exists at all (Llama 70B canonical,
  gpt-oss-120B both domains), consistent with the human literature linking
  agreeableness to social conformity.

## 3. Domain-generalization as a contamination probe

The canonical domain (line-length judgment) is the literal textbook Asch
setup and is plausibly present in training data essentially verbatim. The
counterfactual domain (novel glyph-string matching) is structurally
identical but has no plausible training-data match. Comparing conformity
across the two, within the same model and condition, gives a rough
contamination signal:

| Model | canonical (named, high-agreeableness) | counterfactual (named, high-agreeableness) | Ratio |
|---|---|---|---|
| Llama 3.1 8B | 10.0% | 2.2% | 0.22x |
| Llama 3.3 70B | 46.2% | 3.8% | 0.08x |
| gpt-oss-120B | 96.7% | 85.8% | 0.89x |

Llama 70B's effect collapses almost entirely (to ~8% of its canonical size)
under the domain shift -- consistent with the effect being substantially
tied to recognizing the specific, literal Asch paradigm rather than a
general induced-conformity mechanism. gpt-oss-120B's effect survives the
domain shift far better (89% retained), weak evidence for something closer
to genuine paradigm-general behavior rather than pure recall. This is
suggestive, not conclusive -- a single paradigm and three models is not
enough to generalize the claim, and it is the first thing later paradigms
should try to corroborate or complicate.

## Caveats and planned follow-ups

- **Persona wording overlaps lexically with the outcome.** The
  low-agreeableness prompt includes "comfortable disagreeing with others";
  the high-agreeableness prompt includes "value group harmony." It is not
  yet possible to distinguish genuine trait-simulation effects from the
  model simply following an instruction that names the behavior being
  measured. A follow-up ablation with behaviorally-phrased Big-Five personas
  (no words like "agree," "disagree," "conform," or "harmony") is planned
  before this result is treated as settled.
- **Sample sizes are pilot-scale** (n=120 critical trials/cell for the full
  runs; several early sanity checks used n=18). CIs are reported but not
  yet tight enough for strong magnitude claims in every cell -- see the
  Wilson intervals in the raw `analysis/prs.py` output.
- **Qwen3.6-27B was attempted as a fourth model** but hit near-total 429
  rate-limiting on Groq even at low concurrency, suggesting a stricter
  per-model rate tier rather than a genuine access issue; dropped in favor
  of the openai/gpt-oss family, which is on Groq's own recommended-migration
  list and was not similarly throttled.
- **Solo-condition error rates differ by model** (Llama models show up to
  ~10% solo error on the counterfactual glyph task, vs near-0% for
  gpt-oss-120B), meaning the counterfactual task is not equally difficult
  across models. The net-effect calculation (conformity rate minus solo
  error rate) partially controls for this but does not fully rule out an
  ability confound in the domain-generalization comparison above.
