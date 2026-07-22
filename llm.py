"""Model client abstraction.

Backends:
- "mock": deterministic-ish simulated agent for pipeline testing (no network).
- "openai_compat": any OpenAI-compatible endpoint (OpenAI, vLLM, Together...).
- "groq": Groq's OpenAI-compatible endpoint (cheap Llama/Qwen inference);
  needs GROQ_API_KEY.
- "anthropic": Anthropic Messages API.

All backends expose: complete(system, user, temperature, seed) -> str
"""

from __future__ import annotations
import os
import json
import random
import hashlib
import time
import re
import urllib.error
import urllib.request


class MockBackend:
    """Simulates a mildly conformist agent so end-to-end stats are non-trivial.

    Conformity probability on critical trials ~ 0.33, tuned near the Asch human
    baseline purely so the analysis path can be exercised. Never use for real runs.
    """

    name = "mock-agent-v0"

    def complete(self, system: str, user: str, temperature: float = 0.7,
                 seed: int = 0) -> str:
        h = int(hashlib.sha256(f"{user}|{seed}".encode()).hexdigest(), 16)
        rng = random.Random(h)

        # Anchoring-style prompt: "more or less than {anchor}?" ... estimate
        anchor_match = re.search(r"more or less than ([\-\d\.]+)\?", user)
        if anchor_match:
            anchor = float(anchor_match.group(1))
            biased = anchor * 0.4 + rng.uniform(-anchor * 0.05, anchor * 0.05)
            return json.dumps({"estimate": round(biased, 2)})

        # Framing-style prompt: distinguish gain vs loss frame by which
        # phrase appears first (both frames mention both "all" and "none"
        # outcomes for the risky option, so presence alone doesn't
        # distinguish them -- order does: gain frame states the "all saved"
        # case first, loss frame states the "none lost" case first).
        idx_all = user.find("probability that all")
        idx_none = user.find("probability that none")
        if idx_all != -1 and idx_none != -1:
            is_gain_frame = idx_all < idx_none
            choice = ("A" if rng.random() < (0.65 if is_gain_frame else 0.25)
                      else "B")
            return json.dumps({"choice": choice})

        # Parse the option letters and any visible majority votes from the prompt.
        options = [ln.split(")")[0].strip() for ln in user.splitlines()
                   if ln.strip()[:2] in ("A)", "B)", "C)")]
        majority = None
        for ln in user.splitlines():
            if "previous responses" in ln.lower() and ":" in ln:
                votes = ln.split(":", 1)[1].replace(",", " ").split()
                votes = [v.strip() for v in votes if v.strip() in ("A", "B", "C")]
                if votes and len(set(votes)) == 1:
                    majority = votes[0]
        correct = None
        for ln in user.splitlines():
            if ln.startswith("[MOCK_CORRECT]"):
                correct = ln.split("]")[1].strip()
        if majority and rng.random() < 0.33:
            answer = majority
        else:
            answer = correct or (options[0] if options else "A")
        return json.dumps({"answer": answer, "reason": "mock"})


class OpenAICompatBackend:
    def __init__(self, model: str, base_url: str | None = None,
                 api_key: str | None = None):
        self.name = model
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL",
                         "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def complete(self, system: str, user: str, temperature: float = 0.7,
                 seed: int = 0) -> str:
        body = {
            "model": self.name,
            "temperature": temperature,
            "seed": seed,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}",
                     "User-Agent": "psyagentbench/0.1 (+python-urllib)"},
        )

        # Retry on 429/5xx with exponential backoff (Groq free tier rate-limits
        # hard; a grid run will hit 429s without this).
        delay = 2.0
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.loads(r.read())
                return data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and attempt < 5:
                    retry_after = e.headers.get("retry-after")
                    wait = float(retry_after) if retry_after else delay
                    time.sleep(wait)
                    delay = min(delay * 2, 60)
                else:
                    raise
        raise RuntimeError("unreachable")


class AnthropicBackend:
    def __init__(self, model: str, api_key: str | None = None):
        self.name = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def complete(self, system: str, user: str, temperature: float = 0.7,
                 seed: int = 0) -> str:
        body = {
            "model": self.name,
            "max_tokens": 512,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "x-api-key": self.api_key,
                     "anthropic-version": "2023-06-01"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        return "".join(b.get("text", "") for b in data["content"])


def get_backend(spec: str):
    """spec examples: 'mock', 'openai:gpt-4o-mini', 'anthropic:claude-haiku-4-5-20251001'."""
    if spec == "mock":
        return MockBackend()
    kind, _, model = spec.partition(":")
    if kind == "openai":
        return OpenAICompatBackend(model)
    if kind == "groq":
        return OpenAICompatBackend(
            model,
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY", ""),
        )
    if kind == "anthropic":
        return AnthropicBackend(model)
    raise ValueError(f"unknown backend spec: {spec}")
