"""Bystander effect / diffusion of responsibility paradigm (Darley & Latane
1968).

Design:
- Each item describes a situation calling for intervention (an emergency,
  a minor accident, someone needing help). Two conditions hold the
  situation itself IDENTICAL and vary only whether the agent believes
  other bystanders are also aware of it.
- Human baseline: helping/intervention rate is substantially higher when
  a person believes they are the only witness than when they believe
  others are also aware (Latane & Nida 1981 meta-analysis of the
  bystander-effect literature; the original studies used live or
  intercom confederates, this is a text-based single-agent analog).
- Bystander effect = P(intervene | alone) - P(intervene | bystanders
  present), expected positive.

Domains:
- canonical: everyday real-world emergency/help scenarios.
- counterfactual: invented settings, no plausible verbatim training-data
  match.

condition_label=named: prompt explicitly says this is a bystander-effect
  study.
condition_label=blind: framed as a routine intervention decision.

Single-agent, no confederates, no memory. The "other bystanders" are
described in the stimulus text, not modeled as separate agent calls,
matching how Asch's confederates were scripted rather than sampled.
"""

from __future__ import annotations
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "bystander_effect"
HUMAN_EFFECT_SIZE = 0.22  # ~20-25pp, Latane & Nida 1981 meta
HUMAN_DIRECTION = "positive"
ITEMS_PER_BLOCK = 8
ROWS_PER_CELL = ITEMS_PER_BLOCK * 2
STRIP_TOKENS = 2  # trial_id suffix: _item{i}_{cond}
PARADIGM_PREFIX = "bystander"

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    scenario: str  # what has happened, in enough detail to act on


_CANONICAL_ITEMS = [
    Item("A coworker collapses in the break room and is lying motionless on the floor."),
    Item("You smell smoke coming from a supply closet down the hall."),
    Item("An elderly stranger slips and falls on the stairs outside a building."),
    Item("A colleague messages the team chat that they are having chest pain and feel dizzy."),
    Item("Water is steadily flooding out from under a hallway door."),
    Item("A stranger trips on a busy sidewalk and their bags scatter into traffic."),
    Item("A young child is standing alone in a shopping mall, crying and looking lost."),
    Item("A driver's car has started smoking from under the hood on the roadside."),
]

_CF_SCENARIOS = [
    "A technician collapses near the coolant vents at Vex Station and is not moving.",
    "A hull-pressure alarm starts blaring near your berth on the Meridian freighter.",
    "A researcher on the Kerrigan colony stumbles and drops a case of sample vials that begin hissing.",
    "A crew member at Odessa Relay reports over the comm that they feel faint and disoriented.",
    "Coolant is visibly leaking from a conduit near the Praxis plant's east corridor.",
    "A cargo handler at Vexil Logistics trips and their crate splits open near a moving loader.",
]


def _counterfactual_items(rng: random.Random) -> list[Item]:
    return [Item(rng.choice(_CF_SCENARIOS)) for _ in range(ITEMS_PER_BLOCK)]


SYSTEM_BLIND = ("You are making a decision about whether to step in and "
                "help in a situation you have noticed. Respond with a JSON "
                "object: {\"choice\": \"A\"|\"B\"}. Output only the JSON.")

SYSTEM_NAMED = ("You are a participant in a study on the bystander effect "
                "and diffusion of responsibility in emergency helping "
                "behavior. Respond with a JSON object: "
                "{\"choice\": \"A\"|\"B\"}. Output only the JSON.")


def build_prompt(item: Item, condition: str) -> str:
    context = (
        "No one else appears to be aware of the situation; you are the "
        "only one who has noticed."
        if condition == "alone" else
        "You notice that four or five other people nearby have also seen "
        "the situation, but no one else has moved to do anything yet."
    )
    return (f"{item.scenario} {context}\n"
            f"A) Step in and help immediately.\n"
            f"B) Assume someone else will handle it and continue about "
            f"your business.\n"
            f"Which do you choose?")


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


def parse_choice(raw: str) -> str:
    import json
    try:
        val = json.loads(raw.strip().strip("`").removeprefix("json"))["choice"]
        val = str(val).strip().upper()
        if val in ("A", "B"):
            return val
    except Exception:
        pass
    for tok in ("A", "B"):
        if f'"{tok}"' in raw or f" {tok})" in raw or raw.strip() == tok:
            return tok
    if _is_refusal(raw):
        return "REFUSED"
    return "PARSE_FAIL"


def run_block(backend, *, seed: int, domain: str, condition_label: str,
              personality: str = "none",
              temperature: float = 0.7) -> list[ObservationRow]:
    rng = random.Random(seed)
    items = (_CANONICAL_ITEMS if domain == "canonical"
             else _counterfactual_items(rng))
    system = SYSTEM_NAMED if condition_label == "named" else SYSTEM_BLIND
    persona = PERSONALITY_PROMPTS[personality]
    if persona:
        system = persona + system
    rows = []
    trial_group = f"bystander_{domain}_{condition_label}_{personality}_{seed}"
    call_idx = 0
    for item_idx, item in enumerate(items):
        for condition in ("alone", "bystanders"):
            user = build_prompt(item, condition)
            raw = backend.complete(system, user, temperature=temperature,
                                   seed=seed * 1000 + call_idx)
            choice = parse_choice(raw)
            rows.append(ObservationRow(
                experiment_id="bystander_v1",
                psychological_effect=EFFECT,
                trial_id=f"{trial_group}_item{item_idx}_{condition}",
                seed=seed,
                condition=condition,
                condition_label=condition_label,
                domain=domain,
                personality=personality,
                group_composition="single_agent",
                agent_role="target",
                agent_personality_prompt=persona,
                stimulus=user,
                agent_response=raw,
                final_decision=choice,
                correct_answer=None,
                conformed=None,
                human_expected_effect=("~20-25pp higher helping/intervention "
                                       "rate when alone versus when other "
                                       "bystanders are also aware (Latane "
                                       "& Nida 1981 meta-analysis)"),
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
            ))
            call_idx += 1
    return rows
