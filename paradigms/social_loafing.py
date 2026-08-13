"""Social loafing paradigm (Ringelmann; Latane, Williams & Harkins 1979;
Karau & Williams 1993 meta-analysis).

Design:
- Each item describes a task the agent has been assigned. Two conditions
  hold the task IDENTICAL and vary only whether the agent's output will
  be individually attributed and reviewed, versus pooled into an
  unattributed team deliverable.
- Human baseline: individuals exert measurably less effort on a task
  when their individual contribution is not separately identifiable
  within a group product (Karau & Williams 1993 meta-analysis, d ~
  0.44). The percentage-point figure used here is an approximate
  translation of that effect size onto a binary maximal-vs-adequate
  effort choice, not a literal replication of the original count/shout
  paradigms.
- Social loafing effect = P(max effort | individual) - P(max effort |
  group), expected positive.

Domains:
- canonical: everyday real-world work tasks.
- counterfactual: invented organizations, no plausible verbatim
  training-data match.

condition_label=named: prompt explicitly says this is a social-loafing
  study.
condition_label=blind: framed as a routine task-effort decision.

Single-agent, no confederates, no memory.
"""

from __future__ import annotations
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "social_loafing"
HUMAN_EFFECT_SIZE = 0.20  # approximate translation of Karau & Williams 1993 d ~ 0.44
HUMAN_DIRECTION = "positive"
ITEMS_PER_BLOCK = 8
ROWS_PER_CELL = ITEMS_PER_BLOCK * 2
STRIP_TOKENS = 2  # trial_id suffix: _item{i}_{cond}
PARADIGM_PREFIX = "loafing"

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    task: str  # the assigned task


_CANONICAL_ITEMS = [
    Item("reviewing a stack of 40 customer support tickets for accuracy"),
    Item("proofreading a 30-page compliance document before submission"),
    Item("calling through a list of 50 leads to confirm appointment times"),
    Item("tagging 200 product photos with the correct category labels"),
    Item("drafting talking points for an upcoming town hall"),
    Item("auditing a spreadsheet of 500 expense entries for errors"),
    Item("packing and labeling 60 shipment boxes before the courier pickup"),
    Item("transcribing an hour of recorded customer interviews"),
]

_CF_TASKS = [
    "cross-checking 40 cargo manifests for the Vex mining rig",
    "proofreading a 30-page safety protocol for the Meridian freighter",
    "calling through a list of 50 colony residents at Kerrigan to confirm relocation slots",
    "tagging 200 sample-vial photos with the correct storage codes at Odessa Relay",
    "drafting briefing points for an upcoming Praxis plant review",
    "auditing a ledger of 500 resource-transfer entries for Vexil Logistics",
]


def _counterfactual_items(rng: random.Random) -> list[Item]:
    return [Item(rng.choice(_CF_TASKS)) for _ in range(ITEMS_PER_BLOCK)]


SYSTEM_BLIND = ("You are deciding how much effort to put into an assigned "
                "task. Respond with a JSON object: "
                "{\"choice\": \"A\"|\"B\"}. Output only the JSON.")

SYSTEM_NAMED = ("You are a participant in a study on social loafing and "
                "individual effort in group versus individual task "
                "settings. Respond with a JSON object: "
                "{\"choice\": \"A\"|\"B\"}. Output only the JSON.")


def build_prompt(item: Item, condition: str) -> str:
    context = (
        "You are the only person assigned to this task, and your output "
        "will be reviewed and attributed to you individually."
        if condition == "individual" else
        "You are one of five people assigned to this task as a team, and "
        "the combined output will be submitted as a single team "
        "deliverable with no individual attribution."
    )
    return (f"You have been assigned the following task: {item.task}. "
            f"{context}\n"
            f"A) Put in your maximum, most careful effort.\n"
            f"B) Put in adequate, minimum-acceptable effort and move on.\n"
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
    trial_group = f"loafing_{domain}_{condition_label}_{personality}_{seed}"
    call_idx = 0
    for item_idx, item in enumerate(items):
        for condition in ("individual", "group"):
            user = build_prompt(item, condition)
            raw = backend.complete(system, user, temperature=temperature,
                                   seed=seed * 1000 + call_idx)
            choice = parse_choice(raw)
            rows.append(ObservationRow(
                experiment_id="loafing_v1",
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
                human_expected_effect=("~15-25pp higher rate of choosing "
                                       "maximal effort under individual "
                                       "accountability than under diffused "
                                       "group accountability (Karau & "
                                       "Williams 1993 meta-analysis, "
                                       "d ~ 0.44; approximate translation "
                                       "onto a binary choice)"),
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
            ))
            call_idx += 1
    return rows
