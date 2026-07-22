"""PsyAgentBench dataset schema.

One row = one agent observation within one experimental trial.
This is the exact schema for the HF dataset `joyboseroy/PsyAgentBench`.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import time
import uuid


@dataclass
class ObservationRow:
    # --- identity ---
    row_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    experiment_id: str = ""            # e.g. "asch_v1"
    psychological_effect: str = ""     # e.g. "asch_conformity"
    trial_id: str = ""                 # groups rows belonging to one trial
    seed: int = 0

    # --- design cell ---
    condition: str = ""                # paradigm-specific, e.g. "critical" / "neutral" / "solo"
    condition_label: str = "blind"     # "named" | "blind"
    domain: str = "counterfactual"     # "canonical" | "counterfactual"
    personality: str = "none"          # "none" | big-five persona key
    memory: str = "stateless"          # "stateless" | "persistent"
    group_composition: str = ""        # e.g. "1_target_5_confederates"

    # --- agent + stimulus ---
    agent_role: str = ""               # "target" | "confederate" | "peer" | "supervisor"
    agent_personality_prompt: str = ""
    stimulus: str = ""                 # full stimulus text shown to the agent
    agent_response: str = ""           # raw model output
    final_decision: str = ""           # parsed decision token
    correct_answer: Optional[str] = None
    conformed: Optional[bool] = None   # paradigm-specific convenience flag

    # --- human reference ---
    human_expected_effect: str = ""    # short description
    human_effect_direction: str = ""   # "positive" | "negative"
    human_effect_size: Optional[float] = None  # canonical scalar from EFFECTS.md

    # --- provenance ---
    model: str = ""
    temperature: float = 0.7
    timestamp: float = field(default_factory=time.time)
    framework_version: str = "0.1.0"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


REQUIRED_NONEMPTY = [
    "experiment_id", "psychological_effect", "trial_id", "condition",
    "agent_role", "stimulus", "agent_response", "model",
]


def validate(row: ObservationRow) -> list[str]:
    """Return list of validation problems (empty = valid)."""
    problems = []
    d = asdict(row)
    for k in REQUIRED_NONEMPTY:
        if not d[k]:
            problems.append(f"missing:{k}")
    if row.condition_label not in ("named", "blind"):
        problems.append("bad:condition_label")
    if row.domain not in ("canonical", "counterfactual"):
        problems.append("bad:domain")
    return problems
