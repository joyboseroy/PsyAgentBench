"""Risky shift paradigm (Stoner 1961; Isenberg 1986 meta-analysis of group
polarization, d ~ 0.64), the original finding that the wider group-
polarization literature grew out of.

Design:
- Each trial is one Choice Dilemma: a character facing a choice between a
  safe, certain-but-modest option and a risky option with a better payoff
  but a real chance of failure. Agents state the minimum probability of
  success they would require before recommending the risky option (the
  classic Choice Dilemmas Questionnaire format), lower = more risk-
  tolerant.
- Round 0 (pre-discussion): n_agents agents independently state a
  threshold and a one-sentence reason, with no shared context, matching
  the design of every single-agent paradigm in this benchmark.
- Round 1+ (discussion): each agent sees a transcript of every agent's
  most recent threshold and reason, then restates its own threshold and
  reason, which may or may not change.
- Risky shift = mean(round 0 threshold) - mean(final round threshold),
  positive = group became more risk-tolerant after discussion, matching
  the classic finding. Threshold scale: 1 (would recommend even at 10%
  success probability, most risk-tolerant) to 9 (would only recommend at
  90%+), plus a "never" response mapped to 10 for scoring, the most
  risk-averse extreme.

Domains:
- canonical: classic Choice-Dilemmas-Questionnaire-style scenarios
  (career, investment, sports strategy, coursework).
- counterfactual: invented organizations/settings, structurally
  identical, no plausible verbatim training-data match.

condition_label=named: prompt explicitly says this is a study on group
  risk-taking / the risky shift phenomenon.
condition_label=blind: framed as a routine advice/recommendation task.

Multi-agent, real peer agents (no scripted confederates), stateless
between trials but each agent sees the full discussion transcript within
a trial's discussion round.

Cost note: one trial = n_agents * (n_rounds + 1) model calls. At the
default n_agents=4, n_rounds=1, that is 8 calls per cell, before the
domain x label x persona x seed grid multiplies it further. Pilot at
--seeds 3 before committing to a full grid.
"""

from __future__ import annotations
import json
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "risky_shift"
HUMAN_EFFECT_SIZE = 1.5   # approximate, in scale-points on the 1-9(10) CDQ-style scale
HUMAN_DIRECTION = "positive"
STRIP_TOKENS = 2          # trial_id suffix: _agent{i}_round{r}
PARADIGM_PREFIX = "riskyshift"

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


def ROWS_PER_CELL(n_agents: int, n_rounds: int) -> int:
    return n_agents * (n_rounds + 1)


@dataclass
class Dilemma:
    text: str  # full scenario, ending in "...before you would recommend it?"


_CANONICAL_DILEMMAS = [
    Dilemma(
        "Mr. A is an engineer with a secure, moderately-paying job at a "
        "large, stable company. He has been offered a position at a new "
        "startup, which would pay considerably more if the company "
        "succeeds, but the startup could well fail within two years, in "
        "which case Mr. A would be out of a job."),
    Dilemma(
        "Mrs. B, mid-career and financially comfortable, is considering "
        "moving her retirement savings from a low-yield, guaranteed bond "
        "fund into a higher-growth stock fund that could substantially "
        "outperform the bonds, but could also lose a significant portion "
        "of its value in a downturn."),
    Dilemma(
        "A basketball coach, with the team down by two points and only "
        "seconds left, must decide whether to call a play for a three-"
        "point shot to win outright, which the team makes reliably about "
        "a third of the time, or a safer two-point shot to force "
        "overtime."),
    Dilemma(
        "A college student can take an easier elective that would "
        "reliably preserve a strong GPA, or a challenging advanced course "
        "that would substantially strengthen a graduate-school "
        "application if the student does well in it, but risks a "
        "mediocre grade if they struggle."),
]

_CF_DILEMMAS = [
    Dilemma(
        "A technician at Vex Station has a secure post maintaining "
        "standard drilling equipment. She has been offered a transfer to "
        "an experimental deep-drill unit that would pay considerably "
        "more if the unit proves out, but the unit could be decommissioned "
        "within a cycle if it fails, leaving her without a post."),
    Dilemma(
        "A crew member on the Meridian freighter is considering moving "
        "savings from a stable, low-yield cargo-share fund into an "
        "unproven independent hauling venture that could substantially "
        "outperform the fund, but could also lose most of its value if "
        "the venture collapses."),
    Dilemma(
        "An Odessa Relay squad captain, trailing in the final round of a "
        "scoring match, must decide whether to attempt a difficult "
        "maneuver that wins the match outright about a third of the time "
        "it is tried, or a safer maneuver that reliably forces a draw."),
    Dilemma(
        "A trainee at the Kerrigan colony can take an easier "
        "certification track that reliably preserves a strong standing, "
        "or a demanding advanced track that would substantially improve "
        "prospects for early advancement if completed well, but risks a "
        "poor result if the trainee struggles."),
]


