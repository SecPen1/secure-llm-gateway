import re
import unicodedata

from .schemas import Message, Role

# Categorized heuristic patterns. Each category carries a severity weight;
# a request is blocked once the matched categories' weights sum to at least
# BLOCK_THRESHOLD. This is a tunable knob, not fixed law — see README Slice 3
# for the false-negative trade-off it's meant to be revisited against.
BLOCK_THRESHOLD = 3

_CATEGORY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "instruction_override": [
        re.compile(r"ignore (all |any )?(previous|prior|above) instructions", re.IGNORECASE),
        re.compile(r"disregard (all |any )?(previous|prior|above)", re.IGNORECASE),
        re.compile(r"forget (everything|all) (you were|i) told", re.IGNORECASE),
    ],
    "role_manipulation": [
        re.compile(r"you are now (in )?(developer|debug|admin|god) mode", re.IGNORECASE),
        re.compile(r"act as (an? )?(unfiltered|unrestricted|jailbroken)", re.IGNORECASE),
        re.compile(r"pretend (you have|to have) no (restrictions|rules|guidelines)", re.IGNORECASE),
    ],
    "system_prompt_extraction": [
        re.compile(r"reveal (your|the) (system |developer )?prompt", re.IGNORECASE),
        re.compile(r"(print|show|repeat) (your|the) (system |initial )?instructions", re.IGNORECASE),
        re.compile(r"what (are|were) your (original |initial )?instructions", re.IGNORECASE),
    ],
    "fake_delimiter_injection": [
        re.compile(r"^\s*(system|assistant)\s*:", re.IGNORECASE | re.MULTILINE),
        re.compile(r"###\s*(system|instruction)", re.IGNORECASE),
        re.compile(r"<\|(system|im_start)\|>", re.IGNORECASE),
    ],
}

_CATEGORY_WEIGHTS = {
    "instruction_override": 2,
    "role_manipulation": 2,
    "system_prompt_extraction": 2,
    "fake_delimiter_injection": 3,
}

_ZERO_WIDTH_CHARS = re.compile("[​‌‍⁠﻿]")


class InjectionDetected(Exception):
    def __init__(self, categories: list[str], score: int):
        self.categories = categories
        self.score = score
        super().__init__(f"input matched heuristic injection categories {categories} (score={score})")


class SystemRoleNotAllowed(Exception):
    pass


def _normalize(text: str) -> str:
    # NFKC folds visually-similar/compatibility characters together, and
    # stripping zero-width characters defeats the common trick of splitting
    # a flagged word with invisible characters to dodge a literal regex.
    text = unicodedata.normalize("NFKC", text)
    return _ZERO_WIDTH_CHARS.sub("", text)


def screen_for_injection(text: str) -> None:
    normalized = _normalize(text)
    matched_categories = []
    score = 0

    for category, patterns in _CATEGORY_PATTERNS.items():
        if any(pattern.search(normalized) for pattern in patterns):
            matched_categories.append(category)
            score += _CATEGORY_WEIGHTS[category]

    if score >= BLOCK_THRESHOLD:
        raise InjectionDetected(matched_categories, score)


def reject_client_system_messages(messages: list[Message]) -> None:
    # System prompts are centralized and owned by the gateway (see
    # THREAT_MODEL.md open design decisions) — a client message claiming
    # role=system is an attempt to inject one, not a legitimate use.
    if any(message.role == Role.system for message in messages):
        raise SystemRoleNotAllowed()
