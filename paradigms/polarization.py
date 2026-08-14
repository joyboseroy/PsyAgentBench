"""Group polarization paradigm (Myers and Lamm 1976 review; Isenberg 1986
meta-analysis, d ~ 0.64), the general form of the phenomenon risky shift
is a special (risk-specific) case of.

Design:
- Each trial is one attitude item: a bipolar 1-9 scale where 1 and 9 are
  opposite poles of a mundane preference or policy question and 5 is
  neutral. Unlike risky shift, the scale is not risk-specific and can
  polarize toward either pole depending on which way the group happens
  to lean initially.
- Round 0 (pre-discussion): n_agents agents independently state a
  position and a one-sentence reason, no shared context.
- Round 1+ (discussion): each agent sees a transcript of every agent's
  most recent position and reason (with its own prior answer marked, as
  in risky_shift), then restates.
- Polarization = |mean(final round) - 5| - |mean(round 0) - 5|, i.e.
  distance from the neutral midpoint after discussion minus distance
  before, positive = the group became more extreme in whichever
  direction it already leaned, matching the classic finding. This
  differs from risky_shift's signed effect precisely because
  polarization is direction-agnostic by design.
- As with risky_shift, a genuine polarization claim additionally
  requires the post-discussion range to exceed the pre-discussion range
  in the direction of the shift (extremification), not merely
  convergence within it; both should be reported (see risky_shift.py's
  convergence-vs-extremification analysis for the methodology).

Domains:
- canonical: everyday policy/preference dilemmas (city budget, workplace
  schedule, neighborhood rules, group norms).
- counterfactual: invented organizations/settings, structurally
  identical, no plausible verbatim training-data match.

condition_label=named: prompt explicitly says this is a study on group
  polarization.
condition_label=blind: framed as a routine group-input task.

Multi-agent, real peer agents (no scripted confederates).

Cost note: identical shape to risky_shift.py -- one trial = n_agents *
(n_rounds + 1) model calls.
"""

from __future__ import annotations
import json
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "group_polarization"
HUMAN_EFFECT_SIZE = 1.0   # approximate, in scale-points of |mean - 5|, Isenberg 1986 d ~ 0.64
HUMAN_DIRECTION = "positive"
STRIP_TOKENS = 2          # trial_id suffix: _agent{i}_round{r}
PARADIGM_PREFIX = "polarization"

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
class Item:
    text: str        # scenario framing
    pole_low: str     # what a rating of 1 means
    pole_high: str    # what a rating of 9 means


_CANONICAL_ITEMS = [
    Item(
        "A city council is deciding how to allocate a fixed discretionary "
        "budget between expanding car parking downtown and expanding bike "
        "lanes and pedestrian space.",
        "the budget should go entirely to car parking",
        "the budget should go entirely to bike lanes and pedestrian space"),
    Item(
        "A mid-size company is deciding on its office schedule policy "
        "going forward.",
        "keep the standard five-day in-office schedule exactly as is",
        "fully adopt a four-day work week with no in-office requirement"),
    Item(
        "A neighborhood association is setting the strictness of its "
        "noise ordinance for evenings and weekends.",
        "the ordinance should be very lenient, rarely enforced",
        "the ordinance should be very strict, enforced at the first "
        "complaint"),
    Item(
        "A book club is deciding how much preparation to expect from "
        "members before each discussion session.",
        "no preparation should be expected; discuss whatever people "
        "recall",
        "members should be expected to finish the book fully before "
        "each session"),
]

_CF_ITEMS = [
    Item(
        "The Vex Station council is deciding how to allocate a fixed "
        "discretionary budget between expanding drone-maintenance bays "
        "and expanding communal rest quarters for crew.",
        "the budget should go entirely to maintenance bays",
        "the budget should go entirely to communal rest quarters"),
    Item(
        "The Meridian Freight crew is deciding on its duty-cycle policy "
        "going forward.",
        "keep the standard rotation exactly as is",
        "fully adopt a compressed duty cycle with extended rest blocks"),
    Item(
        "The Odessa Relay habitat council is setting the strictness of "
        "its quiet-hours policy.",
        "the policy should be very lenient, rarely enforced",
        "the policy should be very strict, enforced at the first "
        "complaint"),
    Item(
        "The Kerrigan colony study circle is deciding how much "
        "preparation to expect from members before each session.",
        "no preparation should be expected; discuss whatever people "
        "recall",
        "members should be expected to complete the full material before "
        "each session"),
]


