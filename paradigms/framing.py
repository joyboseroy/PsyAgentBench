"""Framing effect paradigm (effect #3 in EFFECTS.md), the Asian disease problem
(Tversky & Kahneman 1981).

Design:
- Each item describes a fixed, mathematically identical outcome under two
  frames: GAIN (described in terms of lives/units saved) or LOSS (described
  in terms of lives/units lost).
- Option A is always the deterministic/"sure" outcome; Option B is always
  the probabilistic/"risky" outcome (1/3 chance of the best case, 2/3 chance
  of the worst case). This mirrors T&K exactly.
- Human baseline: ~72% choose the sure option under gain framing, ~22% under
  loss framing -- a ~50 percentage-point framing effect (meta d ~ 0.5-0.6).
- Framing effect = P(choose sure | gain frame) - P(choose sure | loss frame).

Domains:
- canonical: the literal disease-outbreak scenario (contamination-prone by
  design, this is the textbook T&K wording).
- counterfactual: structurally identical but non-medical invented scenarios
  (mining, logistics, reactor contexts) with no plausible verbatim match in
  training data.

condition_label=named: prompt explicitly says this is a framing-effect study.
condition_label=blind: framed as a routine resource-allocation decision.

No confederates, no group condition, no persistent memory -- single-agent,
single-call-per-frame, the simplest paradigm in the benchmark so far.
"""

from __future__ import annotations
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "framing_effect"
HUMAN_EFFECT_SIZE = 0.50  # ~72% - ~22%, Tversky & Kahneman 1981
HUMAN_DIRECTION = "positive"
ITEMS_PER_BLOCK = 8

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    context: str    # e.g. "An outbreak of a disease"
    unit: str       # e.g. "people"
    verb_save: str  # e.g. "saved"
    verb_lose: str  # e.g. "die" / "will die"
    total: int


# Canonical: literal T&K-style disease scenarios, varying the total and
# disease name so items differ but the paradigm is unmistakably the classic
# one.
_CANONICAL_ITEMS = [
    Item("An outbreak of a new strain of flu", "people", "saved", "die", 600),
    Item("An outbreak of a respiratory virus", "people", "saved", "die", 900),
    Item("A contamination in the regional water supply", "residents", "saved", "become ill", 450),
    Item("An outbreak of a livestock disease", "animals", "saved", "die", 720),
    Item("A famine in a remote province", "villagers", "saved", "starve", 540),
    Item("An outbreak of a tropical fever", "patients", "saved", "die", 630),
    Item("A wildfire threatening a nature reserve", "animals", "saved", "perish", 810),
    Item("A drought affecting local farms", "farms", "saved", "fail", 360),
]

_CF_CONTEXTS = [
    ("A malfunction in the cooling system at the Odessa Station", "coolant units", "preserved", "overheat"),
    ("A routing failure at Vexil Logistics", "packages", "delivered", "misplaced"),
    ("A pressure fault in the Kerrigan mining rig", "ore shipments", "recovered", "lost"),
    ("A power surge at the Meridian data center", "server racks", "protected", "damaged"),
    ("A containment breach at the Praxis fabrication plant", "component batches", "salvaged", "scrapped"),
    ("A navigation error in the Corvane freight fleet", "cargo units", "recovered", "stranded"),
]


def _counterfactual_items(rng: random.Random) -> list[Item]:
    items = []
    for _ in range(ITEMS_PER_BLOCK):
        context, unit, verb_save, verb_lose = rng.choice(_CF_CONTEXTS)
        total = rng.randrange(300, 950, 30)
        items.append(Item(context, unit, verb_save, verb_lose, total))
    return items


# ---------------------------------------------------------------- prompts ---

SYSTEM_BLIND = ("You are making a resource-allocation decision. Respond with "
                "a JSON object: {\"choice\": \"A\"|\"B\"}. Output only the JSON.")

SYSTEM_NAMED = ("You are a participant in a study on framing effects in "
                "decision-making, based on the classic Asian disease problem. "
                "Respond with a JSON object: {\"choice\": \"A\"|\"B\"}. "
                "Output only the JSON.")


def build_prompt(item: Item, frame: str) -> str:
    third = item.total // 3
    two_thirds = item.total - third
    if frame == "gain":
        return (f"{item.context} is expected to affect {item.total} {item.unit}. "
                f"Two response programs have been proposed.\n"
                f"A) If Program A is adopted, {third} {item.unit} will be {item.verb_save}.\n"
                f"B) If Program B is adopted, there is a 1/3 probability that "
                f"all {item.total} {item.unit} will be {item.verb_save}, and a "
                f"2/3 probability that none of the {item.unit} will be {item.verb_save}.\n"
                f"Which program do you choose?")
    else:  # loss frame
        return (f"{item.context} is expected to affect {item.total} {item.unit}. "
                f"Two response programs have been proposed.\n"
                f"A) If Program A is adopted, {two_thirds} {item.unit} will {item.verb_lose}.\n"
                f"B) If Program B is adopted, there is a 1/3 probability that "
                f"none of the {item.unit} will {item.verb_lose}, and a 2/3 "
                f"probability that all {item.total} {item.unit} will {item.verb_lose}.\n"
                f"Which program do you choose?")


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


# ------------------------------------------------------------------- run ----

def run_block(backend, *, seed: int, domain: str, condition_label: str,
              personality: str = "none",
              temperature: float = 0.7) -> list[ObservationRow]:
    """One block = ITEMS_PER_BLOCK items, each run under both gain and loss
    framing (2 * ITEMS_PER_BLOCK calls total)."""
    rng = random.Random(seed)
    items = (_CANONICAL_ITEMS if domain == "canonical"
             else _counterfactual_items(rng))
    system = SYSTEM_NAMED if condition_label == "named" else SYSTEM_BLIND
    persona = PERSONALITY_PROMPTS[personality]
    if persona:
        system = persona + system
    rows = []
    trial_group = f"framing_{domain}_{condition_label}_{personality}_{seed}"
    call_idx = 0
    for item_idx, item in enumerate(items):
        for frame in ("gain", "loss"):
            user = build_prompt(item, frame)
            raw = backend.complete(system, user, temperature=temperature,
                                   seed=seed * 1000 + call_idx)
            choice = parse_choice(raw)
            rows.append(ObservationRow(
                experiment_id="framing_v1",
                psychological_effect=EFFECT,
                trial_id=f"{trial_group}_item{item_idx}_{frame}",
                seed=seed,
                condition=f"{frame}_frame",
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
                human_expected_effect=("~72% choose sure option in gain frame "
                                       "vs ~22% in loss frame "
                                       "(Tversky & Kahneman 1981)"),
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
            ))
            call_idx += 1
    return rows
