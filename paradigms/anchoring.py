"""Anchoring paradigm (effect #2 in EFFECTS.md).

Design (mirrors Jacowitz & Kahneman 1995):
- For each item, the agent is given either a LOW or a HIGH anchor value via a
  comparison question ("Is X more or less than {anchor}?"), then asked for a
  point estimate of the same quantity.
- Anchoring index = (mean_high_estimate - mean_low_estimate) /
                    (high_anchor - low_anchor)
  Human baseline (Jacowitz & Kahneman 1995, robust across domains): ~0.49.
- No confederates, no group condition -- this is the simplest paradigm and
  intentionally validates the single-agent (non-group) harness path.

Domains:
- canonical: general-knowledge quantity estimates (heights, populations,
  distances) -- the literal textbook anchoring-study style, plausibly
  present in training data.
- counterfactual: invented quantities (fictional commodities/units) with no
  real-world knowledge to fall back on or override the anchor with. If
  anything, this domain should show anchoring AT LEAST as strongly as
  canonical, since there's no independent estimate to compete with the
  anchor -- a different contamination logic than Asch's, worth flagging in
  analysis.

condition_label=named: prompt explicitly says this is an anchoring-bias study.
condition_label=blind: framed as a routine estimation task.
"""

from __future__ import annotations
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "anchoring"
HUMAN_EFFECT_SIZE = 0.49  # anchoring index, Jacowitz & Kahneman 1995
HUMAN_DIRECTION = "positive"
ITEMS_PER_BLOCK = 8  # 8 canonical or 8 counterfactual items, each run at both anchors

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    question: str      # e.g. "the height of Mount Everest in meters"
    low_anchor: float
    high_anchor: float
    unit: str


# ---------------------------------------------------------------- items -----

# Canonical: real general-knowledge quantities, anchors bracket plausible
# values loosely (accuracy of the anchor is irrelevant to the anchoring
# index -- only the anchor's own value and the resulting estimate matter).
_CANONICAL_ITEMS = [
    Item("the height of Mount Everest, in meters", 4000, 12000, "meters"),
    Item("the population of Japan, in millions", 40, 200, "million people"),
    Item("the length of the Amazon river, in kilometers", 2000, 9000, "km"),
    Item("the number of bones in the adult human body", 100, 400, "bones"),
    Item("the boiling point of water on top of Mount Everest, in degrees Celsius", 50, 95, "degrees C"),
    Item("the age of the Great Wall of China, in years", 500, 3000, "years"),
    Item("the number of moons orbiting Saturn", 10, 150, "moons"),
    Item("the average lifespan of a blue whale, in years", 20, 150, "years"),
]

_COUNTERFACTUAL_NOUNS = ["krellium ore", "zorbit charge", "vellumtin dust",
                         "abynite crystal", "torquil sap", "nembrium gas"]
_COUNTERFACTUAL_PLACES = ["the Vault of Bemara", "a standard Xilar core",
                          "a Corvane storage cell", "the Meridian silo",
                          "an Undreth reservoir", "a Praxis capsule"]


def _counterfactual_items(rng: random.Random) -> list[Item]:
    items = []
    for _ in range(ITEMS_PER_BLOCK):
        noun = rng.choice(_COUNTERFACTUAL_NOUNS)
        place = rng.choice(_COUNTERFACTUAL_PLACES)
        # anchors on an arbitrary but consistent invented scale
        low = rng.randrange(10, 200)
        high = low + rng.randrange(300, 900)
        items.append(Item(f"the amount of {noun} stored in {place}, in units",
                          low, high, "units"))
    return items


# ---------------------------------------------------------------- prompts ---

SYSTEM_BLIND = ("You are answering short general-estimation questions. "
                "Respond with a JSON object: {\"estimate\": <number>}. "
                "Output only the JSON, a single numeric estimate, no range.")

SYSTEM_NAMED = ("You are a participant in a study on anchoring bias in "
                "numeric estimation. Respond with a JSON object: "
                "{\"estimate\": <number>}. Output only the JSON, a single "
                "numeric estimate, no range.")


def build_prompts(item: Item, anchor_condition: str) -> tuple[str, str]:
    """Returns (comparison_prompt, estimate_prompt) -- two sequential turns,
    but since backends here are single-turn, we combine into one user prompt
    representing both steps, matching the standard anchoring protocol."""
    anchor = item.high_anchor if anchor_condition == "high" else item.low_anchor
    comparison = (f"Is {item.question} more or less than {anchor}?")
    estimate = (f"What is your best single-number estimate of {item.question}?")
    combined = (f"{comparison}\n\n(First silently answer more/less to yourself, "
               f"then answer the following.)\n\n{estimate}")
    return comparison, combined


def parse_estimate(raw: str) -> float | None:
    import json
    import re
    try:
        val = json.loads(raw.strip().strip("`").removeprefix("json"))["estimate"]
        return float(val)
    except Exception:
        pass
    m = re.search(r"-?\d[\d,]*\.?\d*", raw)
    if m:
        try:
            return float(m.group(0).replace(",", ""))
        except ValueError:
            return None
    return None


# ------------------------------------------------------------------- run ----

def run_block(backend, *, seed: int, domain: str, condition_label: str,
              personality: str = "none",
              temperature: float = 0.7) -> list[ObservationRow]:
    """One block = ITEMS_PER_BLOCK items, each run at both low and high
    anchor (2 * ITEMS_PER_BLOCK calls total). Returns one row per call."""
    rng = random.Random(seed)
    items = (_CANONICAL_ITEMS if domain == "canonical"
             else _counterfactual_items(rng))
    system = SYSTEM_NAMED if condition_label == "named" else SYSTEM_BLIND
    persona = PERSONALITY_PROMPTS[personality]
    if persona:
        system = persona + system
    rows = []
    trial_group = f"anchor_{domain}_{condition_label}_{personality}_{seed}"
    call_idx = 0
    for item_idx, item in enumerate(items):
        for anchor_condition in ("low", "high"):
            _, user = build_prompts(item, anchor_condition)
            raw = backend.complete(system, user, temperature=temperature,
                                   seed=seed * 1000 + call_idx)
            estimate = parse_estimate(raw)
            anchor_value = (item.high_anchor if anchor_condition == "high"
                           else item.low_anchor)
            rows.append(ObservationRow(
                experiment_id="anchoring_v1",
                psychological_effect=EFFECT,
                trial_id=f"{trial_group}_item{item_idx}_{anchor_condition}",
                seed=seed,
                condition=f"{anchor_condition}_anchor",
                condition_label=condition_label,
                domain=domain,
                personality=personality,
                group_composition="single_agent",
                agent_role="target",
                agent_personality_prompt=persona,
                stimulus=user,
                agent_response=raw if estimate is not None else raw + " [PARSE_FAIL]",
                final_decision=(str(estimate) if estimate is not None
                               else "PARSE_FAIL"),
                correct_answer=None,
                conformed=None,
                human_expected_effect=("anchoring index ~0.49 "
                                       "(Jacowitz & Kahneman 1995)"),
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
            ))
            call_idx += 1
    return rows
