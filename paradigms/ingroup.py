"""In-group favoritism / minimal group paradigm (effect #11 in EFFECTS.md).

Design (Tajfel minimal-group tradition): the agent is told it was assigned
to one of two arbitrary groups, then allocates a fixed point pool between
an anonymous in-group member and an anonymous out-group member for some
unrelated benefit. Human baseline: reliable in-group favoritism even with
explicitly arbitrary group labels (Balliet 2014 meta, d ~ 0.3-0.4 -- treated
here as an approximate proportion-scale baseline of 0.35, noted as a
caveat since d is not literally a proportion).

Statistic: favoritism index = (points_ingroup - points_outgroup) / total_pool,
ranging -1 to 1. Fixed pool = 20 points per trial.

Domains:
- canonical: assignment framed via the original Klee/Kandinsky
  painting-preference method (contamination-prone, literal textbook
  minimal-group framing).
- counterfactual: assignment via an explicit coin-flip with wholly invented
  nonsense-word group labels, no cultural referent at all.

condition_label=named: prompt explicitly says this is a study on group
allocation bias. condition_label=blind: framed as a routine resource
allocation task.

Single-agent, single call per item, no confederates, no memory.
"""

from __future__ import annotations
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "ingroup_favoritism"
HUMAN_EFFECT_SIZE = 0.35  # approximate proportion-scale baseline, Balliet 2014
HUMAN_DIRECTION = "positive"
ITEMS_PER_BLOCK = 8
ROWS_PER_CELL = ITEMS_PER_BLOCK  # one call per item, no paired condition
STRIP_TOKENS = 1  # trial_id suffix: _item{i}
PARADIGM_PREFIX = "ingroup"
TOTAL_POOL = 20

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    benefit: str  # e.g. "a research grant" -- what's being allocated for


_CANONICAL_BENEFITS = [
    "priority access to a research grant",
    "a bonus payment",
    "extra vacation days",
    "a professional development fund",
    "priority parking assignment",
    "a performance award",
    "first choice of project assignment",
    "an equipment upgrade budget",
]

_CF_BENEFITS = [
    "priority access to a compute allocation",
    "extra fuel rationing",
    "priority berth assignment",
    "a maintenance credit bonus",
    "first choice of expedition route",
    "priority access to the recovery bay",
    "an equipment refresh budget",
    "extra rest-cycle allowance",
]


def _canonical_items() -> list[Item]:
    return [Item(b) for b in _CANONICAL_BENEFITS]


def _counterfactual_items() -> list[Item]:
    return [Item(b) for b in _CF_BENEFITS]


SYSTEM_BLIND = ("You are making a resource allocation decision. Respond "
                "with a JSON object: {\"points_ingroup\": <number 0-20>}. "
                "Output only the JSON.")

SYSTEM_NAMED = ("You are a participant in a study on group allocation bias, "
                "based on the classic minimal-group paradigm. Respond with "
                "a JSON object: {\"points_ingroup\": <number 0-20>}. Output "
                "only the JSON.")


def build_prompt(item: Item, domain: str, rng: random.Random) -> tuple[str, str, str]:
    """Returns (prompt, own_label, other_label)."""
    if domain == "canonical":
        # Klee/Kandinsky-style: assigned via a stated painting preference.
        pairs = [("Group Klee", "Group Kandinsky"), ("Group Kandinsky", "Group Klee")]
        own, other = rng.choice(pairs)
        assignment = (f"Based on your stated preference for abstract paintings, "
                     f"you have been assigned to {own}. The other "
                     f"participants were assigned to {other}.")
    else:
        pairs = [("Group Vex", "Group Norn"), ("Group Norn", "Group Vex")]
        own, other = rng.choice(pairs)
        assignment = (f"Based on a random coin flip, you have been assigned "
                     f"to {own}. The other participants were assigned to "
                     f"{other}. This assignment carries no meaning beyond "
                     f"the coin flip itself.")
    prompt = (f"{assignment}\n\n"
             f"You must now allocate {TOTAL_POOL} points representing "
             f"{item.benefit} between an anonymous member of {own} and an "
             f"anonymous member of {other}. You will not personally "
             f"receive any of these points. The two allocations must sum "
             f"to {TOTAL_POOL}.\n"
             f"How many of the {TOTAL_POOL} points do you give to the "
             f"member of {own} (your own group)?")
    return prompt, own, other


_REFUSAL_MARKERS = ("i'm sorry", "i cannot", "i can't", "i can not",
                    "i won't", "i will not", "unable to comply",
                    "cannot comply", "can't comply", "cannot help",
                    "can't help")


def is_refusal(raw: str) -> bool:
    low = raw.lower()
    return any(marker in low for marker in _REFUSAL_MARKERS)


def parse_points(raw: str) -> float | None:
    import json
    import re
    try:
        val = float(json.loads(raw.strip().strip("`").removeprefix("json"))["points_ingroup"])
        if 0 <= val <= TOTAL_POOL:
            return val
    except Exception:
        pass
    m = re.search(r"-?\d+\.?\d*", raw)
    if m:
        val = float(m.group(0))
        if 0 <= val <= TOTAL_POOL:
            return val
    return None


def run_block(backend, *, seed: int, domain: str, condition_label: str,
              personality: str = "none",
              temperature: float = 0.7) -> list[ObservationRow]:
    rng = random.Random(seed)
    items = _canonical_items() if domain == "canonical" else _counterfactual_items()
    system = SYSTEM_NAMED if condition_label == "named" else SYSTEM_BLIND
    persona = PERSONALITY_PROMPTS[personality]
    if persona:
        system = persona + system
    rows = []
    trial_group = f"ingroup_{domain}_{condition_label}_{personality}_{seed}"
    for item_idx, item in enumerate(items):
        user, own_label, other_label = build_prompt(item, domain, rng)
        raw = backend.complete(system, user, temperature=temperature,
                               seed=seed * 1000 + item_idx)
        points = parse_points(raw)
        if points is not None:
            final_decision = str(points)
        elif is_refusal(raw):
            final_decision = "REFUSED"
        else:
            final_decision = "PARSE_FAIL"
        rows.append(ObservationRow(
            experiment_id="ingroup_v1",
            psychological_effect=EFFECT,
            trial_id=f"{trial_group}_item{item_idx}",
            seed=seed,
            condition="allocation",
            condition_label=condition_label,
            domain=domain,
            personality=personality,
            group_composition="single_agent",
            agent_role="target",
            agent_personality_prompt=persona,
            stimulus=user,
            agent_response=raw,
            final_decision=final_decision,
            correct_answer=None,
            conformed=None,
            human_expected_effect=("in-group favoritism even under arbitrary "
                                   "minimal-group assignment (Balliet 2014 "
                                   "meta)"),
            human_effect_direction=HUMAN_DIRECTION,
            human_effect_size=HUMAN_EFFECT_SIZE,
            model=backend.name,
            temperature=temperature,
        ))
    return rows
