from backend.models.eval import EvalLabel


def confidence_band(confidence: float) -> str:
    if confidence >= 0.80:
        return "High"
    if confidence >= 0.55:
        return "Moderate"
    return "Low"



_LABEL_PREAMBLE = {
    "Compatible": "This item appears safe",
    "Caution": "This item may be a concern",
    "High risk": "This item is likely unsafe",
    "Unclear": "Safety is uncertain for this item",
}


_LABEL_DATA_NOTE = {
    "Compatible": None,
    "Caution": "Review the flagged ingredients before ordering.",
    "High risk": "Avoid this item or confirm ingredients with the restaurant.",
    "Unclear": "Ask restaurant staff for a full ingredient list before ordering.",
}


def generate_short_explanation(
    label: EvalLabel,
    reasons: list[str],
    missing_info: list[str],
    confidence: float,
) -> str:
    """
    Produce a concise, human-readable safety explanation for display in the UI.

    Structure:
        <label preamble>: <primary reason>. <confidence statement>[ <action note>]
    """
    band = confidence_band(confidence)
    preamble = _LABEL_PREAMBLE[label]
    action = _LABEL_DATA_NOTE[label]

    if reasons:
        primary_reason = reasons[0][0].lower() + reasons[0][1:]  
        core = f"{preamble}: {primary_reason}."
    else:
        core = f"{preamble}."

    if missing_info:
        confidence_stmt = f"Confidence is {band.lower()} because {missing_info[0].lower()}."
    else:
        confidence_stmt = f"Confidence is {band.lower()} based on available restaurant data."

    parts = [core, confidence_stmt]
    if action:
        parts.append(action)

    return " ".join(parts)