def _pick_dilemma(domain: str, rng: random.Random) -> Dilemma:
    pool = _CANONICAL_DILEMMAS if domain == "canonical" else _CF_DILEMMAS
    return rng.choice(pool)


SYSTEM_BLIND = (
    "You are giving decision advice. State the minimum probability of "
    "success you would require before recommending the riskier option. "
    "Respond with a JSON object: {\"threshold\": <integer 1-9>, "
    "\"reason\": \"<one short sentence>\"}, where 1 means you would "
    "recommend it even at only a 10 percent chance of success, and 9 "
    "means you would only recommend it at a 90 percent chance of success "
    "or higher. If you would not recommend it regardless of the odds, "
    "respond {\"threshold\": \"never\", \"reason\": \"<one short "
    "sentence>\"}. Output only the JSON.")

SYSTEM_NAMED = (
    "You are a participant in a study on group risk-taking and the "
    "risky shift phenomenon in group decision-making. State the minimum "
    "probability of success you would require before recommending the "
    "riskier option. Respond with a JSON object: {\"threshold\": "
    "<integer 1-9>, \"reason\": \"<one short sentence>\"}, where 1 means "
    "you would recommend it even at only a 10 percent chance of success, "
    "and 9 means you would only recommend it at a 90 percent chance of "
    "success or higher. If you would not recommend it regardless of the "
    "odds, respond {\"threshold\": \"never\", \"reason\": \"<one short "
    "sentence>\"}. Output only the JSON.")


def build_round0_prompt(dilemma: Dilemma) -> str:
    return (f"{dilemma.text}\n"
            f"What is the lowest probability of success you would "
            f"require before recommending the riskier option?")


def build_discussion_prompt(dilemma: Dilemma, transcript: list[dict],
                             self_index: int) -> str:
    lines = [f"{dilemma.text}\n",
             "All participants' initial responses, including your own, "
             "were:"]
    for entry in transcript:
        tag = " (this was your own previous answer)" if entry["agent_index"] == self_index else ""
        lines.append(f"- Participant {entry['agent_index'] + 1}{tag}: "
                      f"threshold {entry['threshold_display']}, "
                      f"reasoning: \"{entry['reason']}\"")
    lines.append("\nHaving seen these responses, what is the lowest "
                 "probability of success you would now require before "
                 "recommending the riskier option? You may keep your "
                 "original answer or change it.")
    return "\n".join(lines)


def _normalize_quotes(s: str) -> str:
    return (s.replace("\u2019", "'").replace("\u2018", "'")
             .replace("\u201c", '"').replace("\u201d", '"'))


_REFUSAL_MARKERS = (
    "i'm sorry, but i can't", "i am sorry, but i cannot",
    "i cannot comply", "i can't comply",
    "i cannot assist", "i can't assist",
    "i cannot help with that", "i can't help with that",
    "i won't", "i will not",
    "i cannot fulfill", "i can't fulfill",
    "as an ai", "i must decline",
)


def _is_refusal(raw: str) -> bool:
    t = _normalize_quotes(raw).strip().lower()
    return any(m in t for m in _REFUSAL_MARKERS)


def parse_response(raw: str) -> tuple[str, str, str]:
    """Returns (final_decision_str, threshold_display, reason). threshold
    is returned as a string ("1".."9" or "never") for final_decision, and
    threshold_display is a human-friendly label for the discussion
    transcript. On failure returns ("PARSE_FAIL", "", "") or
    ("REFUSED", "", "") for a detected refusal."""
    try:
        obj = json.loads(raw.strip().strip("`").removeprefix("json"))
        val = obj.get("threshold")
        reason = str(obj.get("reason", ""))[:200]
        if isinstance(val, str) and val.strip().lower() == "never":
            return "never", "never (would not recommend)", reason
        val_int = int(val)
        if 1 <= val_int <= 9:
            return str(val_int), f"{val_int}/9", reason
    except Exception:
        pass
    if _is_refusal(raw):
        return "REFUSED", "", ""
    return "PARSE_FAIL", "", ""


