import re

_STREET_RE = re.compile(
    r"\bonto\s+(.+)$|\bon\s+(.+)$|\btoward\s+(.+)$", re.IGNORECASE
)

def extract_street_hint(instruction: str) -> str:
    """
    Best-effort street name hint from the human-readable instruction.
    Example: "Turn left onto Swanston St" -> "Swanston St"
    """
    m = _STREET_RE.search(instruction.strip())
    if not m:
        return instruction.strip()
    # pick first non-empty group
    for g in m.groups():
        if g:
            return g.strip()
    return instruction.strip()