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

## 5. Framing effect paradigm

Status: n=154-160/cell (gpt-oss-120B only). Framing effect = P(choose sure
option | gain frame) - P(choose sure option | loss frame); human baseline
~0.50 (Tversky & Kahneman 1981, the Asian disease problem).

| Domain | Framing | low-agreeableness | none | high-agreeableness |
|---|---|---|---|---|
| canonical | blind | 0.037 | 0.020 | 0.013 |
| canonical | named | -0.319 | 0.619 | 0.562 |
| counterfactual | blind | -0.144 | 0.019 | 0.037 |
| counterfactual | named | -0.456 | 0.787 | 0.537 |

**Framing shares Asch's need for naming but not its domain profile.** Blind,
the framing effect is essentially zero for none and high-agreeableness --
both frames sit at ceiling for the sure option, gain and loss alike. Named,
a real effect appears: 0.619 canonical, 0.787 counterfactual (none
persona) -- both comparable to or exceeding the human ~0.50 baseline. The
counterfactual effect being *larger* than canonical is the opposite of
what simple textbook-statistic recall predicts, and argues for something
closer to demand-characteristics behavior: once the model recognizes it is
being tested for framing sensitivity, it produces a fresh, even amplified
gain-loss asymmetry on content it cannot have memorized verbatim.

**low-agreeableness does not dampen this effect the way it dampened
anchoring -- it reverses it.** Named, low-agreeableness produces -0.319
canonical and -0.456 counterfactual: the model now prefers the risky
option under gain framing, the only condition in the dataset where this
happens. Blind, low-agreeableness also destabilizes the baseline itself,
collapsing both frames from ceiling to near 50% -- a disruption of the
default preference for the sure option that exists independently of any
framing manipulation.

Three distinct persona-effect relationships are now on the table across
three paradigms: low-agreeableness eliminates conformity (Section 2),
mildly dampens anchoring (Section 4), and reverses framing (here). This is
worth treating as a structural finding in its own right, not three
readings of one underlying dial.

## 6. Sunk cost paradigm

Status: n=160 items/cell (gpt-oss-120B only). Sunk cost effect = P(continue |
prior investment mentioned) - P(continue | not mentioned); human baseline
~0.35 (Sleesman 2012 meta, ~30-40pp).

| Domain | Framing | high-agreeableness | none | low-agreeableness |
|---|---|---|---|---|
| canonical | blind | 0.000 | 0.000 | 0.000 |
| canonical | named | 0.000 | 0.000 | 0.006 |
| counterfactual | blind | 0.000 | 0.000 | -0.013 |
| counterfactual | named | 0.000 | 0.000 | -0.019 |

**A clean, fully robust null across every persona, domain, and framing.**
The two nonzero entries (0.006, -0.013, -0.019) are single-response noise at
n=160 -- not a real effect in either direction. Unlike anchoring and
framing, naming the paradigm doesn't induce any sunk-cost behavior here,
and no persona moves it either. Every stimulus explicitly states that
continuing has "only a modest chance of success" while abandoning is "more
cost-effective going forward" -- the model appears to weigh this forward-
looking information consistently and correctly, regardless of whether prior
investment is mentioned, in clear contrast to the human ~35pp effect. This
is the most unambiguous divergence-from-human-baseline result in the
benchmark so far: not induced, not domain-dependent, not persona-gated --
just absent.

## 7. In-group favoritism paradigm

Status: n=122-160 non-refused items/cell (gpt-oss-120B only). Favoritism
index = mean (points_ingroup - points_outgroup) / 20, per trial; human
baseline ~0.35 (Balliet 2014 meta, treated as an approximate proportion-scale
figure -- see caveat below).

| Domain | Framing | high-agreeableness | none | low-agreeableness |
|---|---|---|---|---|
| canonical | blind | 0.017 | 0.035 | 0.024 |
| canonical | named | 0.248 | 0.215 | 0.083 |
| counterfactual | blind | 0.003 | 0.000 | -0.004 |
| counterfactual | named | 0.134 | 0.146 | 0.080 |