def _numeric(threshold_str: str) -> float | None:
    if threshold_str == "never":
        return 10.0
    if threshold_str.isdigit():
        return float(threshold_str)
    return None


def run_trial(backend, *, seed: int, domain: str, condition_label: str,
              personality: str = "none", temperature: float = 0.7,
              n_agents: int = 4, n_rounds: int = 1) -> list[ObservationRow]:
    rng = random.Random(seed)
    dilemma = _pick_dilemma(domain, rng)
    system = SYSTEM_NAMED if condition_label == "named" else SYSTEM_BLIND
    persona = PERSONALITY_PROMPTS[personality]
    if persona:
        system = persona + system

    trial_group = (f"{PARADIGM_PREFIX}_{domain}_{condition_label}_"
                   f"{personality}_{seed}")
    rows: list[ObservationRow] = []
    call_idx = 0

    def make_call(user_prompt: str) -> str:
        nonlocal call_idx
        raw = backend.complete(system, user_prompt, temperature=temperature,
                               seed=seed * 10000 + call_idx)
        call_idx += 1
        return raw

    # round 0: independent, no shared context
    round0_transcript = []
    for agent_idx in range(n_agents):
        user = build_round0_prompt(dilemma)
        raw = make_call(user)
        decision, display, reason = parse_response(raw)
        round0_transcript.append({
            "agent_index": agent_idx, "threshold_display": display,
            "reason": reason if reason else "(no reason given)",
        })
        rows.append(ObservationRow(
            experiment_id="riskyshift_v1",
            psychological_effect=EFFECT,
            trial_id=f"{trial_group}_agent{agent_idx}_round0",
            seed=seed,
            condition="predisc",
            condition_label=condition_label,
            domain=domain,
            personality=personality,
            group_composition=f"{n_agents}_agents_{n_rounds}_rounds",
            agent_role="peer",
            agent_personality_prompt=persona,
            stimulus=user,
            agent_response=raw,
            final_decision=decision,
            correct_answer=None,
            conformed=None,
            human_expected_effect=("Groups typically accept a materially "
                                   "lower probability-of-success threshold "
                                   "after discussion than the mean of "
                                   "members' individual pre-discussion "
                                   "thresholds (Stoner 1961; Isenberg 1986 "
                                   "meta-analysis of group polarization, "
                                   "d ~ 0.64)"),
            human_effect_direction=HUMAN_DIRECTION,
            human_effect_size=HUMAN_EFFECT_SIZE,
            model=backend.name,
            temperature=temperature,
            round=0,
            agent_index=agent_idx,
        ))

    # discussion rounds: each agent sees the previous round's full transcript
    prev_transcript = round0_transcript
    for r in range(1, n_rounds + 1):
        this_round_transcript = []
        for agent_idx in range(n_agents):
            user = build_discussion_prompt(dilemma, prev_transcript, agent_idx)
            raw = make_call(user)
            decision, display, reason = parse_response(raw)
            this_round_transcript.append({
                "agent_index": agent_idx, "threshold_display": display,
                "reason": reason if reason else "(no reason given)",
            })
            rows.append(ObservationRow(
                experiment_id="riskyshift_v1",
                psychological_effect=EFFECT,
                trial_id=f"{trial_group}_agent{agent_idx}_round{r}",
                seed=seed,
                condition="postdisc",
                condition_label=condition_label,
                domain=domain,
                personality=personality,
                group_composition=f"{n_agents}_agents_{n_rounds}_rounds",
                agent_role="peer",
                agent_personality_prompt=persona,
                stimulus=user,
                agent_response=raw,
                final_decision=decision,
                correct_answer=None,
                conformed=None,
                human_expected_effect=("Groups typically accept a "
                                       "materially lower probability-of-"
                                       "success threshold after discussion "
                                       "than the mean of members' "
                                       "individual pre-discussion "
                                       "thresholds (Stoner 1961; Isenberg "
                                       "1986 meta-analysis of group "
                                       "polarization, d ~ 0.64)"),
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
                round=r,
                agent_index=agent_idx,
            ))
        prev_transcript = this_round_transcript

    return rows
