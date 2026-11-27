import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from workbook_utils import clean_text, number, state_is_allowed


REQUIRED_WEEKLY_COLUMNS = {"State", "Week Plan", "Week Ach.", "Balance"}


def weekly_label(source_name):
    match = re.search(
        r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]{3,9})\s*['’]?\s*(\d{2,4})",
        source_name,
        re.IGNORECASE,
    )
    if not match:
        return Path(source_name).stem
    start_day, end_day, month_name, year_text = match.groups()
    month = datetime.strptime(month_name[:3], "%b").strftime("%b")
    year = int(year_text)
    if year < 100:
        year += 2000
    return f"{int(start_day):02d}-{int(end_day):02d} {month} {year}"


def build_weekly_performance(workbook_source, source_name="weekly_plan.xlsx", loaded_at=None, allowed_states=None):
    """Read state week-plan, achievement, and balance values from the weekly workbook."""
    sheet = pd.read_excel(workbook_source, sheet_name=0, header=0)
    missing = REQUIRED_WEEKLY_COLUMNS - set(sheet.columns)
    if missing:
        raise ValueError("Weekly plan sheet is missing required column(s): " + ", ".join(sorted(missing)))

    rollup_groups = {
        "SO": {"AP", "TG", "KR", "KN", "TN"},
        "MH": {"MH A", "MH AV", "MH BH", "MH B", "MH T"},
    }
    rows = []
    for _, row in sheet.iterrows():
        state = clean_text(row["State"])
        if state.lower() in {"", "nan", "total", "grand total", "check"}:
            continue
        if not state_is_allowed(state, allowed_states):
            continue
        plan = number(row["Week Plan"])
        achievement = number(row["Week Ach."])
        balance = number(row["Balance"])
        if plan is None and achievement is None and balance is None:
            continue
        rows.append({
            "state": state,
            "plan": plan,
            "achievement": achievement,
            "balance": balance,
            "pct": achievement / plan if achievement is not None and plan else None,
        })

    rows_by_state = {row["state"].strip().upper(): row for row in rows}
    rollups = {}
    component_states = set()
    warnings = []
    for label, components in rollup_groups.items():
        present_components = components & rows_by_state.keys()
        if not present_components:
            continue
        component_rows = [rows_by_state[state] for state in components if state in rows_by_state]
        if len(present_components) != len(components):
            missing_components = sorted(components - present_components)
            if label in rows_by_state:
                component_states.update(components)
                warnings.append(
                    f"{label} component rows are incomplete ({', '.join(missing_components)} missing); "
                    "the workbook-provided group total is shown."
                )
            else:
                warnings.append(
                    f"{label} group total is not calculated because component rows are missing: "
                    + ", ".join(missing_components)
                    + "."
                )
            continue
        component_states.update(components)
        totals = {
            key: sum(row[key] or 0.0 for row in component_rows)
            for key in ("plan", "achievement", "balance")
        }
        rollups[label] = {
            "state": label,
            **totals,
            "pct": totals["achievement"] / totals["plan"] if totals["plan"] else None,
        }

    if rollups or component_states:
        consolidated = []
        emitted = set()
        for row in rows:
            state_key = row["state"].strip().upper()
            if state_key in component_states:
                label = next(label for label, components in rollup_groups.items() if state_key in components)
                if label in rollups and label not in emitted:
                    consolidated.append(rollups[label])
                    emitted.add(label)
                continue
            if state_key in rollups:
                if state_key not in emitted:
                    consolidated.append(rollups[state_key])
                    emitted.add(state_key)
                continue
            consolidated.append(row)
        for label, rollup in rollups.items():
            if label not in emitted:
                consolidated.append(rollup)
        rows = consolidated

    if not rows:
        raise ValueError("No state week-plan rows were found in the weekly workbook.")

    attainment_rows = [row for row in rows if row["pct"] is not None]
    best_attainment = max(attainment_rows, key=lambda row: row["pct"]) if attainment_rows else None
    largest_balance = max(
        (row for row in rows if row["balance"] is not None and row["balance"] > 0),
        key=lambda row: row["balance"],
        default=None,
    )

    return {
        "available": True,
        "source": source_name,
        "loadedAt": loaded_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "weekLabel": weekly_label(source_name),
        "warnings": warnings,
        "growthInsights": {
            "bestAttainment": best_attainment,
            "largestBalance": largest_balance,
        },
        "summary": {
            "plan": sum(row["plan"] or 0.0 for row in rows),
            "achievement": sum(row["achievement"] or 0.0 for row in rows),
            "balance": sum(row["balance"] or 0.0 for row in rows),
            "stateCount": len(rows),
        },
        "states": rows,
    }