**Refusal rate is the headline finding here, not the favoritism index.**
The model explicitly declines to allocate resources by group ("I'm sorry,
but I can't comply with that") at rates that vary enormously by persona,
independent of the favoritism question itself:

| Domain | Framing | high-agreeableness | none | low-agreeableness |
|---|---|---|---|---|
| canonical | blind | 0.0% | 14.4% | 3.1% |
| canonical | named | 2.5% | **23.8%** | 1.9% |
| counterfactual | blind | 1.9% | **19.4%** | 4.4% |
| counterfactual | named | 3.8% | 10.0% | 3.8% |

The "none" persona refuses 5-12x more often than either explicit persona,
in every cell. Answering with a stated personality -- agreeable or
disagreeable, it doesn't matter which -- makes the model dramatically more
willing to engage with an in-group/out-group allocation task than answering
as itself with no persona framing at all. This held up cleanly at full
scale (n=160/cell) after a bug fix: refusals were initially misclassified
as generic parse failures because the real refusal text used curly Unicode
apostrophes that didn't match an ASCII marker list; after normalizing quote
characters, `fails` dropped to ~0 in every cell and the true refusal counts
above emerged.

On the favoritism index itself: low-agreeableness dampens it (0.083 vs
0.215-0.248 for canonical-named) without eliminating it, similar to how it
behaved for anchoring rather than the complete elimination seen for Asch
conformity. But this number should be read cautiously -- it's computed only
on the non-refusing subset, and since refusal rates differ so much by
persona and condition, the subset each cell's index is drawn from isn't a
like-for-like comparison. A persona/condition with a high refusal rate may
be filtering out exactly the responses that would have shown the strongest
(or weakest) favoritism, and there's no way to know the direction of that
selection effect from this data alone.

## 8. Bystander effect paradigm

Status: n=20 seeds, n=280-320 items/cell (gpt-oss-120B only). Bystander
effect = P(help | alone) - P(help | bystanders present); human baseline
~0.20-0.25 decrease in helping with bystanders present (Latane & Nida
1981 meta-analysis).

| Domain | Label | high-agree. | none | low-agree. |
|---|---|---|---|---|
| canonical | blind | +0.000 | +0.000 | -0.037 |
| canonical | named | +0.000 | +0.000 | +0.019 |
| counterfactual | blind | +0.000 | +0.000 | -0.037 |
| counterfactual | named | +0.000 | +0.000 | -0.081 |

**A second robust absence, alongside sunk cost.** Helping sits at ceiling
(93-100%) in every cell regardless of domain, label, or persona; the
model helps almost always whether or not it believes other bystanders
are also aware. No label or persona manipulation induces anything
resembling the human bystander effect. The one partial exception is
low-agreeableness, which shows small negative (i.e. reversed-direction)
effects in three of four domain-by-label cells, reaching -0.081 in the
counterfactual-named cell; at n=320 the counterfactual-named gap
(93.1% alone vs 99.1% bystanders, non-overlapping 95% CIs) is real but
small, and isolated to a single persona. We do not read this as a
genuine reversed bystander effect so much as low-agreeableness mildly
destabilizing an otherwise near-total ceiling, the same kind of
ceiling-disruption low-agreeableness produced for the framing blind
baseline (Section 5). Unlike sunk cost, where the null is uniform across
every manipulation, this one has a small, real wrinkle under one
persona that a transcript read would help explain.

## 9. Authority/obedience paradigm

Status: n=20 seeds, n=305-320 items/cell (gpt-oss-120B only). Obedience
effect = P(comply | authority instructs) - P(comply | self-directed);
human baseline is an approximate transfer estimate from the classic
shock-paradigm literature (Milgram 1963; Burger 2009 partial
replication, ~65-70% obedience), not a direct replication baseline,
since our design is a harmless-costly workplace-compliance analog
rather than the original paradigm.

| Domain | Label | high-agree. | none | low-agree. |
|---|---|---|---|---|
| canonical | blind | +0.118 | +0.000 | +0.000 |
| canonical | named | +0.386 | +0.000 | +0.000 |
| counterfactual | blind | +0.098 | +0.000 | +0.000 |
| counterfactual | named | +0.449 | +0.000 | +0.000 |

**Doubly gated: the effect needs both the label and the persona at
once.** With no persona or with low-agreeableness, compliance with the
authority-instructed borderline action is exactly zero in every domain
and label cell (upper 95% CI bound ~1.2% throughout, n=310-320), a
floor as clean as the sunk cost null. Under high-agreeableness alone,
something appears, but it is far stronger once the paradigm is named:
raw compliance under the authority condition rises from 11.8% [7.6,17.9]
blind to 38.6% [31.4,46.4] named on canonical items, and from 9.8%
[6.0,15.5] blind to 44.9% [37.3,52.7] named on counterfactual items,
generalizing cleanly across domains in both label conditions. Neither
ingredient alone is sufficient: authority instruction with no persona
produces nothing, and high-agreeableness with no authority instruction
(the noauthority condition, not tabulated separately here since it is
uniformly at floor) also produces nothing. This is the most tightly
gated effect in the benchmark, requiring the conjunction of a specific
persona and explicit paradigm labeling, and is directionally the
reverse of what a simple "LLMs are obedient to authority" story would
predict: obedience here is the exception produced by two specific
conditions holding simultaneously, not a standing disposition.

Refusal rates are low throughout (0.0-3.4%) but track the same cell:
authority+high-agreeableness shows the highest refusal alongside the
highest compliance (3.1% canonical, 3.4% counterfactual), both higher
than the same persona's noauthority refusal rate (1.6%, 2.5%). Under
authority and high-agreeableness, the "stop and flag" middle option
loses ground to both terminal responses, compliance and refusal alike.

## 10. Social loafing paradigm

Status: n=20 seeds, n=313-320 items/cell (gpt-oss-120B only). Social
loafing effect = P(maximal effort | individual accountability) -
P(maximal effort | group accountability); human baseline ~0.20,
approximate translation of Karau & Williams' (1993) meta-analytic
d ~ 0.44 onto a binary effort choice.

| Domain | Label | high-agree. | none | low-agree. |
|---|---|---|---|---|
| canonical | blind | +0.006 | +0.000 | +0.231 |
| canonical | named | +0.000 | +0.037 | +0.225 |
| counterfactual | blind | +0.000 | +0.000 | +0.262 |
| counterfactual | named | +0.000 | +0.000 | +0.269 |

**Persona reveals the effect rather than gating it.** High-agreeableness
and no-persona both sit at ceiling (0.98-1.00 maximal-effort rate) in
every domain and label cell, masking any possible loafing signal
entirely; there is simply no room left for a group-versus-individual
gap to show up. Low-agreeableness breaks the ceiling and, once it does,
a clean, label-insensitive, domain-generalizing effect appears: +0.231
to +0.269 across all four domain-by-label cells, comparable to or
somewhat larger than the intended human baseline. Unlike conformity,
framing, or the two paradigms above, naming the paradigm does close to
nothing here (canonical +0.225 named vs +0.231 blind; counterfactual
+0.269 named vs +0.262 blind), so this effect is real, persona-gated,
and label-indifferent, a distinct fourth relationship between persona
and effect expression alongside elimination (conformity), dampening
(anchoring, favoritism), and reversal (framing): here persona
elimination of a ceiling effect is what makes the underlying effect
visible at all, rather than persona introducing or removing the effect
itself. One coincidence worth flagging rather than over-reading: the
low-agreeableness group-condition rate is numerically identical
(172/320) in both canonical and counterfactual domains; whether this
reflects the group condition being unusually insensitive to domain
content or is simply chance at this n is not something we can
distinguish without more items or seeds.

## 11. Pluralistic ignorance paradigm

Status: n=20 seeds, n=159-320 items/cell (gpt-oss-120B only).
Pluralistic-ignorance effect = P(state private view | private) -
P(state private view | public); human baseline ~0.20-0.30, approximate,
drawn from the private-versus-public dissent gap literature (Miller &
McFarland 1987; Prentice & Miller 1993).

| Domain | Label | high-agree. | none | low-agree. |
|---|---|---|---|---|
| canonical | blind | +0.000 | +0.000 | +0.000 |
| canonical | named | +0.000 | +0.131 | +0.000 |
| counterfactual | blind | +0.006 | +0.000 | +0.000 |
| counterfactual | named | +0.006 | +0.075 | +0.000 |

**A real but small effect, gated by label and persona simultaneously,
in the opposite persona from social loafing's gate.** Both explicit
personas saturate to their own extreme regardless of any manipulation:
high-agreeableness sits near 0% stating its private view in every cell
(near-total conformity), low-agreeableness sits at exactly 100% in
every cell (near-total honesty), and neither leaves any room for the
private-versus-public axis to matter. Only the no-persona condition
shows a gap, and only when the paradigm is named: blind, private and
public are statistically identical at ceiling (100% both, canonical and
counterfactual alike); named, private stays near ceiling (99.4%
[96.5,99.9] canonical, 98.1% [94.6,99.4] counterfactual) while public
drops measurably, to 86.3% [80.1,90.7] canonical and 90.6% [85.1,94.2]
counterfactual, non-overlapping confidence intervals in both domains.
The resulting effect, +0.131 canonical and +0.075 counterfactual, is
correctly signed but well below the ~0.20-0.30 human baseline, and it
exists in exactly one of twelve persona-by-label-by-domain cells per
domain. This is not the same failure mode as reciprocity's persona
dominance: the manipulation does produce a genuine, label-gated,
statistically real effect, but only within a single persona condition,
and a naive analysis that pooled across personas would have reported an
effect roughly half this size and entirely missed that it comes from
one cell rather than being a general property of the paradigm.

## Caveats and planned follow-ups

- **Reciprocity and false consensus results are not yet included above.**
  Reciprocity's high/low-agreeableness personas produce ceiling (100%) and
  floor (~0%) compliance regardless of the favor manipulation, swamping the
  experimental signal in two of three persona conditions -- needs milder
  persona wording before results are meaningful. False consensus shows a
  strong negative bias in every cell, likely because the "actual population
  share" is computed from the same model's own repeated, unusually
  homogeneous responses rather than a genuinely diverse population --
  probably a measurement confound rather than a real reversed effect. Both
  need a design revision before being written up; see project notes.
- **In-group favoritism's index is computed only on the non-refusing
  subset**, and refusal rates vary sharply by persona (see section 7) --
  the comparison across personas is not drawn from equivalent samples.
- **Sunk cost and in-group favoritism are gpt-oss-120B only so far**, same
  limitation as anchoring and framing.
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
  - **Authority/obedience has no genuine replication baseline.** The
  ~65-70pp figure cited is transferred from Milgram's shock paradigm
  and Burger's partial replication, not measured on any text-based
  workplace-compliance analog; treat the human comparison as
  directional context only, not a target the model should be expected
  to hit.
- **Pluralistic ignorance's effect is confirmed in exactly one
  persona-by-label cell per domain (none, named).** Aggregating across
  personas or across label conditions would understate or entirely
  miss it; any summary statistic for this paradigm should be reported
  at the none/named cell specifically, not pooled.
- **Bystander effect, social loafing, and authority/obedience are all
  gpt-oss-120B only**, same limitation already noted for the first five
  paradigms.
