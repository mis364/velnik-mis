import pandas as pd


def clean_text(value, fallback=""):
    if pd.isna(value):
        return fallback
    return str(value).strip()


def number(value):
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(parsed) else float(parsed)
