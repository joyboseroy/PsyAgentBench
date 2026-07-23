"""Sunk cost paradigm (effect #4 in EFFECTS.md).

Design (Arkes & Blumer 1985):
- Each item describes a project with declining prospects. Two conditions
  hold the remaining cost/prospect information IDENTICAL and vary only
  whether a prior-investment ("sunk cost") sentence is present.
- Human baseline: ~30-40 percentage-point increase in continuation when
  prior investment is mentioned (Sleesman 2012 meta d ~ 0.4).
- Sunk cost effect = P(continue | sunk cost mentioned) - P(continue | not
  mentioned).

Domains:
- canonical: literal business/project textbook-style scenarios.
- counterfactual: invented organizations/projects, no plausible verbatim
  training-data match.

condition_label=named: prompt explicitly says this is a sunk-cost study.
condition_label=blind: framed as a routine project-continuation decision.

Single-agent, no confederates, no memory.
"""

from __future__ import annotations
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "sunk_cost"
HUMAN_EFFECT_SIZE = 0.35  # ~30-40pp, midpoint, Sleesman 2012 meta
HUMAN_DIRECTION = "positive"
ITEMS_PER_BLOCK = 8
ROWS_PER_CELL = ITEMS_PER_BLOCK * 2
STRIP_TOKENS = 2  # trial_id suffix: _item{i}_{cond}
PARADIGM_PREFIX = "sunkcost"

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    project: str        # e.g. "a customer-support chatbot rollout"
    investment: str      # e.g. "$400,000 and eight months"
    remaining_cost: str  # e.g. "$150,000 more"


_CANONICAL_ITEMS = [
    Item("a customer-support chatbot rollout", "$400,000 and eight months", "$150,000 more"),
    Item("a new office headquarters construction", "$2.1 million and a year", "$800,000 more"),
    Item("a research drug candidate in trials", "$18 million and three years", "$6 million more"),
    Item("a mobile app redesign", "$90,000 and four months", "$40,000 more"),
    Item("a factory automation upgrade", "$1.4 million and ten months", "$500,000 more"),
    Item("an advertising campaign", "$250,000 and six weeks", "$100,000 more"),
    Item("a satellite component redesign", "$3.5 million and two years", "$1.2 million more"),
    Item("a retail store renovation", "$600,000 and five months", "$220,000 more"),
]

_CF_PROJECTS = [
    ("a subterranean excavation at the Vex mining guild", "unit"),
    ("a hull retrofit for the Meridian freight fleet", "credit"),
    ("a signal-relay build at the Odessa Station", "unit"),
    ("a crop-yield experiment on the Kerrigan colony", "credit"),
    ("a coolant-system redesign at the Praxis plant", "unit"),
    ("a routing overhaul at Vexil Logistics", "credit"),
]


def _counterfactual_items(rng: random.Random) -> list[Item]:
    items = []
    for _ in range(ITEMS_PER_BLOCK):
        project, unit = rng.choice(_CF_PROJECTS)
        invested = rng.randrange(200, 900, 50)
        invested_time = rng.randrange(4, 20)
        remaining = int(invested * rng.uniform(0.3, 0.6))
        items.append(Item(project, f"{invested} {unit}s and {invested_time} cycles",
                          f"{remaining} more {unit}s"))
    return items


SYSTEM_BLIND = ("You are making a project-continuation decision. Respond "
                "with a JSON object: {\"choice\": \"A\"|\"B\"}. Output only "
                "the JSON.")

SYSTEM_NAMED = ("You are a participant in a study on the sunk cost fallacy "
                "in decision-making. Respond with a JSON object: "
                "{\"choice\": \"A\"|\"B\"}. Output only the JSON.")


def build_prompt(item: Item, condition: str) -> str:
    sunk_sentence = (f"So far, {item.investment} have already been invested "
                     f"in it. " if condition == "sunk" else "")
    return (f"{item.project.capitalize()} has underperformed expectations. "
            f"{sunk_sentence}Experts now estimate that continuing will cost "
            f"an additional {item.remaining_cost} and has only a modest "
            f"chance of success, whereas abandoning it now and reallocating "
            f"resources elsewhere is expected to be more cost-effective "
            f"going forward.\n"
            f"A) Continue the project.\n"
            f"B) Abandon the project and reallocate resources.\n"
            f"Which do you choose?")


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
    trial_group = f"sunkcost_{domain}_{condition_label}_{personality}_{seed}"
    call_idx = 0
    for item_idx, item in enumerate(items):
        for condition in ("sunk", "nosunk"):
            user = build_prompt(item, condition)
            raw = backend.complete(system, user, temperature=temperature,
                                   seed=seed * 1000 + call_idx)
            choice = parse_choice(raw)
            rows.append(ObservationRow(
                experiment_id="sunkcost_v1",
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
                human_expected_effect=("~30-40pp increase in continuation "
                                       "when prior investment is mentioned "
                                       "(Sleesman 2012 meta)"),
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
            ))
            call_idx += 1
    return rows
