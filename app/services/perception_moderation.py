import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ModerationAssessment:
    status: str
    risk_level: str
    flags: list[str]


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{8,}\d)(?!\w)")
_WORD_RE = re.compile(r"\b[\w'’-]+\b", re.UNICODE)


def assess_perception(body: str) -> ModerationAssessment:
    """Conservative intake guardrail.

    This intentionally flags observable spam/privacy-risk patterns only. It does
    not infer whether a viewpoint is true, false, offensive, political, or
    valuable. Human review remains authoritative for substantive decisions.
    """
    text = " ".join(body.split())
    lowered = text.casefold()
    words = _WORD_RE.findall(lowered)
    flags: list[str] = []

    urls = _URL_RE.findall(text)
    if len(urls) >= 3 or (urls and len(urls) >= max(2, len(words) // 12)):
        flags.append("link_heavy")

    if _EMAIL_RE.search(text) or _PHONE_RE.search(text):
        flags.append("contact_information")

    if len(words) >= 8:
        counts: dict[str, int] = {}
        for word in words:
            counts[word] = counts.get(word, 0) + 1
        if max(counts.values(), default=0) >= max(5, len(words) // 2):
            flags.append("repetitive_content")

    if len(text) >= 40:
        alpha = [char for char in text if char.isalpha()]
        if alpha and sum(char.isupper() for char in alpha) / len(alpha) >= 0.9:
            flags.append("excessive_caps")

    if len(text) >= 80 and len(set(text.replace(" ", ""))) <= 5:
        flags.append("low_variation")

    # A single flag is not enough to hold a perception. Two independent signals
    # create a review task; this keeps ordinary short opinions from being
    # silently treated as suspicious.
    if len(flags) >= 2:
        return ModerationAssessment("pending_review", "medium", flags)
    return ModerationAssessment("published", "none", flags)
