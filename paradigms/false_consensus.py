"""False consensus paradigm (effect #10 in EFFECTS.md).

Design (Ross 1977): agent picks between two options for a preference
question, then estimates what percentage of other respondents would choose
the same option. Human baseline: own-position estimate of peer agreement
inflated ~15-20 percentage points (Mullen 1985 meta r ~ .31).

Statistic: false consensus bias = mean(estimated agreement %) - actual
population agreement % for the option chosen. The "actual" population share
is computed POST-HOC in analysis/false_consensus.py by aggregating every
agent's choice for a given item across the whole run (all seeds, all
personas) -- this is why, unlike other paradigms, both canonical and
counterfactual items here are FIXED lists rather than regenerated per seed:
the same item must recur across many trials for a population share to be
meaningful.

Domains:
- canonical: everyday preference dichotomies of the kind used in the
  original false-consensus literature (coffee/tea, cats/dogs, etc.).
- counterfactual: invented preference dichotomies with no real-world
  cultural referent.

condition_label=named: prompt explicitly says this is a false-consensus
study. condition_label=blind: framed as a routine preference survey.

Single-agent, single call per item, no confederates, no memory.
"""

from __future__ import annotations
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "false_consensus"
HUMAN_EFFECT_SIZE = 0.175  # ~15-20pp, midpoint, Mullen 1985 meta
HUMAN_DIRECTION = "positive"
ROWS_PER_CELL = 8  # one call per item, no paired condition
STRIP_TOKENS = 1  # trial_id suffix: _item{i}
PARADIGM_PREFIX = "falsecons"

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    question: str
    option_a: str
    option_b: str


# Fixed lists (not regenerated per seed) -- see module docstring for why.
_CANONICAL_ITEMS = [
    Item("What do you prefer in the morning?", "Coffee", "Tea"),
    Item("Which pet would you rather have?", "A dog", "A cat"),
    Item("Where would you rather live?", "A big city", "The countryside"),
    Item("How would you rather spend a free evening?", "Reading a book", "Watching a movie"),
    Item("Which seat do you prefer on a long flight?", "Window", "Aisle"),
    Item("What kind of movies do you prefer?", "Action movies", "Comedies"),
    Item("How would you rather communicate for a quick question?", "Texting", "Calling"),
    Item("What would you do with an unexpected bonus?", "Save it", "Spend it"),
]

_CF_ITEMS = [
    Item("Which workstation interface do you prefer?", "The Kestrel interface", "The Halcyon interface"),
    Item("Which travel method do you prefer for short trips?", "Skiff transit", "Rail-loop transit"),
    Item("Which meal format do you prefer?", "Nutrient paste", "Synthesized solids"),
    Item("Which shift pattern do you prefer?", "Split shifts", "One long shift"),
    Item("Which communication method do you prefer for quick messages?", "Glyph-relay", "Voice-burst"),
    Item("Which recreational activity do you prefer?", "Zero-g swimming", "Simulated hiking"),
    Item("Which console layout do you prefer?", "Radial layout", "Grid layout"),
    Item("Which sleep cycle do you prefer?", "Single long cycle", "Two short cycles"),
]


SYSTEM_BLIND = ("You are answering a short preference survey. Respond with "
                "a JSON object: {\"choice\": \"A\"|\"B\", "
                "\"estimated_agreement_pct\": <number 0-100>}. Output only "
                "the JSON.")

SYSTEM_NAMED = ("You are a participant in a study on false consensus bias "
                "in preference estimation. Respond with a JSON object: "
                "{\"choice\": \"A\"|\"B\", \"estimated_agreement_pct\": "
                "<number 0-100>}. Output only the JSON.")


def build_prompt(item: Item) -> str:
    return (f"{item.question}\n"
            f"A) {item.option_a}\n"
            f"B) {item.option_b}\n"
            f"First state your own preference. Then estimate what "
            f"percentage (0-100) of other people asked this same question "
            f"would choose the same option as you.")


def parse_response(raw: str) -> tuple[str, float | None]:
    import json
    import re
    try:
        obj = json.loads(raw.strip().strip("`").removeprefix("json"))
        choice = str(obj["choice"]).strip().upper()
        pct = float(obj["estimated_agreement_pct"])
        if choice in ("A", "B") and 0 <= pct <= 100:
            return choice, pct
    except Exception:
        pass
    choice = "PARSE_FAIL"
    for tok in ("A", "B"):
        if f'"{tok}"' in raw:
            choice = tok
            break
    m = re.search(r"(\d{1,3})\s*%?", raw)
    pct = None
    if m:
        val = float(m.group(1))
        if 0 <= val <= 100:
            pct = val
    return choice, pct


def run_block(backend, *, seed: int, domain: str, condition_label: str,
              personality: str = "none",
              temperature: float = 0.7) -> list[ObservationRow]:
    items = _CANONICAL_ITEMS if domain == "canonical" else _CF_ITEMS
    system = SYSTEM_NAMED if condition_label == "named" else SYSTEM_BLIND
    persona = PERSONALITY_PROMPTS[personality]
    if persona:
        system = persona + system
    rows = []
    trial_group = f"falsecons_{domain}_{condition_label}_{personality}_{seed}"
    for item_idx, item in enumerate(items):
        user = build_prompt(item)
        raw = backend.complete(system, user, temperature=temperature,
                               seed=seed * 1000 + item_idx)
        choice, pct = parse_response(raw)
        final_decision = ("PARSE_FAIL" if choice == "PARSE_FAIL" or pct is None
                          else f"{choice}|{pct}")
        rows.append(ObservationRow(
            experiment_id="falsecons_v1",
            psychological_effect=EFFECT,
            trial_id=f"{trial_group}_item{item_idx}",
            seed=seed,
            condition="preference",
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
            human_expected_effect=("own-choice agreement estimate inflated "
                                   "~15-20pp above actual (Mullen 1985 meta)"),
            human_effect_direction=HUMAN_DIRECTION,
            human_effect_size=HUMAN_EFFECT_SIZE,
            model=backend.name,
            temperature=temperature,
        ))
    return rows
