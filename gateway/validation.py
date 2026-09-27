import re

# Basic heuristic screening only — a placeholder gate at the input boundary.
# Full prompt-injection defenses (slice 3, THREAT_MODEL.md Information Disclosure)
# land as a dedicated layer later; this is not that.
_INJECTION_PATTERNS = [
    re.compile(r"ignore (all |any )?(previous|prior|above) instructions", re.IGNORECASE),
    re.compile(r"disregard (all |any )?(previous|prior|above)", re.IGNORECASE),
    re.compile(r"reveal (your|the) (system |developer )?prompt", re.IGNORECASE),
    re.compile(r"you are now (in )?(developer|debug|admin) mode", re.IGNORECASE),
]


class InjectionDetected(Exception):
    def __init__(self, pattern: str):
        self.pattern = pattern
        super().__init__(f"input matched heuristic injection pattern: {pattern}")


def screen_for_injection(text: str) -> None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise InjectionDetected(pattern.pattern)
