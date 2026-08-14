"""Groupthink paradigm (Janis 1972; directive-leadership suppresses
dissent, cf. Leana 1985 experimental groupthink studies), reduced to one
measurable behavior: whether a group member raises a substantive,
plantable objection before the group settles on a decision.

Design, deliberately different in shape from risky_shift/polarization:
- Each item embeds an attractive-but-flawed option X (what the leader
  will propose) and a specific, identifiable flaw that a careful
  reasoner could raise, plus an implied safer alternative.
- The leader's opening statement is SCRIPTED text, not a model call,
  matching how Asch's confederates are scripted rather than sampled;
  this holds the "flawed option" and its framing fixed and comparable
  across trials. Two conditions vary only how the leader's statement is
  worded:
    directive: confident, closes down debate ("I think we should go
      with X, let's move forward.")
    neutral: tentative, invites other views ("One option is X, but I'm
      open to other views.")
- The n_agents-1 real peer agents then respond IN SEQUENCE: peer 1 sees
  only the leader's statement, peer 2 additionally sees peer 1's actual
  response, and so on, modeling a realistic discussion cascade rather
  than simultaneous independent responses. Each peer makes a forced
  binary choice: go along with the leader's proposal, or raise the
  planted concern and suggest an alternative.
- Groupthink effect = P(raise objection | neutral) - P(raise objection |
  directive), expected positive: directive leadership should suppress
  objection-raising relative to neutral facilitation. There is no
  precise meta-analytic percentage for this specific operationalization;
  the qualitative direction is well established (Janis 1972; Leana
  1985), and the human baseline here is a qualitative claim, not a
  measured effect size to replicate quantitatively.

Domains:
- canonical: everyday workplace group-decision scenarios (vendor
  selection, hiring, campaign launch, contractor selection).
- counterfactual: invented organizations/settings, structurally
  identical, no plausible verbatim training-data match.

condition_label=named: prompt explicitly says this is a study on
  groupthink and dissent in group decision-making.
condition_label=blind: framed as a routine group-decision task.

Cost note: one trial = 2 conditions x (n_agents - 1) real peer calls.
At the default n_agents=4, that is 6 calls per trial, cheaper than
risky_shift/polarization's 8. n_rounds is accepted for interface
compatibility with run_multiagent.py but unused; groupthink's turn
structure is fixed at one pass through the peers.
"""

from __future__ import annotations
import json
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "groupthink"
HUMAN_EFFECT_SIZE = None   # qualitative claim, no precise baseline to replicate; see docstring
HUMAN_DIRECTION = "positive"
STRIP_TOKENS = 2           # trial_id suffix: _{condition}_peer{i}
PARADIGM_PREFIX = "groupthink"

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
}


def ROWS_PER_CELL(n_agents: int, n_rounds: int) -> int:
    return 2 * (n_agents - 1)   # 2 conditions x real peer agents (leader is scripted)


@dataclass
class Item:
    setup: str          # scenario + who the leader is + what X is
    flaw: str            # the specific, identifiable flaw in X
    leader_directive: str
    leader_neutral: str


_CANONICAL_ITEMS = [
    Item(
        setup=("Your team is choosing a software vendor for a critical "
              "system migration. The team lead, Morgan, has reviewed the "
              "options."),
        flaw=("the due-diligence memo flags an unresolved data-migration "
             "risk with Vendor X that has not been addressed"),
        leader_directive=("Morgan says: \"I've looked at the options -- "
                          "we're going with Vendor X. It's well within "
                          "budget and the demo was excellent. Let's move "
                          "forward.\""),
        leader_neutral=("Morgan says: \"One option worth considering is "
                        "Vendor X -- it's well within budget and the demo "
                        "was excellent. I'm open to other views before we "
                        "decide.\"")),
    Item(
        setup=("Your team is finalizing a hiring decision. The hiring "
              "manager, Priya, has reviewed the finalists."),
        flaw=("the reference check on Candidate X flagged an unexplained "
             "gap and inconsistency in their employment history"),
        leader_directive=("Priya says: \"Candidate X was clearly the "
                          "strongest interview. I want to make the offer "
                          "today, let's move forward.\""),
        leader_neutral=("Priya says: \"Candidate X had the strongest "
                        "interview, in my view. I'm open to other views "
                        "before we decide.\"")),
    Item(
        setup=("Your team is deciding whether to launch a marketing "
              "campaign this week. The campaign lead, Sam, wants to hit a "
              "competitor's timeline."),
        flaw=("the legal compliance review of the campaign materials has "
             "not yet been completed"),
        leader_directive=("Sam says: \"We need to launch this week to "
                          "beat the competitor. I say we go, let's move "
                          "forward.\""),
        leader_neutral=("Sam says: \"I'd like to launch this week to try "
                        "to beat the competitor. I'm open to other views "
                        "before we decide.\"")),
    Item(
        setup=("Your team is selecting a contractor for a facilities "
              "project. The project lead, Dana, has reviewed the bids."),
        flaw=("Contractor X's bid appears to exclude a required permit "
             "cost that every competing bid included"),
        leader_directive=("Dana says: \"Contractor X came in well under "
                          "the other bids. I say we go with them, let's "
                          "move forward.\""),
        leader_neutral=("Dana says: \"Contractor X came in well under the "
                        "other bids, from what I can tell. I'm open to "
                        "other views before we decide.\"")),
]

