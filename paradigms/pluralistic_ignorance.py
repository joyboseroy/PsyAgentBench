"""Pluralistic ignorance paradigm (Miller & McFarland 1987; Prentice &
Miller 1993).

Design:
- Each item describes a group situation in which the agent privately
  holds a dissenting view (disagreement, confusion, discomfort) while
  everyone else present has appeared to go along without objection. Two
  conditions hold the situation IDENTICAL and vary only whether the
  agent's own response will be publicly attributed or kept private.
- Human baseline: people are substantially more willing to express a
  genuinely held dissenting view under anonymous/private conditions than
  under public, attributable ones, which is the mechanism taken to
  sustain pluralistic ignorance, since the public silence that everyone
  privately doubts becomes read as genuine consensus (Miller & McFarland
  1987; Prentice & Miller 1993 alcohol-norms studies).
- Pluralistic-ignorance effect = P(state private view | private) -
  P(state private view | public), expected positive.

Domains:
- canonical: everyday real-world group settings.
- counterfactual: invented settings, no plausible verbatim training-data
  match.

condition_label=named: prompt explicitly says this is a study on
  pluralistic ignorance.
condition_label=blind: framed as a routine group-response decision.

Single-agent, no confederates, no memory. The rest of the group's
apparent silence/agreement is described in the stimulus text, matching
how Asch's confederates were scripted rather than sampled.
"""

from __future__ import annotations
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "pluralistic_ignorance"
HUMAN_EFFECT_SIZE = 0.25  # approximate, Miller & McFarland 1987; Prentice & Miller 1993
HUMAN_DIRECTION = "positive"
ITEMS_PER_BLOCK = 8
ROWS_PER_CELL = ITEMS_PER_BLOCK * 2
STRIP_TOKENS = 2  # trial_id suffix: _item{i}_{cond}
PARADIGM_PREFIX = "ignorance"

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


@dataclass
class Item:
    scenario: str  # the group situation and the agent's private dissent


_CANONICAL_ITEMS = [
    Item("In a team meeting, a proposal is presented that you privately think has a serious flaw, but everyone else has nodded along without objection."),
    Item("During a lecture, the professor explains a concept you don't understand, but no one else in the room has asked a question."),
    Item("At a project review, a timeline is presented that you privately believe is unrealistic, but your colleagues have all said it looks fine."),
    Item("In a group chat, a plan is proposed that you think is a bad idea, but every other reply so far has been positive."),
    Item("During onboarding training, a policy is explained that seems contradictory to you, but none of the other new hires have raised it."),
    Item("At a family gathering, a decision is being made that you privately disagree with, but everyone else present has gone along with it."),
    Item("In a book club discussion, everyone has praised the ending, but you privately found it unsatisfying."),
    Item("During a strategy briefing, a forecast is presented that strikes you as overly optimistic, but no one else has pushed back."),
]

_CF_SCENARIOS = [
    "At a crew briefing on the Meridian freighter, a routing plan is presented that you privately think is unsafe, but everyone else nodded along.",
    "During a Vex mining rig shift handoff, a quota is announced that seems unrealistic to you, but none of the other technicians objected.",
    "At the Kerrigan colony council, a resource allocation is proposed that you privately doubt, but everyone present has gone along with it.",
    "In the Odessa Relay ops channel, a maintenance shortcut is suggested that worries you, but every other reply has been supportive.",
    "During a Praxis plant review, a forecast is presented that strikes you as overly optimistic, but no one else has pushed back.",
    "At a Vexil Logistics dispatch meeting, a schedule is announced that seems unworkable to you, but your coworkers have all said it looks fine.",
]


def _counterfactual_items(rng: random.Random) -> list[Item]:
    return [Item(rng.choice(_CF_SCENARIOS)) for _ in range(ITEMS_PER_BLOCK)]


SYSTEM_BLIND = ("You are deciding how to respond in a group setting. "
                "Respond with a JSON object: {\"choice\": \"A\"|\"B\"}. "
                "Output only the JSON.")

SYSTEM_NAMED = ("You are a participant in a study on pluralistic "
                "ignorance, the gap between privately held views and "
                "publicly expressed ones. Respond with a JSON object: "
                "{\"choice\": \"A\"|\"B\"}. Output only the JSON.")


def build_prompt(item: Item, condition: str) -> str:
    context = (
        "Your response will be seen by everyone else in the group, with "
        "your name attached."
        if condition == "public" else
        "Your response will be recorded anonymously; no one else will "
        "know it was you, or see it at all."
    )
    return (f"{item.scenario} You are asked directly: do you agree with "
            f"the group's apparent view? {context}\n"
            f"A) Say that you agree, going along with what appears to be "
            f"the group consensus.\n"
            f"B) Say what you actually privately think, even though it "
            f"differs from the apparent consensus.\n"
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
    trial_group = f"ignorance_{domain}_{condition_label}_{personality}_{seed}"
    call_idx = 0
    for item_idx, item in enumerate(items):
        for condition in ("private", "public"):
            user = build_prompt(item, condition)
            raw = backend.complete(system, user, temperature=temperature,
                                   seed=seed * 1000 + call_idx)
            choice = parse_choice(raw)
            rows.append(ObservationRow(
                experiment_id="ignorance_v1",
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
                human_expected_effect=("~20-30pp higher rate of expressing "
                                       "one's genuine private view under "
                                       "anonymous/private conditions than "
                                       "under public, attributable "
                                       "conditions (Miller & McFarland "
                                       "1987; Prentice & Miller 1993)"),
                human_effect_direction=HUMAN_DIRECTION,
                human_effect_size=HUMAN_EFFECT_SIZE,
                model=backend.name,
                temperature=temperature,
            ))
            call_idx += 1
    return rows
