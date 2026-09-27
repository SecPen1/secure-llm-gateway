import re

# Sensitive-data patterns to redact from LLM responses before they reach the
# client. Scoped to high-confidence credential/financial identifiers rather
# than general PII (e.g. email addresses) to keep the false-positive rate low
# enough that this stays usable — see README Slice 4.
_PATTERNS: dict[str, re.Pattern[str]] = {
    "credit_card": re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic_api_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
}


def filter_response(text: str) -> tuple[str, list[str]]:
    redacted_categories: list[str] = []
    filtered_text = text

    for category, pattern in _PATTERNS.items():
        if pattern.search(filtered_text):
            redacted_categories.append(category)
            filtered_text = pattern.sub(f"[REDACTED:{category}]", filtered_text)

    return filtered_text, redacted_categories