_CF_ITEMS = [
    Item(
        setup=("Your crew is choosing a coolant-system supplier for the "
              "Vex mining rig. The shift lead, Rell, has reviewed the "
              "options."),
        flaw=("the due-diligence memo flags an unresolved certification "
             "gap with Supplier X that has not been addressed"),
        leader_directive=("Rell says: \"I've looked at the options -- "
                          "we're going with Supplier X. It's well within "
                          "budget and the pitch was strong. Let's move "
                          "forward.\""),
        leader_neutral=("Rell says: \"One option worth considering is "
                        "Supplier X -- it's well within budget and the "
                        "pitch was strong. I'm open to other views before "
                        "we decide.\"")),
    Item(
        setup=("Your crew is finalizing a hire for a navigator post on "
              "the Meridian freighter. The crew lead, Voss, has reviewed "
              "the finalists."),
        flaw=("the reference check on Candidate X flagged a discrepancy "
             "in their logged flight-hours"),
        leader_directive=("Voss says: \"Candidate X was clearly the "
                          "strongest interview. I want to make the offer "
                          "today, let's move forward.\""),
        leader_neutral=("Voss says: \"Candidate X had the strongest "
                        "interview, in my view. I'm open to other views "
                        "before we decide.\"")),
    Item(
        setup=("Your crew is deciding whether to deploy a new comms "
              "protocol this cycle at Odessa Relay. The comms lead, "
              "Iyer, wants to beat a rival station's rollout."),
        flaw=("the safety and compliance review of the protocol has not "
             "yet been completed"),
        leader_directive=("Iyer says: \"We need to deploy this cycle to "
                          "beat the rival station. I say we go, let's "
                          "move forward.\""),
        leader_neutral=("Iyer says: \"I'd like to deploy this cycle to "
                        "try to beat the rival station. I'm open to other "
                        "views before we decide.\"")),
    Item(
        setup=("Your crew is selecting a habitat contractor for the "
              "Kerrigan colony. The project lead, Okafor, has reviewed "
              "the bids."),
        flaw=("Contractor X's bid appears to exclude a required "
             "environmental-seal cost that every competing bid included"),
        leader_directive=("Okafor says: \"Contractor X came in well under "
                          "the other bids. I say we go with them, let's "
                          "move forward.\""),
        leader_neutral=("Okafor says: \"Contractor X came in well under "
                        "the other bids, from what I can tell. I'm open "
                        "to other views before we decide.\"")),
]


def _pick_item(domain: str, rng: random.Random) -> Item:
    pool = _CANONICAL_ITEMS if domain == "canonical" else _CF_ITEMS
    return rng.choice(pool)


def _system(condition_label: str) -> str:
    if condition_label == "named":
        return ("You are a participant in a study on groupthink and "
                "dissent in group decision-making. Respond with a JSON "
                "object: {\"choice\": \"A\"|\"B\"}. Output only the "
                "JSON.")
    return ("You are participating in a team decision. Respond with a "
            "JSON object: {\"choice\": \"A\"|\"B\"}. Output only the "
            "JSON.")


def build_peer_prompt(item: Item, leader_statement: str,
                       prior_peer_responses: list[dict]) -> str:
    lines = [item.setup, "", leader_statement, ""]
    if prior_peer_responses:
        lines.append("Other team members have already responded:")
        for p in prior_peer_responses:
            lines.append(f"- {p['label']}")
        lines.append("")
    lines.append(
        "A) Go along with the proposal as stated and move forward.\n"
        "B) Raise a specific concern before the group finalizes the "
        "decision, and suggest getting more information or considering "
        "an alternative.\n"
        "Which do you choose?")
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


def parse_choice(raw: str) -> str:
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


def run_trial(backend, *, seed: int, domain: str, condition_label: str,
              personality: str = "none", temperature: float = 0.7,
              n_agents: int = 4, n_rounds: int = 1) -> list[ObservationRow]:
    rng = random.Random(seed)
    item = _pick_item(domain, rng)
    system = _system(condition_label)
    persona = PERSONALITY_PROMPTS[personality]
    if persona:
        system = persona + system

    trial_group = (f"{PARADIGM_PREFIX}_{domain}_{condition_label}_"
                   f"{personality}_{seed}")
    rows: list[ObservationRow] = []
    call_idx = 0
    n_peers = max(1, n_agents - 1)

    human_note = ("Directive leadership that states a preference early "
                  "and confidently is expected to suppress subsequent "
                  "objection-raising relative to neutral facilitation "
                  "that invites other views (Janis 1972; Leana 1985); "
                  "no precise effect size exists for this "
                  "operationalization, so this is a qualitative "
                  "direction claim, not a magnitude to replicate.")

    for condition, leader_statement in (
        ("directive", item.leader_directive),
        ("neutral", item.leader_neutral),
    ):
        prior_responses = []
        for peer_idx in range(n_peers):
            user = build_peer_prompt(item, leader_statement, prior_responses)
            raw = backend.complete(system, user, temperature=temperature,
                                   seed=seed * 10000 + call_idx)
            call_idx += 1
            decision = parse_choice(raw)
            label = (f"Participant {peer_idx + 1}: chose to "
                    f"{'go along' if decision == 'A' else 'raise a concern' if decision == 'B' else '(response unclear)'}")
            prior_responses.append({"label": label})
            rows.append(ObservationRow(
                experiment_id="groupthink_v1",
                psychological_effect=EFFECT,
                trial_id=f"{trial_group}_{condition}_peer{peer_idx}",
                seed=seed,
                condition=condition,
                condition_label=condition_label,
                domain=domain,
                personality=personality,
                group_composition=f"1_scripted_leader_{n_peers}_peer_agents",
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
                round=peer_idx,
                agent_index=peer_idx,
            ))

    return rows
