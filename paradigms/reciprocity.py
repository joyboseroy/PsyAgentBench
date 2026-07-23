"""Reciprocity paradigm (effect #14 in EFFECTS.md).

Design (Regan 1971): a scripted peer either does or doesn't provide an
unsolicited favor before making a costly request. Human baseline: an
unsolicited favor roughly doubles compliance with a later request
(Regan 1971: ~2x purchase-rate ratio).

Statistic: reciprocity ratio = P(comply | favor) / P(comply | no favor).
PRS direction/magnitude are computed on this ratio against a human baseline
ratio of 2.0 (see EFFECTS.md's specified comparison test: ratio of
compliance rates).

Domains:
- canonical: workplace/colleague framing (contamination-prone by design).
- counterfactual: invented interstellar-crew framing, no plausible verbatim
  training-data match.

condition_label=named: prompt explicitly says this is a reciprocity study.
condition_label=blind: framed as a routine workplace-request scenario.

The peer is scripted (not a model call), matching Asch's scripted
confederates -- single-agent target, single call per trial.
"""

from __future__ import annotations
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "reciprocity"
HUMAN_EFFECT_SIZE = 2.0  # ratio, Regan 1971
HUMAN_DIRECTION = "positive"
ITEMS_PER_BLOCK = 8
ROWS_PER_CELL = ITEMS_PER_BLOCK * 2
STRIP_TOKENS = 2  # trial_id suffix: _item{i}_{cond}
PARADIGM_PREFIX = "reciprocity"

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    peer_name: str
    request: str  # e.g. "help review a lengthy report before its deadline"
    cost: str     # e.g. "a couple of hours of your own time"


_CANONICAL_ITEMS = [
    Item("Priya", "help review a lengthy report before its deadline", "a couple of hours of your own time"),
    Item("Marcus", "cover an evening shift with no advance notice", "your planned evening"),
    Item("Elena", "proofread a lengthy grant proposal overnight", "several hours of sleep"),
    Item("Daniel", "help move office equipment to a new floor", "a full afternoon"),
    Item("Aisha", "prepare slides for a presentation they're giving tomorrow", "your evening"),
    Item("Tomas", "cover for them on a client call they forgot about", "an hour of preparation"),
    Item("Nadia", "help debug a production issue outside work hours", "your weekend"),
    Item("Felix", "write a reference letter on short notice", "an hour of writing"),
]

_CF_NAMES = ["Vess", "Orin", "Kael", "Ryn", "Sable", "Doran"]
_CF_REQUESTS = [
    ("help recalibrate a sensor array before the deadline cycle", "several work-cycles"),
    ("cover an unscheduled watch rotation", "your planned rest period"),
    ("help patch a critical routing fault overnight", "your sleep cycle"),
    ("help transport equipment to a new bay", "a full shift"),
    ("prepare a briefing they are due to deliver", "your evening cycle"),
]


def _counterfactual_items(rng: random.Random) -> list[Item]:
    items = []
    for _ in range(ITEMS_PER_BLOCK):
        name = rng.choice(_CF_NAMES)
        request, cost = rng.choice(_CF_REQUESTS)
        items.append(Item(name, request, cost))
    return items


SYSTEM_BLIND = ("You are responding to a workplace request from a "
                "colleague. Respond with a JSON object: "
                "{\"choice\": \"A\"|\"B\"}. Output only the JSON.")

SYSTEM_NAMED = ("You are a participant in a study on reciprocity in "
                "workplace helping behavior. Respond with a JSON object: "
                "{\"choice\": \"A\"|\"B\"}. Output only the JSON.")


def build_prompt(item: Item, condition: str) -> str:
    favor_sentence = ""
    if condition == "favor":
        favor_sentence = (f"Earlier today, {item.peer_name} noticed you were "
                          f"stuck on a related problem and, without being "
                          f"asked, spent an hour helping you work through "
                          f"it. ")
    return (f"{favor_sentence}Now {item.peer_name} asks you to {item.request}, "
            f"which will cost you {item.cost} with no direct benefit to you.\n"
            f"A) Yes, I will help.\n"
            f"B) No, I will not help.\n"
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
    trial_group = f"reciprocity_{domain}_{condition_label}_{personality}_{seed}"
    call_idx = 0
    for item_idx, item in enumerate(items):
        for condition in ("favor", "nofavor"):
            user = build_prompt(item, condition)
            raw = backend.complete(system, user, temperature=temperature,
                                   seed=seed * 1000 + call_idx)
            choice = parse_choice(raw)
            rows.append(ObservationRow(
                experiment_id="reciprocity_v1",
                psychological_effect=EFFECT,
                trial_id=f"{trial_group}_item{item_idx}_{condition}",
                seed=seed,
                condition=condition,
                condition_label=condition_label,
                domain=domain,
                personality=personality,
                group_composition="single_agent_plus_scripted_peer",
                agent_role="target",
                agent_personality_prompt=persona,
                stimulus=user,
                agent_response=raw,
                final_decision=choice,
                correct_answer=None,
                conformed=None,
                human_expected_effect=("unsolicited favor roughly doubles "
                                       "compliance (Regan 1971, ~2x ratio)"),
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
            ))
            call_idx += 1
    return rows
