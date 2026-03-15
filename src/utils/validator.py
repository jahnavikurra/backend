from typing import Tuple


def validate_notes_text(notes: str) -> Tuple[bool, str]:
    cleaned = (notes or "").strip()

    if not cleaned:
        return False, "Notes cannot be empty."

    if len(cleaned) < 8:
        return False, "Please provide a little more context so a useful work item can be generated."

    if len(cleaned) > 20000:
        return False, "Notes are too long."

    return True, ""
