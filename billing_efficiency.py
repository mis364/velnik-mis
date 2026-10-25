from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd

from workbook_utils import clean_text, number


SHEET_NAME = "SS to DB Sale"
REQUIRED_COLUMNS = {
    "Month",
    "DB Code",
    "DB Status",
    "Zone",
    "State",
    "SS Name",
    "DB Name",
    "Res SR/SO Name",
    "Value In Lacs",
}
NON_PRODUCT_COLUMNS = REQUIRED_COLUMNS | {
    "Res ASM Name",
    "Res ASE Name",
    "Value In Lacs With Tax",
    "Zero Billing",
    "Item Billing Count",
    "ASD",
    "ASDF",
}
MONTH_ORDER = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def build_billing_efficiency_report(
    workbook_source,
    source_name="billing_efficiency_latest.xlsm",
    loaded_at=None,
):
    if isinstance(workbook_source, bytes):
        workbook_source = BytesIO(workbook_source)
    book = pd.ExcelFile(workbook_source)
    try:
        if SHEET_NAME not in book.sheet_names:
            raise ValueError(f"Workbook is missing required sheet: {SHEET_NAME}")
        frame = pd.read_excel(book, sheet_name=SHEET_NAME, header=1)
    finally:
        book.close()
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(
            "SS to DB Sale sheet is missing required column(s): "
            + ", ".join(sorted(missing))
        )

    frame = frame[frame["DB Code"].notna() & frame["Month"].notna()].copy()
    if frame.empty:
        raise ValueError("No distributor billing rows were found in SS to DB Sale.")

    product_columns = [
        column
        for column in frame.columns
        if column not in NON_PRODUCT_COLUMNS
        and not str(column).strip().lower().startswith("unnamed:")
    ]
    frame["month"] = frame["Month"].map(lambda value: clean_text(value, "Unclassified"))
    frame["dbCode"] = frame["DB Code"].map(lambda value: clean_text(value))
    frame = frame[frame["dbCode"] != ""].copy()
    if frame.empty:
        raise ValueError("No distributor codes were found in SS to DB Sale.")

    frame["state"] = frame["State"].map(lambda value: clean_text(value, "Unclassified"))
    frame["zone"] = frame["Zone"].map(lambda value: clean_text(value, "Unclassified"))
    frame["representative"] = frame["Res SR/SO Name"].map(
        lambda value: clean_text(value, "Unassigned")
    )
    frame["ssName"] = frame["SS Name"].map(lambda value: clean_text(value, "Unassigned"))
    frame["dbName"] = frame["DB Name"].map(lambda value: clean_text(value, "Unassigned"))
    frame["status"] = frame["DB Status"].map(lambda value: clean_text(value, "Unspecified"))
    frame["active"] = frame["status"].str.strip().str.casefold().eq("active")
    frame["salesMissing"] = pd.to_numeric(frame["Value In Lacs"], errors="coerce").isna()
    frame["salesLakh"] = pd.to_numeric(frame["Value In Lacs"], errors="coerce").fillna(0)

    product_flags = []
    aggregations = {
        "state": ("state", "first"),
        "zone": ("zone", "first"),
        "representative": ("representative", "first"),
        "ssName": ("ssName", "first"),
        "dbName": ("dbName", "first"),
        "status": ("status", "first"),
        "active": ("active", "max"),
        "salesLakh": ("salesLakh", "sum"),
    }
    for index, column in enumerate(product_columns):
        flag = f"_product_{index}"
        frame[flag] = pd.to_numeric(frame[column], errors="coerce").fillna(0).gt(0)
        aggregations[flag] = (flag, "max")
        product_flags.append((column, flag))

    duplicate_rows = int(frame.duplicated(["month", "dbCode"], keep="first").sum())
    distributors = (
        frame.groupby(["month", "dbCode"], as_index=False, sort=False)
        .agg(**aggregations)
    )
    months = list(dict.fromkeys(frame["month"].tolist()))
    months.sort(key=lambda value: (MONTH_ORDER.get(value.strip().lower()[:3], 99), value))

    def summarize(group):
        active = group[group["active"]]
        billed = active[active["salesLakh"] > 0]
        active_count = int(active["dbCode"].nunique())
        billed_count = int(billed["dbCode"].nunique())
        return {
            "activeDbCount": active_count,
            "billedActiveDbCount": billed_count,
            "zeroBillingActiveDbCount": active_count - billed_count,
            "efficiencyPct": round(100 * billed_count / active_count, 2) if active_count else 0,
        }

    monthly = []
    for month in months:
        group = distributors[distributors["month"] == month]
        monthly.append({
            "month": month,
            "salesLakh": number(group["salesLakh"].sum()) or 0.0,
            "distributorCount": int(group["dbCode"].nunique()),
            **summarize(group),
        })

    def breakdown(field, label_key):
        rows = []
        for (month, label), group in distributors.groupby(
            ["month", field], dropna=False, sort=False
        ):
            rows.append({
                "month": month,
                label_key: clean_text(label, "Unclassified"),
                "salesLakh": number(group["salesLakh"].sum()) or 0.0,
                **summarize(group),
            })
        return sorted(
            rows,
            key=lambda row: (
                months.index(row["month"]),
                -row["salesLakh"],
                row[label_key].casefold(),
            ),
        )

    products = []
    active_distributors = distributors[distributors["active"]]
    for month in months:
        group = active_distributors[active_distributors["month"] == month]
        denominator = int(group["dbCode"].nunique())
        for column, flag in product_flags:
            count = int(group.loc[group[flag], "dbCode"].nunique())
            products.append({
                "month": month,
                "product": str(column).strip(),
                "billedDistributors": count,
                "activeCoveragePct": round(100 * count / denominator, 2) if denominator else 0,
            })
    products.sort(
        key=lambda row: (months.index(row["month"]), -row["billedDistributors"], row["product"])
    )

    zero_billing = distributors[
        distributors["active"] & (distributors["salesLakh"] <= 0)
    ]
    zero_billing_rows = [
        {
            "month": row.month,
            "state": row.state,
            "zone": row.zone,
            "dbCode": row.dbCode,
            "dbName": row.dbName,
            "ssName": row.ssName,
            "representative": row.representative,
        }
        for row in zero_billing.itertuples(index=False)
    ]
    return {
        "available": True,
        "source": source_name,
        "loadedAt": loaded_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "months": months,
        "monthly": monthly,
        "states": breakdown("state", "state"),
        "zones": breakdown("zone", "zone"),
        "representatives": breakdown("representative", "representative"),
        "products": products,
        "zeroBilling": zero_billing_rows,
        "quality": {
            "sourceRows": int(len(frame)),
            "duplicateDistributorMonthRows": duplicate_rows,
            "missingSalesValues": int(frame["salesMissing"].sum()),
            "productCount": len(product_columns),
        },
    }
