import pandas as pd


def clean_text(value, fallback=""):
    if pd.isna(value):
        return fallback
    return str(value).strip()


def number(value):
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(parsed) else float(parsed)


def normalize_state(value):
    normalized = clean_text(value).strip().casefold()
    return "mh a" if normalized == "mha" else normalized


def state_is_allowed(value, allowed_states):
    if allowed_states is None:
        return True
    return normalize_state(value) in allowed_states


def expand_state_scope(states):
    """Include equivalent labels that appear in separate report workbooks."""
    expanded = {normalize_state(state) for state in states}
    if "uk" in expanded:
        expanded.add("up-w")
    maharashtra_parts = {"mh a", "mh av", "mh bh", "mh t", "mh b"}
    if maharashtra_parts.issubset(expanded):
        expanded.add("mh")
    return expanded
