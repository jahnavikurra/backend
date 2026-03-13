def validate_notes(notes: str) -> tuple[bool, str]:
    cleaned = (notes or "").strip()

    if not cleaned:
        return False, "Notes cannot be empty."

    if len(cleaned) < 8:
        return False, "Please provide a little more context so I can generate a useful work item."

    return True, ""
