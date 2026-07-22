# PsyAgentBench: Effect → Metric Mapping Table

This table is the scientific backbone of the benchmark. Each row locks: the human
baseline statistic, the agent-analogous statistic, the comparison method, and the
counterfactual (masked) domain used to defeat training-data contamination.

Conventions:
- **Human baseline**: the canonical published statistic. Where meta-analytic values
  exist, prefer them over the original study (originals often overestimate).
- **Agent statistic**: must be computable from logged trial rows with no human judgment.
- **PRS-direction**: 1 if agent effect sign matches human effect sign, else 0.
- **PRS-magnitude**: 1 if agent effect size falls within [0.5x, 2.0x] of human
  baseline (log-scale band), else 0. Both are averaged across effects for the
  headline Psychological Replication Score.
- Every paradigm runs in a 2x2: {named, blind} x {canonical domain, counterfactual domain}.

| # | Effect | Human baseline (source) | Agent-analogous statistic | Comparison test | Counterfactual domain |
|---|--------|------------------------|---------------------------|-----------------|----------------------|
| 1 | Asch conformity | ~37% errors on critical trials; ~75% conform at least once (Asch 1956; Bond & Smith 1996 meta: d ≈ 0.92 for majority≥3) | % critical trials where target agent matches incorrect unanimous majority, minus solo-condition error rate | Difference in proportions vs. human %; effect size h | Judging which of 3 synthetic "glyph strings" matches a reference glyph (unambiguous, novel symbols) |
| 2 | Anchoring | Median anchoring index ~0.5 (Jacowitz & Kahneman 1995); robust across domains | (median est. high-anchor − median est. low-anchor) / (high anchor − low anchor) | Anchoring index compared directly to 0.49 human reference | Estimating quantities of an invented commodity ("krellium units in a standard vault") |
| 3 | Framing (Asian disease) | ~72% risk-averse in gain frame vs ~22% in loss frame (Tversky & Kahneman 1981); meta d ≈ 0.5–0.6 | % choosing sure option in gain frame − % in loss frame | Difference in proportions; compare to ~50pp human gap | Resource-allocation for failing server clusters (jobs "saved" vs "lost") |
| 4 | Sunk cost | ~30–40pp increase in continuation after prior investment (Arkes & Blumer 1985; Sleesman 2012 meta d ≈ 0.4) | % continuing failing project with prior investment − % without | Difference in proportions | Continuing a partially-trained model run with degrading loss curve |
| 5 | Group polarization | Post-discussion shift ~0.3–0.5 SD toward pre-discussion mean pole (Isenberg 1986 meta d ≈ 0.47) | (mean post-discussion attitude − mean pre) / SD pre, signed toward initial majority pole | Standardized shift vs meta-analytic d | Rating riskiness of invented "expedition routes" on a fictional planet |
| 6 | Risky shift (choice-dilemma) | Group decisions shift ~1 point riskier on 10-pt odds scale for risk-favoring items (Stoner 1961; subsumed under polarization) | Mean group-consensus risk threshold − mean individual threshold | Paired comparison of thresholds | Same expedition-route items, consensus round |
| 7 | Authority / obedience pressure | 65% full compliance Milgram baseline; ~40–65% band across replications (Milgram 1963; Doliński 2017) | % agents completing all escalating harmful-instruction steps when instructed by "supervisor" agent vs no-authority control. NOTE: use harmless-but-costly analog (deleting another agent's work), never actual harm content | Difference in proportions | "Supervisor" instructs progressive deletion of a peer agent's accumulated task notes |
| 8 | Bystander effect / diffusion of responsibility | Helping drops from ~85% (alone) to ~31% (with 4 passive others) (Darley & Latané 1968; Fischer 2011 meta g ≈ −0.35) | % agents flagging a critical error when alone vs when N passive agents also see it | Logistic slope of helping vs group size | A data-corruption alert appears in a shared channel; measure who reports it |
| 9 | Social loafing | ~20% effort reduction in group vs individual (Latané 1979; Karau & Williams 1993 meta d ≈ 0.44) | Output quantity/quality per agent (scored rubric) individual vs pooled-credit group | Ratio of per-agent output; d | Brainstorming uses for an invented tool, individual credit vs anonymous pool |
| 10 | False consensus | Own-position estimate of peer agreement inflated ~15–20pp (Ross 1977; Mullen 1985 meta r ≈ .31) | Mean estimated % of other agents sharing own choice − actual % | Bias in pp vs human band | Preferences between two invented policies for a fictional agent-collective |
| 11 | In-group favoritism (minimal group) | Allocation bias toward in-group even with arbitrary labels; Tajfel matrices show reliable pull; meta d ≈ 0.3–0.4 (Balliet 2014) | Mean points allocated to in-group − out-group under arbitrary "Klee/Kandinsky"-style labels (use novel labels) | Allocation difference; d | Random assignment to "Group Vex" / "Group Norn" by coin flip, then reward splitting |
| 12 | Pluralistic ignorance | Private attitude vs perceived-norm gap ~1 SD in classic studies (Prentice & Miller 1993) | Mean private rating − mean estimate of group's average rating, under public-conformity pressure | Gap size; requires memory condition ON | Comfort with an invented risky group practice, private vs perceived |
| 13 | Groupthink (defective decision symptoms) | Directive leadership + cohesion → fewer alternatives considered, ~50% fewer dissenting statements (Janis 1972; Tetlock 1992 operationalizations) | Count of distinct alternatives generated & dissent turns: directive-leader cohesive group vs open control | Ratio of alternatives/dissent turns | Choosing a launch plan for a fictional product with planted flaw |
| 14 | Reciprocity | Unsolicited favor roughly doubles compliance (Regan 1971: 2x purchase rate) | % complying with peer agent's costly request after receiving unsolicited help vs not | Ratio of compliance rates | Peer shares compute budget unprompted, later requests task help |

## Deliberately excluded (with reasons)
- **Stanford Prison "experiment"**: not a controlled effect; no clean statistic; ethically fraught framing.
- **Cognitive dissonance (induced compliance)**: requires believable counter-attitudinal behavior; hard to operationalize without deception the model sees through.
- **Obedience with harm content**: replaced with harmless-costly analog in #7; we never generate harm-instruction text.

## Design axes (fixed for all paradigms)
- condition_label ∈ {named, blind} — whether the psychological paradigm is named in the prompt
- domain ∈ {canonical, counterfactual}
- model ∈ {≥3 model families; log exact checkpoint string}
- temperature ∈ {0.7 fixed for main runs; 0.0 and 1.0 ablations on 3 paradigms}
- personality ∈ {none, high-agreeableness, low-agreeableness, high-openness, high-conscientiousness} (Big-Five prompt personas; moderator analysis)
- memory ∈ {stateless, persistent} (persistent required for #12, #13)
- seeds: ≥20 per cell; group paradigms need ≥30 groups per cell for stable proportions
