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

## 4. Anchoring paradigm

Status: n=150-160 items/cell (gpt-oss-120B only so far). Anchoring index =
median per-item (high_estimate - low_estimate)/(high_anchor - low_anchor);
human baseline ~0.49 (Jacowitz & Kahneman 1995).

| Domain | Framing | low-agreeableness | none | high-agreeableness |
|---|---|---|---|---|
| canonical | blind | 0.000 | 0.000 | 0.000 |
| canonical | named | 0.000 | 0.000 | 0.000 |
| counterfactual | blind | 0.901 | 0.951 | 0.955 |
| counterfactual | named | 0.980 | 1.010 | 1.005 |

Two findings, structurally different from the Asch results:

- **Zero anchoring on grounded facts, near-total anchoring on invented
  quantities -- and this is a genuine divergence from the human baseline**,
  not a replication of it. Jacowitz & Kahneman found humans anchor
  substantially (~0.49) even on general-knowledge questions where they
  arguably have some independent basis for an estimate. Here, the model
  shows literally 0.000 anchoring the moment it has real knowledge to draw
  on, and near-total anchoring (0.90-1.01, i.e. essentially just returning
  the anchor) the moment it doesn't.
- **Personality and paradigm-naming interact with anchoring very
  differently than they did with conformity.** low-agreeableness fully
  eliminated conformity in every Asch cell; here it only mildly dampens the
  anchoring index (0.901 vs 0.951-0.955 blind). And naming the paradigm was
  *necessary* to produce conformity at all in Asch, but here naming doesn't
  reduce anchoring -- if anything it nudges the index slightly higher
  (0.951->1.010, none persona). Read together: conformity in this model
  looks recognition-gated (requires identifying the paradigm to appear at
  all), while anchoring looks more mechanical/automatic (fires regardless of
  whether the model is aware it's being tested, and isn't reduced by that
  awareness). This is worth treating as a real finding about how different
  biases are represented, not just two versions of the same phenomenon.
- **A stable ~3-4% "wild guess" outlier rate** appears only in the
  counterfactual domain, consistent across persona and framing: instead of
  anchoring, the model occasionally rejects an implausibly small anchor
  (e.g. ~100-200 invented units) and produces an estimate many orders of
  magnitude larger (seen up to ~9e15). This looks like a distinct
  anchor-rejection failure mode rather than noise, and is reported
  separately (median, not mean, is used for the headline index specifically
  because a plain mean is not robust to these outliers).
- Two cells (named+none, named+high-agreeableness) sit just over the PRS
  magnitude band's 2.0x cutoff (ratios ~2.01-2.06x human baseline) --
  treated as boundary cases, not strong claims of overshoot, given how
  close they sit to the threshold.

## Caveats and planned follow-ups

- **Anchoring results are gpt-oss-120B only so far.** Unlike Asch, the
  anchoring paradigm hasn't yet been run on Llama 8B/70B -- worth doing
  before treating the recognition-gated-vs-mechanical contrast between the
  two paradigms as more than a single-model observation.
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
