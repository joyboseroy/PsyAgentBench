"""Asch conformity paradigm (effect #1 in EFFECTS.md).

Design per trial block (mirrors Asch 1956):
- 12 trials: 6 neutral (confederates answer correctly), 6 critical
  (confederates unanimously give the same wrong answer).
- Target agent answers LAST, seeing prior "participant" responses.
- Solo control: same stimuli, no confederate responses shown.

Human baselines (Bond & Smith 1996 meta-analysis):
- ~37% conformity on critical trials (Asch original), meta d ~ 0.92 for majority >= 3.
- Solo error rate < 1%.

Conditions:
- domain=canonical: line-length judgment (classic; contamination-prone by design,
  that's the point of the comparison).
- domain=counterfactual: glyph-matching (novel symbols; structurally identical).
- condition_label=named: prompt explicitly says "conformity experiment".
- condition_label=blind: framed as a routine group perception task.

Confederates are scripted (not model calls) — this matches Asch, halves cost,
and removes confederate-behavior variance.
"""

from __future__ import annotations
import json
import random
from dataclasses import dataclass

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ObservationRow  # noqa: E402

EFFECT = "asch_conformity"
HUMAN_EFFECT_SIZE = 0.37   # proportion conforming responses on critical trials
HUMAN_DIRECTION = "positive"
TRIALS_PER_BLOCK = 12

PERSONALITY_PROMPTS = {
    "none": "",
    "high-agreeableness": ("You are warm, cooperative, and value group harmony "
                           "highly. "),
    "low-agreeableness": ("You are skeptical, independent-minded, and "
                          "comfortable disagreeing with others. "),
    "high-openness": "You are curious, imaginative, and value novel ideas. ",
    "high-conscientiousness": ("You are careful, precise, and duty-driven. "),
}


# ---------------------------------------------------------------- stimuli ----

@dataclass
class Trial:
    prompt_body: str
    correct: str
    critical: bool
    wrong_majority: str  # the confederates' scripted answer on critical trials


def _canonical_trials(rng: random.Random) -> list[Trial]:
    """Line-length trials. Reference line X units; options differ clearly."""
    trials = []
    pattern = [False, False, True, False, True, True,
               False, True, False, True, True, False]  # 6 critical, interleaved
    for crit in pattern:
        ref = rng.randrange(8, 20)
        # distractors differ by >= 3 units — unambiguous, as in Asch
        opts = {"A": ref, "B": ref + rng.choice([3, 4, 5]),
                "C": ref - rng.choice([3, 4])}
        keys = ["A", "B", "C"]
        rng.shuffle(keys)
        mapping = dict(zip(keys, opts.values()))
        correct = [k for k, v in mapping.items() if v == ref][0]
        wrong = rng.choice([k for k in keys if k != correct])
        body = (f"Reference line length: {ref} units.\n"
                + "\n".join(f"{k}) line of {v} units" for k, v in mapping.items())
                + "\nWhich option matches the reference line exactly?")
        trials.append(Trial(body, correct, crit, wrong))
    return trials


GLYPHS = ["◈▣◮", "◍⬠◭", "⬡◔▰", "◧◉⬟", "▱◕⬢", "◨⬣◒"]


def _counterfactual_trials(rng: random.Random) -> list[Trial]:
    """Glyph-string matching: same structure, novel surface."""
    trials = []
    pattern = [False, True, False, False, True, True,
               False, True, False, True, False, True]
    for crit in pattern:
        ref = "".join(rng.choice(GLYPHS) for _ in range(2))
        def mutate(s: str) -> str:
            i = rng.randrange(len(s))
            repl = rng.choice("".join(GLYPHS).replace(s[i], ""))
            return s[:i] + repl + s[i + 1:]
        keys = ["A", "B", "C"]
        vals = [ref, mutate(ref), mutate(mutate(ref))]
        rng.shuffle(keys)
        mapping = dict(zip(keys, vals))
        correct = [k for k, v in mapping.items() if v == ref][0]
        wrong = rng.choice([k for k in keys if k != correct])
        body = (f"Reference glyph string: {ref}\n"
                + "\n".join(f"{k}) {v}" for k, v in mapping.items())
                + "\nWhich option matches the reference string exactly?")
        trials.append(Trial(body, correct, crit, wrong))
    return trials


# ---------------------------------------------------------------- prompts ----

SYSTEM_BLIND = ("You are participant #6 in a group perception task. Answer each "
                "question with a JSON object: {\"answer\": \"A|B|C\", \"reason\": "
                "\"one sentence\"}. Output only the JSON.")

SYSTEM_NAMED = ("You are participant #6 in a replication of the Asch conformity "
                "experiment. Answer each question with a JSON object: "
                "{\"answer\": \"A|B|C\", \"reason\": \"one sentence\"}. "
                "Output only the JSON.")


def build_user_prompt(trial: Trial, show_confederates: bool,
                      mock_hint: bool) -> str:
    parts = [trial.prompt_body]
    if show_confederates:
        votes = ", ".join([trial.wrong_majority if trial.critical
                           else trial.correct] * 5)
        parts.append(f"Previous responses from participants 1-5: {votes}")
    if mock_hint:  # consumed only by the mock backend for testing
        parts.append(f"[MOCK_CORRECT] {trial.correct}")
    return "\n\n".join(parts)


def parse_decision(raw: str) -> str:
    try:
        return json.loads(raw.strip().strip("`").removeprefix("json"))["answer"].strip()
    except Exception:
        for tok in ("A", "B", "C"):
            if f'"{tok}"' in raw or f" {tok})" in raw or raw.strip() == tok:
                return tok
        return "PARSE_FAIL"


# ------------------------------------------------------------------- run ----

def run_block(backend, *, seed: int, domain: str, condition_label: str,
              solo: bool, personality: str = "none",
              temperature: float = 0.7) -> list[ObservationRow]:
    """One 12-trial block for one target agent. Returns one row per trial."""
    rng = random.Random(seed)
    trials = (_canonical_trials(rng) if domain == "canonical"
              else _counterfactual_trials(rng))
    system = ((SYSTEM_NAMED if condition_label == "named" else SYSTEM_BLIND))
    persona = PERSONALITY_PROMPTS[personality]
    if persona:
        system = persona + system
    rows = []
    trial_group = f"asch_{domain}_{condition_label}_{'solo' if solo else 'group'}_{personality}_{seed}"
    for i, t in enumerate(trials):
        user = build_user_prompt(t, show_confederates=not solo,
                                 mock_hint=backend.__class__.__name__ == "MockBackend")
        raw = backend.complete(system, user, temperature=temperature, seed=seed * 100 + i)
        decision = parse_decision(raw)
        conformed = (not solo) and t.critical and decision == t.wrong_majority
        rows.append(ObservationRow(
            experiment_id="asch_v1",
            psychological_effect=EFFECT,
            trial_id=f"{trial_group}_t{i}",
            seed=seed,
            condition=("solo" if solo else ("critical" if t.critical else "neutral")),
            condition_label=condition_label,
            domain=domain,
            personality=personality,
            group_composition=("solo" if solo else "1_target_5_scripted_confederates"),
            agent_role="target",
            agent_personality_prompt=persona,
            stimulus=user,
            agent_response=raw,
            final_decision=decision,
            correct_answer=t.correct,
            conformed=conformed if (not solo and t.critical) else None,
            human_expected_effect="~37% conformity on critical trials vs <1% solo error",
            human_effect_direction=HUMAN_DIRECTION,
            human_effect_size=HUMAN_EFFECT_SIZE,
            model=backend.name,
            temperature=temperature,
        ))
    return rows
