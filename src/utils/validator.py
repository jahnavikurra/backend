def validate_notes_text(notes: str) -> tuple[bool, str]:
    if notes is None:
        return False, "Notes are required."

    cleaned = notes.strip()
    if not cleaned:
        return False, "Notes cannot be empty."

    if len(cleaned) < 5:
        return False, "Notes must be at least 5 characters long."

    if len(cleaned) > 15000:
        return False, "Notes are too long. Please keep them under 15000 characters."

    return True, ""