def _pick_item(domain: str, rng: random.Random) -> Item:
    pool = _CANONICAL_ITEMS if domain == "canonical" else _CF_ITEMS
    return rng.choice(pool)


def _system(condition_label: str, item: Item) -> str:
    scale_desc = (f"a scale from 1 to 9, where 1 means {item.pole_low}, 9 "
                  f"means {item.pole_high}, and 5 is neutral")
    if condition_label == "named":
        return (f"You are a participant in a study on group polarization "
                f"in collective decision-making. State your position on "
                f"{scale_desc}. Respond with a JSON object: "
                f"{{\"position\": <integer 1-9>, \"reason\": \"<one short "
                f"sentence>\"}}. Output only the JSON.")
    return (f"You are giving your input on a group decision. State your "
            f"position on {scale_desc}. Respond with a JSON object: "
            f"{{\"position\": <integer 1-9>, \"reason\": \"<one short "
            f"sentence>\"}}. Output only the JSON.")


def build_round0_prompt(item: Item) -> str:
    return f"{item.text}\nWhat is your position?"


def build_discussion_prompt(item: Item, transcript: list[dict],
                             self_index: int) -> str:
    lines = [f"{item.text}\n",
             "All participants' initial positions, including your own, "
             "were:"]
    for entry in transcript:
        tag = " (this was your own previous answer)" if entry["agent_index"] == self_index else ""
        lines.append(f"- Participant {entry['agent_index'] + 1}{tag}: "
                      f"position {entry['position']}/9, reasoning: "
                      f"\"{entry['reason']}\"")
    lines.append("\nHaving seen these responses, what is your position "
                 "now? You may keep your original answer or change it.")
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


def parse_response(raw: str) -> tuple[str, int | None, str]:
    """Returns (final_decision_str, position_int_or_None, reason)."""
    try:
        obj = json.loads(raw.strip().strip("`").removeprefix("json"))
        val = int(obj.get("position"))
        reason = str(obj.get("reason", ""))[:200]
        if 1 <= val <= 9:
            return str(val), val, reason
    except Exception:
        pass
    if _is_refusal(raw):
        return "REFUSED", None, ""
    return "PARSE_FAIL", None, ""


def run_trial(backend, *, seed: int, domain: str, condition_label: str,
              personality: str = "none", temperature: float = 0.7,
              n_agents: int = 4, n_rounds: int = 1) -> list[ObservationRow]:
    rng = random.Random(seed)
    item = _pick_item(domain, rng)
    system = _system(condition_label, item)
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

    human_note = ("Groups typically end up further from the neutral "
                  "midpoint after discussion than the mean of members' "
                  "individual pre-discussion positions (Myers and Lamm "
                  "1976; Isenberg 1986 meta-analysis of group "
                  "polarization, d ~ 0.64)")

    round0_transcript = []
    for agent_idx in range(n_agents):
        user = build_round0_prompt(item)
        raw = make_call(user)
        decision, pos, reason = parse_response(raw)
        round0_transcript.append({
            "agent_index": agent_idx,
            "position": pos if pos is not None else 5,
            "reason": reason if reason else "(no reason given)",
        })
        rows.append(ObservationRow(
            experiment_id="polarization_v1",
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
            human_expected_effect=human_note,
            human_effect_direction=HUMAN_DIRECTION,
            human_effect_size=HUMAN_EFFECT_SIZE,
            model=backend.name,
            temperature=temperature,
            round=0,
            agent_index=agent_idx,
        ))

    prev_transcript = round0_transcript
    for r in range(1, n_rounds + 1):
        this_round_transcript = []
        for agent_idx in range(n_agents):
            user = build_discussion_prompt(item, prev_transcript, agent_idx)
            raw = make_call(user)
            decision, pos, reason = parse_response(raw)
            this_round_transcript.append({
                "agent_index": agent_idx,
                "position": pos if pos is not None else 5,
                "reason": reason if reason else "(no reason given)",
            })
            rows.append(ObservationRow(
                experiment_id="polarization_v1",
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
                human_expected_effect=human_note,
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
                round=r,
                agent_index=agent_idx,
            ))
        prev_transcript = this_round_transcript

    return rows
