from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import mimetypes
import os
import re
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    import pandas as pd  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: install it with `python -m pip install pandas openpyxl`."
    ) from exc

from weekly import build_weekly_performance
from workbook_utils import clean_text, number


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
WORKBOOK_PATH = DATA_DIR / "latest.xlsx"
META_PATH = DATA_DIR / "source.json"
NEPAL_MANUAL_PATH = DATA_DIR / "nepal_manual.json"
STOCK_WORKBOOK_PATH = DATA_DIR / "stock_latest.xlsx"
STOCK_META_PATH = DATA_DIR / "stock_source.json"
WEEKLY_WORKBOOK_PATH = DATA_DIR / "weekly_plan.xlsx"
WEEKLY_META_PATH = DATA_DIR / "weekly_source.json"
LAST_YEAR_WORKBOOK_PATH = DATA_DIR / "last_year_sales.xlsx"
LAST_YEAR_META_PATH = DATA_DIR / "last_year_source.json"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_BACKUP_BYTES = 250 * 1024 * 1024
BACKUP_FILE_NAMES = (
    "latest.xlsx",
    "source.json",
    "nepal_manual.json",
    "stock_latest.xlsx",
    "stock_source.json",
    "weekly_plan.xlsx",
    "weekly_source.json",
    "last_year_sales.xlsx",
    "last_year_source.json",
)
SESSION_COOKIE_NAME = "sales_mis_session"
SESSION_TTL_SECONDS = 12 * 60 * 60
SESSION_SIGNING_KEY = os.urandom(32)
REQUIRED_SHEETS = {"Raw", "SS to DB Sale"}
REQUIRED_STOCK_SHEETS = {"Stock", "Item Stock CS & SS Stock", "State wise Stock"}
POPULATION_PROJECTIONS_2026 = {
    "MP": 89_965_000,
    "CG": 31_311_000,
    "NESSA": 53_739_000,
    "OD": 47_221_000,
    "WB": 100_631_000,
    "JK": 41_108_000,
    "BH": 132_850_000,
    "UP": 243_466_000,
    "UK": 12_028_000,
    "DL": 22_674_000,
    "HR": 31_409_000,
    "PB": 31_370_000,
    "JN": 13_927_000,
    "RJ": 83_879_000,
    "GJ": 74_343_000,
    "SO": 275_300_000,
    "MH": 129_584_000,
}
POPULATION_REGION_MEMBERS = {
    "MP": {"members": ["MP"], "fallbackMembers": []},
    "CG": {"members": ["CG"], "fallbackMembers": []},
    "NESSA": {"members": ["Nessa"], "fallbackMembers": []},
    "OD": {"members": ["OD"], "fallbackMembers": []},
    "WB": {"members": ["WB"], "fallbackMembers": []},
    "JK": {"members": ["JK"], "fallbackMembers": []},
    "BH": {"members": ["BH"], "fallbackMembers": []},
    "UP": {"members": ["UP"], "fallbackMembers": []},
    "UK": {"members": ["UK"], "fallbackMembers": []},
    "DL": {"members": ["DL"], "fallbackMembers": []},
    "HR": {"members": ["HR"], "fallbackMembers": []},
    "PB": {"members": ["PB"], "fallbackMembers": []},
    "JN": {"members": ["JN"], "fallbackMembers": []},
    "RJ": {"members": ["RJ"], "fallbackMembers": []},
    "GJ": {"members": ["GJ"], "fallbackMembers": []},
    "SO": {"members": ["AP", "TG", "KR", "KN", "TN"], "fallbackMembers": ["SO"]},
    "MH": {"members": ["MH A", "MH AV", "MH BH", "MH B", "MH T"], "fallbackMembers": ["MH"]},
}
POPULATION_SOURCE = "MoHFW / National Commission on Population, Population Projections for India and States 2011–2036 (2020), projected population as of 1 July 2026"
POPULATION_SOURCE_URL = "https://nhm.gov.in/New_Updates_2018/Report_Population_Projection_2019.pdf"
_CACHE_LOCK = threading.Lock()
_CACHE = {"mtime": None, "payload": None}
_STOCK_CACHE = {"mtime": None, "payload": None}
_WEEKLY_CACHE = {"mtime": None, "payload": None}
_LAST_YEAR_CACHE = {"mtime": None, "payload": None}


def build_analysis_context(scope, start_date=None, end_date=None):
    context = {}
    if scope in {"both", "sales"}:
        report = get_report()
        period = report["period"]
        start = max(start_date or period["start"], period["start"])
        end = min(end_date or period["end"], period["end"])
        if start > end:
            raise ValueError("The selected dates do not overlap the sales report period.")

        def selected_totals(rows):
            totals = {}
            for row in rows:
                if start <= row["date"] <= end:
                    totals[row["label"]] = totals.get(row["label"], 0.0) + (row["value"] or 0.0)
            return [
                {"name": name, "salesLakh": value}
                for name, value in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
            ]

        daily = [row for row in report["daily"] if start <= row["date"] <= end]
        comparison = build_period_comparison(report["history"], start, end)
        weekly = get_weekly_performance()
        context["sales"] = {
            "period": {"start": start, "end": end},
            "comparison": comparison,
            "sourcePeriod": period,
            "daily": daily,
            "stateSales": selected_totals(report["stateByDay"]),
            "productSales": selected_totals(report["productByDay"])[:40],
            "monthlyPlanProgress": report["statePlan"],
            "quality": {
                "salesLines": report["quality"]["salesLines"],
                "missingNet": report["quality"]["missingNet"],
                "missingTariff": report["quality"]["missingTariff"],
                "duplicateRows": report["quality"]["duplicateRows"],
                "activeZeroBilling": report["quality"]["activeZeroBilling"],
            },
            "zeroBillingByState": sorted(
                report["zeroByState"].items(),
                key=lambda item: (-item[1], item[0]),
            )[:5],
            "weeklyPerformance": (
                {
                    "weekLabel": weekly.get("weekLabel"),
                    "summary": weekly.get("summary"),
                    "states": weekly.get("states", []),
                    "warnings": weekly.get("warnings", []),
                }
                if weekly.get("available")
                else None
            ),
        }
    if scope in {"both", "stock"}:
        stock = get_stock_report()
        context["stock"] = None if stock is None else {
            "reportDate": stock["reportDate"],
            "summary": stock["summary"],
            "products": stock["products"][:40],
            "states": stock["states"],
        }
    return context


def build_period_comparison(history, start, end):
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()
    period_days = (end_date - start_date).days + 1
    previous_end = start_date.fromordinal(start_date.toordinal() - 1)
    previous_start = previous_end.fromordinal(previous_end.toordinal() - period_days + 1)
    previous_from = previous_start.isoformat()
    previous_to = previous_end.isoformat()
    available = history["start"] <= previous_from and history["end"] >= previous_to
    result = {
        "available": available,
        "currentPeriod": {"start": start, "end": end},
        "previousPeriod": {"start": previous_from, "end": previous_to},
    }
    if not available:
        return result

    def totals(rows, begin, finish):
        output = {}
        for row in rows:
            if begin <= row["date"] <= finish:
                key = row["label"].strip().casefold()
                if key not in output:
                    output[key] = {"name": row["label"], "value": 0.0}
                output[key]["value"] += row["value"] or 0.0
        return output

    def range_total(rows, begin, finish):
        return sum(
            row.get("net") or 0
            for row in rows
            if begin <= row["date"] <= finish
        )

    current_total = range_total(history["daily"], start, end)
    previous_total = range_total(history["daily"], previous_from, previous_to)
    current_states = totals(history["stateByDay"], start, end)
    previous_states = totals(history["stateByDay"], previous_from, previous_to)
    states = []
    for key in current_states.keys() | previous_states.keys():
        label = (current_states.get(key) or previous_states[key])["name"]
        current = current_states.get(key, {}).get("value", 0.0)
        previous = previous_states.get(key, {}).get("value", 0.0)
        states.append({
            "state": label,
            "currentSales": current,
            "previousSales": previous,
            "change": current - previous,
            "changePct": (current - previous) / abs(previous) * 100 if previous else None,
        })
    states.sort(key=lambda row: (-abs(row["change"]), row["state"]))
    result.update({
        "currentSales": current_total,
        "previousSales": previous_total,
        "change": current_total - previous_total,
        "changePct": (current_total - previous_total) / abs(previous_total) * 100 if previous_total else None,
        "states": states,
    })
    return result


def build_local_analysis(question, context, language="en"):
    """Generate data-grounded sales and inventory observations without external services."""
    query = question.casefold()
    sections = []
    sales = context.get("sales")
    stock = context.get("stock")
    is_hindi = language == "hi"

    def amount(value):
        return f"{value:,.2f} {'लाख' if is_hindi else 'lakh'}"

    def stock_amount(value):
        unit = "वर्कबुक इकाई" if is_hindi else "workbook units"
        return f"{value:,.2f} {unit}"

    wants_sales = any(word in query for word in ("sales", "revenue", "billing", "बिक्री", "बिलिंग", "विक्रय"))
    wants_plan = any(word in query for word in ("plan", "gap", "target", "achievement", "attainment", "योजना", "लक्ष्य", "अंतर", "उपलब्धि"))
    wants_trend = any(word in query for word in ("trend", "daily", "day", "date", "increase", "decrease", "रुझान", "दैनिक", "दिन", "तारीख", "बढ़ोतरी", "कमी"))
    wants_state = any(word in query for word in ("state", "region", "where", "territory", "राज्य", "क्षेत्र", "कहाँ", "कहां"))
    wants_product = any(word in query for word in ("product", "item", "sku", "sell", "उत्पाद", "वस्तु", "बेच"))
    wants_stock = any(word in query for word in ("stock", "inventory", "negative", "overstock", "स्टॉक", "भंडार", "नकारात्मक"))
    wants_quality = any(word in query for word in ("quality", "missing", "duplicate", "data", "गुणवत्ता", "लापता", "डुप्लिकेट", "डेटा"))
    wants_compare = any(word in query for word in ("compare", "comparison", "versus", " vs ", "तुलना", "मुकाबला"))
    wants_period_compare = any(word in query for word in ("previous", "prior", "last period", "period comparison", "पिछली अवधि", "पिछले", "तुलना"))
    wants_stock_billing = (
        wants_stock
        and wants_sales
        and any(word in query for word in ("low", "below", "under", "weak", "sell", "opportunity", "mismatch", "but", "कम", "नीचे", "कमजोर", "बिक्री", "अवसर", "लेकिन", "जबकि"))
    )
    specific = wants_plan or wants_trend or wants_state or wants_product or wants_stock or wants_quality or wants_compare or wants_period_compare

    if sales and (not specific or wants_trend or (wants_sales and not wants_period_compare)):
        daily = sales["daily"]
        if daily:
            sales_total = sum(row.get("net") or 0 for row in daily)
            average = sales_total / len(daily)
            if is_hindi:
                sections.append(
                    f"बिक्री ({sales['period']['start']} से {sales['period']['end']}): "
                    f"दिनांकित Raw लेन-देन से {amount(sales_total)}, कुल {len(daily)} दिनों में "
                    f"(औसतन {amount(average)} प्रति दिन)।"
                )
            else:
                sections.append(
                    f"Sales ({sales['period']['start']} to {sales['period']['end']}): "
                    f"{amount(sales_total)} from dated Raw transactions across {len(daily)} days "
                    f"(average {amount(average)} per day)."
                )
            busiest = max(daily, key=lambda row: row.get("net") or 0)
            slowest = min(daily, key=lambda row: row.get("net") or 0)
            if len(daily) > 1:
                if is_hindi:
                    sections.append(
                        f"सबसे अधिक बिक्री वाला दिन: {busiest['date']} को {amount(busiest.get('net') or 0)}; "
                        f"सबसे कम बिक्री वाला दिन: {slowest['date']} को {amount(slowest.get('net') or 0)}। "
                        "इन तारीखों पर कवरेज, ऑर्डर के समय या स्रोत डेटा की जाँच करें।"
                    )
                else:
                    sections.append(
                        f"Highest day: {busiest['date']} at {amount(busiest.get('net') or 0)}; "
                        f"lowest day: {slowest['date']} at {amount(slowest.get('net') or 0)}. "
                        "Check these dates for coverage, order timing, or source-data differences."
                    )

    if sales and wants_period_compare:
        comparison = sales.get("comparison", {})
        if comparison.get("available"):
            pct = comparison.get("changePct")
            if is_hindi:
                change_text = (
                    f"{abs(pct):.1f}% {'बढ़ोतरी' if pct >= 0 else 'कमी'}"
                    if pct is not None else "पिछली अवधि में आधार बिलिंग शून्य थी"
                )
                sections.append(
                    f"अवधि तुलना: {comparison['previousPeriod']['start']} से "
                    f"{comparison['previousPeriod']['end']} में {amount(comparison['previousSales'])}; "
                    f"{comparison['currentPeriod']['start']} से {comparison['currentPeriod']['end']} में "
                    f"{amount(comparison['currentSales'])} ({change_text})। "
                    "राज्यवार सबसे बड़े बदलाव: "
                    + "; ".join(
                        f"{row['state']} ({amount(row['change'])})"
                        for row in comparison.get("states", [])[:3]
                    )
                    + "।"
                )
            else:
                change_text = (
                    f"{abs(pct):.1f}% {'increase' if pct >= 0 else 'decrease'}"
                    if pct is not None else "prior-period baseline billing was zero"
                )
                sections.append(
                    f"Equal-length period comparison: {comparison['previousPeriod']['start']} to "
                    f"{comparison['previousPeriod']['end']} had {amount(comparison['previousSales'])}; "
                    f"{comparison['currentPeriod']['start']} to {comparison['currentPeriod']['end']} had "
                    f"{amount(comparison['currentSales'])} ({change_text}). Largest state changes: "
                    + "; ".join(
                        f"{row['state']} ({amount(row['change'])})"
                        for row in comparison.get("states", [])[:3]
                    )
                    + "."
                )
        else:
            sections.append(
                "पिछली समान अवधि का डेटा वर्कबुक में पूरा उपलब्ध नहीं है।"
                if is_hindi else
                "The workbook does not contain complete data for the preceding equal-length period."
            )

    if sales and (not specific or wants_state):
        states = sales.get("stateSales", [])
        if states:
            leaders = ", ".join(
                f"{row['name']} ({amount(row['salesLakh'])})" for row in states[:3]
            )
            sections.append(
                f"चुनी अवधि में बिक्री के अनुसार अग्रणी राज्य/क्षेत्र: {leaders}।"
                if is_hindi else f"Leading states/regions by selected-period sales: {leaders}."
            )

    if sales and (not specific or wants_product):
        products = sales.get("productSales", [])
        if products:
            leaders = ", ".join(
                f"{row['name']} ({amount(row['salesLakh'])})" for row in products[:3]
            )
            sections.append(
                f"चुनी अवधि में बिक्री के अनुसार अग्रणी उत्पाद: {leaders}।"
                if is_hindi else f"Leading products by selected-period sales: {leaders}."
            )

    if sales and (not specific or wants_plan):
        plans = sales.get("monthlyPlanProgress", [])
        below_plan = [
            row for row in plans
            if row.get("plan") and row.get("achievement") is not None and row["achievement"] < row["plan"]
        ]
        below_plan.sort(key=lambda row: (-row.get("gap", 0), row["state"]))
        if below_plan:
            if is_hindi:
                sections.append(
                    "सबसे बड़े योजना अंतर (योजना की अवधि चुनी गई बिक्री तारीखों से अलग हो सकती है): "
                    + "; ".join(
                        f"{row['state']}: {amount(row['gap'])} का अंतर, "
                        f"{row['pct'] * 100:.1f}% उपलब्धि"
                        for row in below_plan[:3]
                    )
                    + "। इन क्षेत्रों में कवरेज और लंबित ऑर्डर की समीक्षा को प्राथमिकता दें।"
                )
            else:
                sections.append(
                    "Largest plan gaps (plan period may differ from selected sales dates): "
                    + "; ".join(
                        f"{row['state']}: {amount(row['gap'])} gap, "
                        f"{row['pct'] * 100:.1f}% achieved"
                        for row in below_plan[:3]
                    )
                    + ". Prioritize a review of coverage and open orders in these regions."
                )
        elif plans:
            sections.append(
                "उपलब्ध योजना डेटा में लक्ष्य से पीछे कोई राज्य/क्षेत्र नहीं मिला।"
                if is_hindi else "No below-plan state/region was identified in the available plan rows."
            )
        else:
            sections.append(
                "योजना प्रगति का डेटा उपलब्ध नहीं है।"
                if is_hindi else "No plan progress data is available."
            )

    if sales and (not specific or wants_stock) and sales.get("weeklyPerformance"):
        weekly = sales["weeklyPerformance"]
        summary = weekly.get("summary") or {}
        sections.append(
            (
                f"साप्ताहिक योजना ({weekly.get('weekLabel') or 'लोड किया गया सप्ताह'}): "
                f"{amount(summary.get('plan') or 0)} में से "
                f"{amount(summary.get('achievement') or 0)} की उपलब्धि।"
            )
            if is_hindi else
            (
                f"Weekly plan ({weekly.get('weekLabel') or 'loaded week'}): "
                f"{amount(summary.get('achievement') or 0)} achieved of "
                f"{amount(summary.get('plan') or 0)} planned."
            )
        )

    if sales and wants_quality:
        quality = sales["quality"]
        sections.append(
            (
                f"डेटा जाँच: {quality['missingNet']} नेट मान गायब, "
                f"{quality['missingTariff']} टैरिफ गायब, "
                f"{quality['duplicateRows']} संभावित डुप्लिकेट पंक्तियाँ, और "
                f"{quality['activeZeroBilling']} सक्रिय वितरक जिनकी बिलिंग शून्य है।"
            )
            if is_hindi else
            (
                f"Data checks: {quality['missingNet']} missing net values, "
                f"{quality['missingTariff']} missing tariffs, "
                f"{quality['duplicateRows']} possible duplicate rows, and "
                f"{quality['activeZeroBilling']} active zero-billing distributors."
            )
        )
        if sales.get("zeroBillingByState"):
            sections.append(
                (
                    "शून्य-बिलिंग फॉलो-अप की अधिक संख्या वाले राज्य/क्षेत्र: "
                    if is_hindi else "Most zero-billing follow-ups by state/region: "
                )
                + ", ".join(f"{state} ({count})" for state, count in sales["zeroBillingByState"][:3])
                + ("।" if is_hindi else ".")
            )

    if stock and (not specific or wants_stock):
        summary = stock["summary"]
        products = stock.get("products", [])
        states = stock.get("states", [])
        negative = [row for row in products if row.get("negative", 0) < 0]
        sections.append(
            (
                f"{stock.get('reportDate') or 'वर्कबुक की तारीख'} तक स्टॉक: "
                f"कुल {stock_amount(summary.get('totalStock') or 0)} "
                f"(CS {stock_amount(summary.get('csStock') or 0)}, "
                f"SS {stock_amount(summary.get('ssStock') or 0)}); "
                f"{summary.get('negativeProductCount', 0)} उत्पादों का स्टॉक ऋणात्मक है।"
            )
            if is_hindi else
            (
                f"Stock as of {stock.get('reportDate') or 'the workbook date'}: "
                f"{stock_amount(summary.get('totalStock') or 0)} total "
                f"({stock_amount(summary.get('csStock') or 0)} CS, "
                f"{stock_amount(summary.get('ssStock') or 0)} SS); "
                f"{summary.get('negativeProductCount', 0)} products have negative balances."
            )
        )
        if negative:
            sections.append(
                (
                    "सबसे अधिक ऋणात्मक स्टॉक वाले उत्पाद: "
                    if is_hindi else "Largest negative product balances: "
                )
                + ", ".join(
                    f"{row['item']} ({stock_amount(row['negative'])})" for row in sorted(
                        negative, key=lambda row: row["negative"]
                    )[:3]
                )
                + (
                    "। नया स्टॉक भेजने से पहले स्रोत वर्कबुक से मिलान करें।"
                    if is_hindi else ". Reconcile these with the source workbook before replenishing."
                )
            )
        if products:
            leaders = ", ".join(f"{row['item']} ({stock_amount(row['total'])})" for row in products[:3])
            sections.append(
                f"सबसे अधिक उत्पाद स्टॉक: {leaders}।"
                if is_hindi else f"Highest product balances: {leaders}."
            )
        if states:
            leaders = ", ".join(f"{row['state']} ({stock_amount(row['total'])})" for row in states[:3])
            sections.append(
                f"सबसे अधिक राज्य/क्षेत्र स्टॉक: {leaders}।"
                if is_hindi else f"Highest state/region balances: {leaders}."
            )

    if sales and stock and wants_stock_billing:
        sales_by_state = {
            row["name"].strip().casefold(): row
            for row in sales.get("stateSales", [])
        }
        stock_by_state = {
            row["state"].strip().casefold(): row
            for row in stock.get("states", [])
        }
        shared_states = sales_by_state.keys() & stock_by_state.keys()
        comparable = [
            (sales_by_state[state], stock_by_state[state])
            for state in shared_states
        ]
        if len(comparable) < 2:
            sections.append(
                (
                    "राज्य स्टॉक-बनाम-बिलिंग विश्लेषण के लिए दोनों रिपोर्टों में कम-से-कम दो समान राज्य/क्षेत्र चाहिए। "
                    "राज्य नाम जाँचें और दोनों वर्कबुक अपलोड करें।"
                    if is_hindi else
                    "State stock-versus-billing analysis needs at least two matching states/regions in both reports; "
                    "check state labels and upload both workbooks."
                )
            )
        else:
            def median(values):
                ordered = sorted(values)
                middle = len(ordered) // 2
                if len(ordered) % 2:
                    return ordered[middle]
                return (ordered[middle - 1] + ordered[middle]) / 2

            stock_median = median([inventory["total"] for _, inventory in comparable])
            billing_median = median([billing["salesLakh"] for billing, _ in comparable])
            opportunities = [
                (billing, inventory)
                for billing, inventory in comparable
                if inventory["total"] > stock_median and billing["salesLakh"] < billing_median
            ]
            opportunities.sort(key=lambda pair: (-pair[1]["total"], pair[0]["salesLakh"], pair[0]["name"]))
            if opportunities:
                findings = "; ".join(
                    f"{billing['name']}: {stock_amount(inventory['total'])} स्टॉक, "
                    f"{amount(billing['salesLakh'])} बिलिंग"
                    if is_hindi else
                    f"{billing['name']}: {stock_amount(inventory['total'])} stock, "
                    f"{amount(billing['salesLakh'])} billing"
                    for billing, inventory in opportunities[:5]
                )
                if is_hindi:
                    sections.append(
                        f"अधिक स्टॉक लेकिन कम बिलिंग वाले राज्य/क्षेत्र की समीक्षा करें "
                        f"({len(comparable)} समान राज्यों में औसत से अधिक स्टॉक और औसत से कम बिलिंग): "
                        f"{findings}। स्टॉक की तारीख {stock.get('reportDate') or 'वर्कबुक की तारीख'} है; "
                        f"बिलिंग अवधि {sales['period']['start']} से {sales['period']['end']} है। "
                        "ये सापेक्ष रैंकिंग हैं, सीधा स्टॉक-बिक्री अनुपात नहीं, क्योंकि वर्कबुक स्टॉक इकाइयाँ "
                        "और बिक्री लाख में हैं। निर्णय से पहले वितरक के पास उपलब्धता, ऑर्डर रूपांतरण, "
                        "हाल की मांग और डिस्पैच बाधाओं की जाँच करें।"
                    )
                else:
                    sections.append(
                        "States/regions to review for available stock but lower billing "
                        f"(above-median stock and below-median billing across {len(comparable)} matched states): "
                        f"{findings}. Stock is as of {stock.get('reportDate') or 'the stock workbook date'}; "
                        f"billing covers {sales['period']['start']} to {sales['period']['end']}. "
                        "These are relative rankings, not a direct stock-to-sales ratio because workbook stock "
                        "units and sales lakh differ. Review distributor availability, order conversion, "
                        "recent demand, and dispatch constraints before deciding action."
                    )
            else:
                sections.append(
                    (
                        f"{len(comparable)} समान राज्यों/क्षेत्रों में किसी का स्टॉक औसत से अधिक और बिलिंग औसत से कम "
                        "दोनों नहीं है। तुलना सापेक्ष औसत पर आधारित है, सीधे स्टॉक-बिक्री अनुपात पर नहीं।"
                        if is_hindi else
                        "No state/region has both above-median stock and below-median billing among the "
                        f"{len(comparable)} matched states/regions. The comparison uses relative medians, "
                        "not a direct stock-to-sales ratio."
                    )
                )

    if sales and stock and wants_compare:
        sales_by_product = {
            row["name"].casefold(): row
            for row in sales.get("productSales", [])
        }
        stock_by_product = {
            row["item"].casefold(): row
            for row in stock.get("products", [])
        }
        shared = [
            (sales_by_product[name], stock_by_product[name])
            for name in sales_by_product.keys() & stock_by_product.keys()
        ]
        shared.sort(key=lambda pair: (-pair[0]["salesLakh"], pair[0]["name"]))
        if shared:
            shared_text = "; ".join(
                    f"{sale['name']}: {amount(sale['salesLakh'])} sales, "
                    f"{stock_amount(item['total'])} stock"
                    for sale, item in shared[:3]
                )
            sections.append(
                (
                    "दोनों रिपोर्टों में मौजूद उत्पाद (बिक्री चुनी तारीखों की; स्टॉक "
                    f"{stock.get('reportDate') or 'वर्कबुक की तारीख'} तक): {shared_text}। "
                    "यह केवल स्नैपशॉट तुलना है, बिक्री-निकासी या स्टॉक-कवरेज दिनों की गणना नहीं।"
                    if is_hindi else
                    "Products appearing in both reports (sales for the selected dates; stock as of "
                    f"{stock.get('reportDate') or 'the workbook date'}): {shared_text}. "
                    "This is a snapshot comparison, not a sell-through or days-of-cover calculation."
                )
            )
        else:
            sections.append(
                (
                    "दोनों रिपोर्टों में समान उत्पाद नाम नहीं मिले, इसलिए उत्पाद-स्तर की तुलना उपलब्ध नहीं है।"
                    if is_hindi else
                    "No matching product names were found in both reports, so a product-level comparison "
                    "is not available."
                )
            )

    if not sections:
        if sales is None and stock is None:
            return (
                "इस विश्लेषण के लिए बिक्री या स्टॉक रिपोर्ट उपलब्ध नहीं है। वर्कबुक अपलोड करके फिर प्रयास करें।"
                if is_hindi else
                "No sales or stock report is available for this analysis. Upload a workbook, then try again."
            )
        return (
            "इस प्रश्न के लिए स्थानीय रिपोर्ट विश्लेषण नहीं मिला। बिक्री रुझान, राज्य या उत्पाद रैंकिंग, "
            "योजना अंतर, स्टॉक बैलेंस, ऋणात्मक स्टॉक या डेटा जाँच के बारे में पूछें।"
            if is_hindi else
            "I couldn’t match that question to a local report analysis. Try asking about sales trends, "
            "state or product rankings, plan gaps, stock balances, negative stock, or data checks."
        )
    return "\n\n".join(sections)


def replace_workbook(contents, destination):
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".uploading",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(contents)
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            temporary_path.replace(destination)
        except PermissionError as exc:
            raise PermissionError(
                f"Windows denied access while replacing {destination.name}. "
                "Close the workbook in Excel or any other app, check that the data folder is writable, and retry."
            ) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def get_column(columns, predicate):
    for column in columns:
        if predicate(str(column).replace("\n", " ").strip().lower()):
            return column
    return None


def find_plan_columns(frame):
    columns = list(frame.columns)
    state_col = get_column(columns, lambda x: x == "state")
    plan_col = get_column(columns, lambda x: x.startswith("billing plan"))
    ach_col = get_column(
        columns,
        lambda x: "ach." in x and "today" not in x and "plan" not in x,
    )
    return state_col, plan_col, ach_col


def build_report(workbook_source, source_name="latest.xlsx", loaded_at=None, manual_nepal_override=None):
    """Read source sheets and return a JSON-safe, month-to-date report."""
    book = pd.ExcelFile(workbook_source)
    missing = REQUIRED_SHEETS - set(book.sheet_names)
    if missing:
        raise ValueError("Workbook is missing required sheet(s): " + ", ".join(sorted(missing)))

    raw = pd.read_excel(book, sheet_name="Raw", header=1)
    required_raw = {"Voucher Number", "Date", "Without GST", "In Lacs", "State", "Item Group2"}
    missing_columns = required_raw - set(raw.columns)
    if missing_columns:
        raise ValueError("Raw sheet is missing required column(s): " + ", ".join(sorted(missing_columns)))

    raw = raw[raw["Voucher Number"].notna()].copy()
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    raw = raw[raw["Date"].notna()].copy()
    if raw.empty:
        raise ValueError("No dated sales lines were found in the Raw sheet.")

    raw["Without GST"] = pd.to_numeric(raw["Without GST"], errors="coerce")
    raw["In Lacs"] = pd.to_numeric(raw["In Lacs"], errors="coerce")
    qty_col = "Acutal Quantity" if "Acutal Quantity" in raw.columns else "Actual Quantity"
    if qty_col in raw.columns:
        raw[qty_col] = pd.to_numeric(raw[qty_col], errors="coerce")
    else:
        raw[qty_col] = pd.NA
    raw["State"] = raw["State"].map(lambda x: clean_text(x, "Unclassified"))
    raw["Item Group2"] = raw["Item Group2"].map(lambda x: clean_text(x, "Unclassified"))

    last_date = raw["Date"].max().normalize()
    first_date = last_date.replace(day=1)
    period_key = first_date.strftime("%Y-%m")
    raw["DateKey"] = raw["Date"].dt.strftime("%Y-%m-%d")
    history_start = raw["Date"].min().strftime("%Y-%m-%d")
    history_end = raw["Date"].max().strftime("%Y-%m-%d")
    history_daily = []
    for date_key, group in raw.groupby("DateKey", sort=True):
        history_daily.append({
            "date": date_key,
            "net": number(group["Without GST"].sum(min_count=1)),
        })
    month = raw[(raw["Date"] >= first_date) & (raw["Date"] <= last_date)].copy()

    daily = []
    for date_key, group in month.groupby("DateKey", sort=True):
        daily.append({
            "date": date_key,
            "net": number(group["Without GST"].sum(min_count=1)),
            "gross": number(group["In Lacs"].sum(min_count=1)),
            "qty": number(group[qty_col].sum(min_count=1)),
            "lines": int(len(group)),
            "missingNet": int(group["Without GST"].isna().sum()),
        })

    def grouped_daily(field, value, frame=month):
        result = []
        for (date_key, label), group in frame.groupby(["DateKey", field], dropna=False, sort=True):
            total = group[value].sum(min_count=1)
            result.append({
                "date": date_key,
                "label": clean_text(label, "Unclassified"),
                "value": number(total),
            })
        return result

    state_plan = []
    state_plan_cols = (None, None, None)
    summary_date_header = ""
    nepal_manual = None
    if "Without GST" in book.sheet_names:
        plan_sheet = pd.read_excel(book, sheet_name="Without GST", header=1)
        state_col, plan_col, ach_col = find_plan_columns(plan_sheet)
        state_plan_cols = (plan_col, ach_col, state_col)
        if len(plan_sheet.columns) > 1:
            summary_date_header = clean_text(plan_sheet.columns[1])
        if state_col and plan_col and ach_col:
            plan_sheet[plan_col] = pd.to_numeric(plan_sheet[plan_col], errors="coerce")
            plan_sheet[ach_col] = pd.to_numeric(plan_sheet[ach_col], errors="coerce")
            np_rows = plan_sheet[plan_sheet[state_col].astype(str).str.strip().str.upper().eq("NP")]
            if not np_rows.empty:
                np_row = np_rows.iloc[0]
                product_columns = [
                    ("Kaveri Cone.1", "Kaveri Cone"),
                    ("Nazia Cone.1", "Nazia Cone"),
                    ("Babelois Diaper.1", "Babelois Diaper"),
                    ("Zareen Cone.1", "Zareen Cone"),
                    ("Range Value", "Other / Range Value"),
                ]
                nepal_manual = {
                    "state": "NP",
                    "dailyHeader": summary_date_header,
                    "dailyBilling": number(np_row.get(summary_date_header)),
                    "plan": number(np_row.get(plan_col)),
                    "achievement": number(np_row.get(ach_col)),
                    "achievementPct": number(np_row.get("Achive. %")),
                    "todayPlan": number(np_row.get("Today's Average Plan")),
                    "todayAchievement": number(np_row.get("Today's Ach.")),
                    "productSales": [
                        {"product": name, "value": number(np_row.get(column)) or 0.0}
                        for column, name in product_columns if column in plan_sheet.columns
                    ],
                }
                if manual_nepal_override and manual_nepal_override.get("period") == period_key:
                    nepal_manual.update({key: value for key, value in manual_nepal_override.items() if key != "period"})
                    if nepal_manual.get("plan"):
                        nepal_manual["achievementPct"] = nepal_manual.get("achievement", 0) / nepal_manual["plan"]
            for _, row in plan_sheet.iterrows():
                state = clean_text(row[state_col])
                plan = number(row[plan_col])
                achievement = number(row[ach_col])
                if state.lower() in {"", "nan", "total", "check"} or not plan or plan <= 0 or achievement is None:
                    continue
                state_plan.append({
                    "state": state,
                    "plan": plan,
                    "achievement": achievement,
                    "pct": achievement / plan,
                    "gap": max(0.0, plan - achievement),
                })
            if nepal_manual:
                for item in state_plan:
                    if item["state"].strip().upper() == "NP":
                        item["plan"] = nepal_manual.get("plan", item["plan"])
                        item["achievement"] = nepal_manual.get("achievement", item["achievement"])
                        item["pct"] = item["achievement"] / item["plan"] if item["plan"] else 0
                        item["gap"] = max(0.0, item["plan"] - item["achievement"])
                        item["manualEntry"] = bool(manual_nepal_override and manual_nepal_override.get("period") == period_key)
                        break
            state_plan.sort(key=lambda item: (-item["gap"], item["state"]))

    db = pd.read_excel(book, sheet_name="SS to DB Sale", header=1)
    db_required = {"DB Code", "DB Status", "State", "DB Name", "Zero Billing"}
    missing_db = db_required - set(db.columns)
    if missing_db:
        raise ValueError("SS to DB Sale sheet is missing required column(s): " + ", ".join(sorted(missing_db)))
    status = db["DB Status"].fillna("").astype(str).str.strip().str.upper()
    zero_flag = db["Zero Billing"].fillna("").astype(str).str.strip().str.lower().eq("zero billing db")
    active_zero = db[(status == "ACTIVE") & zero_flag]
    followups = []
    for _, row in active_zero.iterrows():
        followups.append({
            "code": clean_text(row.get("DB Code")),
            "name": clean_text(row.get("DB Name")),
            "state": clean_text(row.get("State"), "Unclassified"),
            "salesRep": clean_text(row.get("Res SR/SO Name")),
            "asm": clean_text(row.get("Res ASM Name")),
            "superStockist": clean_text(row.get("SS Name")),
        })
    followups.sort(key=lambda item: (item["state"], item["name"]))

    zero_by_state = {}
    for item in followups:
        zero_by_state[item["state"]] = zero_by_state.get(item["state"], 0) + 1

    raw_net_total = number(month["Without GST"].sum(min_count=1)) or 0.0
    gross_total = number(month["In Lacs"].sum(min_count=1)) or 0.0
    raw_state_totals = month.groupby("State")["Without GST"].sum(min_count=1).to_dict()
    raw_nepal = number(raw_state_totals.get("NP"))
    nepal_added_manually = bool(nepal_manual and nepal_manual.get("achievement") is not None and raw_nepal is None)
    manual_nepal_value = nepal_manual["achievement"] if nepal_added_manually else 0.0
    if nepal_manual:
        nepal_manual["includedInPeriod"] = nepal_added_manually
        nepal_manual["manualValue"] = manual_nepal_value
        nepal_manual["hasManualEntry"] = bool(manual_nepal_override and manual_nepal_override.get("period") == period_key)
        if nepal_manual.get("achievement") and not nepal_manual.get("achievementPct"):
            nepal_manual["achievementPct"] = nepal_manual["achievement"] / (nepal_manual.get("plan") or 1)
    net_total = raw_net_total + manual_nepal_value
    product_totals = (
        month.groupby("Item Group2")["Without GST"].sum(min_count=1)
        .sort_values(ascending=False)
    )
    product_values = {clean_text(label, "Unclassified"): (number(value) or 0.0) for label, value in product_totals.items()}
    if nepal_added_manually and nepal_manual:
        for item in nepal_manual["productSales"]:
            product_values[item["product"]] = product_values.get(item["product"], 0.0) + item["value"]
    product_mix = [
        {"product": label, "value": value, "share": value / net_total if net_total else 0.0}
        for label, value in sorted(product_values.items(), key=lambda entry: (-entry[1], entry[0]))
    ]

    for item in state_plan:
        if item["state"].strip().upper() == "NP":
            item["manual"] = bool(item.get("manualEntry") or raw_nepal is None)
            break
    reconciliation = []
    for item in state_plan:
        raw_value = number(raw_state_totals.get(item["state"]))
        difference = None if raw_value is None else item["achievement"] - raw_value
        reconciliation.append({
            "state": item["state"],
            "planAchievement": item["achievement"],
            "rawSales": raw_value,
            "difference": difference,
            "matches": difference is not None and abs(difference) <= 0.02,
            "manual": bool(item.get("manual")),
        })

    dup_cols = [name for name in ["Voucher Number", "NEW DB", "Item Name"] if name in month.columns]
    duplicate_rows = int(month.duplicated(subset=dup_cols, keep=False).sum()) if len(dup_cols) >= 2 else 0
    tariff_col = "Tariff" if "Tariff" in month.columns else None
    missing_tariff = int(pd.to_numeric(month[tariff_col], errors="coerce").isna().sum()) if tariff_col else 0
    report_period = {"start": first_date.strftime("%Y-%m-%d"), "end": last_date.strftime("%Y-%m-%d")}

    return {
        "source": source_name,
        "loadedAt": loaded_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "period": report_period,
        "daily": daily,
        "stateByDay": grouped_daily("State", "Without GST"),
        "productByDay": grouped_daily("Item Group2", "Without GST"),
        "history": {
            "start": history_start,
            "end": history_end,
            "daily": history_daily,
            "stateByDay": grouped_daily("State", "Without GST", raw),
            "productByDay": grouped_daily("Item Group2", "Without GST", raw),
        },
        "statePlan": state_plan,
        "reconciliation": reconciliation,
        "followups": followups,
        "zeroByState": zero_by_state,
        "productMix": product_mix,
        "nepalManual": nepal_manual,
        "summaryDateHeader": summary_date_header,
        "planColumns": {"plan": str(state_plan_cols[0] or ""), "achievement": str(state_plan_cols[1] or "")},
        "quality": {
            "salesLines": int(len(month)),
            "missingNet": int(month["Without GST"].isna().sum()),
            "missingTariff": missing_tariff,
            "duplicateRows": duplicate_rows,
            "netTotal": net_total,
            "rawNetTotal": raw_net_total,
            "grossTotal": gross_total,
            "grossVsNetRatio": gross_total / net_total if net_total else None,
            "activeZeroBilling": len(followups),
        },
    }


def build_stock_report(workbook_source, source_name="stock_latest.xlsx", loaded_at=None):
    """Read the stock workbook's product, state, distributor, and NPD summaries."""
    book = pd.ExcelFile(workbook_source)
    missing = REQUIRED_STOCK_SHEETS - set(book.sheet_names)
    if missing:
        raise ValueError("Stock workbook is missing required sheet(s): " + ", ".join(sorted(missing)))

    stock_sheet = pd.read_excel(book, sheet_name="Stock", header=2)
    required_stock = {"Type", "State", "Name"}
    missing_columns = required_stock - set(stock_sheet.columns)
    if missing_columns:
        raise ValueError("Stock sheet is missing required column(s): " + ", ".join(sorted(missing_columns)))

    item_sheet = pd.read_excel(book, sheet_name="Item Stock CS & SS Stock", header=2)
    required_items = {"Item", "CS", "SS", "Grand Total"}
    missing_columns = required_items - set(item_sheet.columns)
    if missing_columns:
        raise ValueError("Item Stock CS & SS Stock sheet is missing required column(s): " + ", ".join(sorted(missing_columns)))

    state_sheet = pd.read_excel(book, sheet_name="State wise Stock", header=2)
    if "Item" not in state_sheet.columns:
        raise ValueError("State wise Stock sheet is missing the Item column.")

    product_rows = item_sheet[
        item_sheet["Item"].notna()
        & ~item_sheet["Item"].astype(str).str.strip().str.lower().eq("grand total")
    ]
    if product_rows.empty:
        raise ValueError("No product stock rows were found in Item Stock CS & SS Stock.")

    raw_stock = pd.read_excel(book, sheet_name="Stock", header=None)
    negative_by_product = {}
    if len(raw_stock.index) > 0:
        for column in range(3, len(raw_stock.columns)):
            product = clean_text(raw_stock.iloc[2, column]) if len(raw_stock.index) > 2 else ""
            negative = number(raw_stock.iloc[0, column])
            if product and negative is not None:
                negative_by_product[product] = negative

    products = []
    for _, row in product_rows.iterrows():
        product = clean_text(row["Item"])
        if not product:
            continue
        products.append({
            "item": product,
            "cs": number(row["CS"]) or 0.0,
            "ss": number(row["SS"]) or 0.0,
            "total": number(row["Grand Total"]) or 0.0,
            "negative": negative_by_product.get(product, 0.0),
        })
    products.sort(key=lambda item: (-item["total"], item["item"]))

    state_columns = [
        column for column in state_sheet.columns
        if column not in {"Item", "Particulars", "Grand Total"}
    ]
    state_rows = state_sheet[
        state_sheet["Item"].notna()
        & ~state_sheet["Item"].astype(str).str.strip().str.lower().eq("grand total")
    ]
    state_product_rows = []
    for _, row in state_sheet[state_sheet["Item"].notna()].iterrows():
        state_product_rows.append({
            "item": clean_text(row["Item"]),
            "particulars": clean_text(row.get("Particulars")),
            "values": {
                str(column): number(row.get(column))
                for column in state_columns
            },
            "grandTotal": number(row.get("Grand Total")),
        })

    states = []
    for column in state_columns:
        total = pd.to_numeric(state_rows[column], errors="coerce").sum(min_count=1)
        value = number(total)
        if value is not None:
            states.append({"state": str(column), "total": value})
    states.sort(key=lambda item: (-item["total"], item["state"]))

    product_columns = [
        column for column in stock_sheet.columns
        if column not in required_stock and column != "Grand Total"
    ]
    distributors = []
    for _, row in stock_sheet.iterrows():
        name = clean_text(row.get("Name"))
        if not name or name.lower() in {"grand total", "total"}:
            continue
        item_values = [number(row.get(column)) or 0.0 for column in product_columns]
        distributors.append({
            "name": name,
            "type": clean_text(row.get("Type")),
            "state": clean_text(row.get("State"), "Unclassified"),
            "total": sum(item_values),
            "negativeItems": sum(value < -0.01 for value in item_values),
        })
    distributors.sort(key=lambda item: (-item["total"], item["name"]))

    npd_total = 0.0
    if "NPD Stock" in book.sheet_names:
        npd_sheet = pd.read_excel(book, sheet_name="NPD Stock", header=2)
        npd_columns = [column for column in npd_sheet.columns if column not in required_stock]
        npd_total = sum(
            number(pd.to_numeric(npd_sheet[column], errors="coerce").sum(min_count=1)) or 0.0
            for column in npd_columns
        )

    negative_values = [item["negative"] for item in products if item["negative"] < 0]
    opening_label = clean_text(raw_stock.iloc[1, 0]) if len(raw_stock.index) > 1 else ""
    date_match = re.search(r"\d{1,2}-[A-Za-z]{3}-\d{2,4}", opening_label)
    return {
        "source": source_name,
        "loadedAt": loaded_at or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "reportDate": date_match.group(0) if date_match else opening_label,
        "summary": {
            "totalStock": sum(item["total"] for item in products),
            "csStock": sum(item["cs"] for item in products),
            "ssStock": sum(item["ss"] for item in products),
            "negativeStock": sum(abs(value) for value in negative_values),
            "negativeProductCount": len(negative_values),
            "npdStock": npd_total,
            "distributorCount": len(distributors),
        },
        "products": products,
        "states": states,
        "stateColumns": [str(column) for column in state_columns],
        "stateProductRows": state_product_rows,
        "distributors": distributors,
    }


def read_metadata():
    if not META_PATH.exists():
        return {"source_name": WORKBOOK_PATH.name, "loaded_at": "Initial workbook"}
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"source_name": WORKBOOK_PATH.name, "loaded_at": "Unknown"}


def read_nepal_manual():
    if not NEPAL_MANUAL_PATH.exists():
        return None
    try:
        return json.loads(NEPAL_MANUAL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def get_report():
    mtime = WORKBOOK_PATH.stat().st_mtime
    manual_mtime = NEPAL_MANUAL_PATH.stat().st_mtime if NEPAL_MANUAL_PATH.exists() else None
    cache_key = (mtime, manual_mtime)
    with _CACHE_LOCK:
        if _CACHE["payload"] is not None and _CACHE["mtime"] == cache_key:
            return _CACHE["payload"]
        meta = read_metadata()
        payload = build_report(WORKBOOK_PATH, meta.get("source_name", WORKBOOK_PATH.name), meta.get("loaded_at"), read_nepal_manual())
        _CACHE.update({"mtime": cache_key, "payload": payload})
        return payload


def get_stock_report():
    if not STOCK_WORKBOOK_PATH.exists():
        return None
    mtime = STOCK_WORKBOOK_PATH.stat().st_mtime
    with _CACHE_LOCK:
        if _STOCK_CACHE["payload"] is not None and _STOCK_CACHE["mtime"] == mtime:
            return _STOCK_CACHE["payload"]
        try:
            meta = json.loads(STOCK_META_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {"source_name": STOCK_WORKBOOK_PATH.name, "loaded_at": "Unknown"}
        payload = build_stock_report(
            STOCK_WORKBOOK_PATH,
            meta.get("source_name", STOCK_WORKBOOK_PATH.name),
            meta.get("loaded_at"),
        )
        _STOCK_CACHE.update({"mtime": mtime, "payload": payload})
        return payload


def get_weekly_performance():
    if not WEEKLY_WORKBOOK_PATH.exists():
        return {"available": False}
    mtime = WEEKLY_WORKBOOK_PATH.stat().st_mtime
    with _CACHE_LOCK:
        if _WEEKLY_CACHE["payload"] is not None and _WEEKLY_CACHE["mtime"] == mtime:
            return _WEEKLY_CACHE["payload"]
        try:
            meta = json.loads(WEEKLY_META_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {"source_name": WEEKLY_WORKBOOK_PATH.name, "loaded_at": "Unknown"}
        payload = build_weekly_performance(
            WEEKLY_WORKBOOK_PATH,
            meta.get("source_name", WEEKLY_WORKBOOK_PATH.name),
            meta.get("loaded_at"),
        )
        _WEEKLY_CACHE.update({"mtime": mtime, "payload": payload})
        return payload


def get_last_year_report():
    if not LAST_YEAR_WORKBOOK_PATH.exists():
        return None
    mtime = LAST_YEAR_WORKBOOK_PATH.stat().st_mtime
    with _CACHE_LOCK:
        if _LAST_YEAR_CACHE["payload"] is not None and _LAST_YEAR_CACHE["mtime"] == mtime:
            return _LAST_YEAR_CACHE["payload"]
        try:
            meta = json.loads(LAST_YEAR_META_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {"source_name": LAST_YEAR_WORKBOOK_PATH.name, "loaded_at": "Unknown"}
        payload = build_report(
            LAST_YEAR_WORKBOOK_PATH,
            meta.get("source_name", LAST_YEAR_WORKBOOK_PATH.name),
            meta.get("loaded_at"),
        )
        _LAST_YEAR_CACHE.update({"mtime": mtime, "payload": payload})
        return payload


def validate_workbook_bytes(contents):
    try:
        book = pd.ExcelFile(BytesIO(contents))
    except Exception as exc:
        raise ValueError("I could not read that Excel file. Please choose an .xlsx workbook.") from exc
    missing = REQUIRED_SHEETS - set(book.sheet_names)
    if missing:
        raise ValueError("Workbook must include: " + ", ".join(sorted(REQUIRED_SHEETS)) + ". Missing: " + ", ".join(sorted(missing)))
    build_report(BytesIO(contents), "uploaded workbook", datetime.now().strftime("%Y-%m-%d %H:%M"))


def validate_stock_workbook_bytes(contents):
    try:
        book = pd.ExcelFile(BytesIO(contents))
    except Exception as exc:
        raise ValueError("I could not read that Excel file. Please choose an .xlsx stock workbook.") from exc
    missing = REQUIRED_STOCK_SHEETS - set(book.sheet_names)
    if missing:
        raise ValueError(
            "Stock workbook must include: " + ", ".join(sorted(REQUIRED_STOCK_SHEETS))
            + ". Missing: " + ", ".join(sorted(missing))
        )
    build_stock_report(BytesIO(contents), "uploaded stock workbook", datetime.now().strftime("%Y-%m-%d %H:%M"))


def validate_weekly_workbook_bytes(contents):
    try:
        book = pd.ExcelFile(BytesIO(contents))
    except Exception as exc:
        raise ValueError("I could not read that Excel file. Please choose an .xlsx weekly plan workbook.") from exc
    if not book.sheet_names:
        raise ValueError("The weekly plan workbook has no worksheets.")
    build_weekly_performance(BytesIO(contents), "uploaded weekly plan", datetime.now().strftime("%Y-%m-%d %H:%M"))


class SalesMISHandler(BaseHTTPRequestHandler):
    server_version = "SalesMIS/1.0"

    @staticmethod
    def _credentials():
        username = os.environ.get("SALES_MIS_USERNAME", "")
        password = os.environ.get("SALES_MIS_PASSWORD", "")
        return username, password

    @classmethod
    def _session_signature(cls, expires):
        username, password = cls._credentials()
        credentials = f"{username}\0{password}".encode("utf-8")
        key = hmac.new(SESSION_SIGNING_KEY, credentials, hashlib.sha256).digest()
        return hmac.new(key, expires.encode("ascii"), hashlib.sha256).hexdigest()

    def _has_valid_session(self):
        cookie_header = self.headers.get("Cookie", "")
        cookie = next(
            (
                part.strip().partition("=")[2]
                for part in cookie_header.split(";")
                if part.strip().startswith(SESSION_COOKIE_NAME + "=")
            ),
            "",
        )
        expires, separator, signature = cookie.partition(".")
        if (
            not separator
            or not expires.isascii()
            or not expires.isdigit()
            or len(expires) > 12
            or not signature
        ):
            return False
        if int(expires) < int(time.time()):
            return False
        return hmac.compare_digest(signature, self._session_signature(expires))

    def _cookie_attributes(self, max_age):
        attributes = [
            f"{SESSION_COOKIE_NAME}=; Path=/",
            f"Max-Age={max_age}",
            "HttpOnly",
            "SameSite=Strict",
        ]
        if self.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip().lower() == "https":
            attributes.append("Secure")
        return "; ".join(attributes)

    def _send_login_page(self, status=200, error=""):
        message = (
            f'<p role="alert" style="color:#b42318">{error}</p>'
            if error
            else ""
        )
        page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Sign in | Velnik MIS</title>
<script src="/static/language.js" defer></script>
<style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;
background:#f4f6f3;color:#1c2c25;font:16px Arial,sans-serif}}
main{{width:min(100% - 32px,400px);padding:32px;background:#fff;border:1px solid #dfe5e0;
border-radius:12px;box-shadow:0 8px 28px #243b2f12}}
h1{{margin:0 0 8px;font-size:24px}}p{{color:#58665f}}
label{{display:block;margin:18px 0 6px;font-weight:600}}
input{{width:100%;padding:12px;border:1px solid #aab7ae;border-radius:6px;font:inherit}}
button{{width:100%;margin-top:22px;padding:12px;border:0;border-radius:6px;
background:#174a38;color:white;font:inherit;font-weight:600;cursor:pointer}}
</style></head><body><main><button id="pageLanguageToggle" type="button" aria-label="पेज की भाषा हिंदी में बदलें" style="width:auto;margin:0 0 18px;padding:8px 12px">हिन्दी</button><h1>Velnik MIS</h1>
<p>Reports are public. Sign in with the owner account to upload workbooks and update figures.</p>{message}
<form method="post" action="/login" autocomplete="on">
<label for="username">Username</label><input id="username" name="username" autocomplete="username" required>
<label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required>
<button type="submit">Sign in</button></form></main></body></html>"""
        return self.send_bytes(status, page.encode("utf-8"), "text/html; charset=utf-8")

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _render_owner_controls(self, template):
        is_owner = self._has_valid_session()
        template = template.replace("__OWNER_SESSION__", str(is_owner).lower())
        template = template.replace(
            "__OWNER_NAV__",
            (
                '<a href="/backup-download">Download backup</a><a href="/logout">Sign out</a>'
                if is_owner else '<a href="/login">Owner sign in</a>'
            ),
        )
        if is_owner:
            return re.sub(r"<!--GUEST-ONLY-->.*?<!--/GUEST-ONLY-->", "", template, flags=re.DOTALL)
        return re.sub(r"<!--OWNER-ONLY-->.*?<!--/OWNER-ONLY-->", "", template, flags=re.DOTALL)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.send_bytes(200, b"ok", "text/plain; charset=utf-8")
        username, password = self._credentials()
        if path == "/login":
            if not username or not password:
                return self.send_bytes(
                    503,
                    b"Owner sign-in is not configured. Set SALES_MIS_USERNAME and SALES_MIS_PASSWORD.",
                    "text/plain; charset=utf-8",
                )
            if self._has_valid_session():
                return self._redirect("/")
            return self._send_login_page()
        if path == "/logout":
            self.send_response(303)
            self.send_header("Location", "/login")
            self.send_header("Set-Cookie", self._cookie_attributes(0))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/backup-download":
            username, password = self._credentials()
            if not username or not password:
                return self.send_bytes(
                    503,
                    b"Owner sign-in is not configured. Set SALES_MIS_USERNAME and SALES_MIS_PASSWORD.",
                    "text/plain; charset=utf-8",
                )
            if not self._has_valid_session():
                return self.send_bytes(401, b"Sign in is required to download a backup.", "text/plain; charset=utf-8")
            files = [
                DATA_DIR / filename
                for filename in BACKUP_FILE_NAMES
                if (DATA_DIR / filename).is_file()
            ]
            total_size = sum(path.stat().st_size for path in files)
            if total_size > MAX_BACKUP_BYTES:
                return self.send_bytes(413, b"Backup exceeds the 250 MB download limit.", "text/plain; charset=utf-8")
            archive = BytesIO()
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as backup:
                for path in files:
                    backup.write(path, arcname=path.name)
            filename = f"sales-mis-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
            body = archive.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/static/"):
            filename = Path(path.removeprefix("/static/")).name
            file_path = STATIC_DIR / filename
            if not file_path.exists() or file_path.parent != STATIC_DIR:
                return self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            return self.send_bytes(200, file_path.read_bytes(), content_type + "; charset=utf-8")
        if path == "/stock":
            try:
                payload = get_stock_report() or {"available": False}
                template = (TEMPLATE_DIR / "stock.html").read_text(encoding="utf-8")
                encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
                page = template.replace("__STOCK_DATA__", encoded)
                page = self._render_owner_controls(page)
                return self.send_bytes(200, page.encode("utf-8"), "text/html; charset=utf-8")
            except Exception as exc:
                body = ("<h1>Could not build the stock report</h1><p>" + str(exc) + "</p>").encode("utf-8")
                return self.send_bytes(500, body, "text/html; charset=utf-8")
        if path != "/":
            return self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
        try:
            payload = {**get_report(), "weeklyPerformance": get_weekly_performance()}
            try:
                last_year_report = get_last_year_report()
                last_year_error = None
            except (OSError, ValueError, KeyError, IndexError) as exc:
                last_year_report = None
                last_year_error = str(exc)
            payload["lastYearData"] = (
                {
                    "source": last_year_report["source"],
                    "loadedAt": last_year_report["loadedAt"],
                    "history": last_year_report["history"],
                }
                if last_year_report
                else None
            )
            payload["lastYearError"] = last_year_error
            try:
                stock_report = get_stock_report()
                stock_state_error = None
            except (OSError, ValueError, KeyError, IndexError) as exc:
                stock_report = None
                stock_state_error = str(exc)
            payload["stockStateData"] = (
                {
                    "reportDate": stock_report["reportDate"],
                    "states": stock_report["states"],
                }
                if stock_report
                else None
            )
            payload["stockStateError"] = stock_state_error
            payload["populationRegions"] = [
                {
                    "state": state,
                    "population": population,
                    **POPULATION_REGION_MEMBERS[state],
                }
                for state, population in POPULATION_PROJECTIONS_2026.items()
            ]
            payload["populationSource"] = POPULATION_SOURCE
            payload["populationSourceUrl"] = POPULATION_SOURCE_URL
            template = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
            page = template.replace("__REPORT_DATA__", encoded)
            page = self._render_owner_controls(page)
            return self.send_bytes(200, page.encode("utf-8"), "text/html; charset=utf-8")
        except Exception as exc:
            body = ("<h1>Could not build the report</h1><p>" + str(exc) + "</p>").encode("utf-8")
            return self.send_bytes(500, body, "text/html; charset=utf-8")

    def do_POST(self):
        request_path = urlparse(self.path).path
        if request_path == "/login":
            username, password = self._credentials()
            if not username or not password:
                return self.send_bytes(
                    503,
                    b"Owner sign-in is not configured. Set SALES_MIS_USERNAME and SALES_MIS_PASSWORD.",
                    "text/plain; charset=utf-8",
                )
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length <= 0 or content_length > 8_192:
                    raise ValueError
                if "application/x-www-form-urlencoded" not in self.headers.get("Content-Type", ""):
                    raise ValueError
                form = parse_qs(self.rfile.read(content_length).decode("utf-8"), strict_parsing=True)
                submitted_username = form.get("username", [""])[0]
                submitted_password = form.get("password", [""])[0]
            except (UnicodeDecodeError, ValueError):
                return self._send_login_page(400, "Enter your username and password.")
            username_matches = hmac.compare_digest(
                submitted_username.encode("utf-8"),
                username.encode("utf-8"),
            )
            password_matches = hmac.compare_digest(
                submitted_password.encode("utf-8"),
                password.encode("utf-8"),
            )
            if not (username_matches and password_matches):
                return self._send_login_page(401, "The username or password is incorrect.")
            expires = str(int(time.time()) + SESSION_TTL_SECONDS)
            signature = self._session_signature(expires)
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header(
                "Set-Cookie",
                f"{SESSION_COOKIE_NAME}={expires}.{signature}; Path=/; Max-Age={SESSION_TTL_SECONDS}; HttpOnly; SameSite=Strict"
                + (
                    "; Secure"
                    if self.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip().lower() == "https"
                    else ""
                ),
            )
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if request_path == "/logout":
            self.send_response(303)
            self.send_header("Location", "/login")
            self.send_header("Set-Cookie", self._cookie_attributes(0))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        owner_routes = {
            "/nepal-manual",
            "/upload",
            "/stock-upload",
            "/weekly-upload",
            "/last-year-upload",
        }
        if request_path in owner_routes:
            username, password = self._credentials()
            if not username or not password:
                return self.send_bytes(
                    503,
                    b"Owner sign-in is not configured. Set SALES_MIS_USERNAME and SALES_MIS_PASSWORD.",
                    "text/plain; charset=utf-8",
                )
        if request_path in owner_routes and not self._has_valid_session():
            return self.send_bytes(
                401,
                b'{"ok":false,"error":"Sign in is required.","loginUrl":"/login"}',
                "application/json; charset=utf-8",
            )
        if request_path not in owner_routes and request_path != "/ai-chat":
            return self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
        if request_path == "/ai-chat":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length <= 0 or content_length > 24_000:
                    raise ValueError("Chat request must be smaller than 24 KB.")
                data = json.loads(self.rfile.read(content_length).decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("Chat request must be a JSON object.")
                question = data.get("question")
                if not isinstance(question, str) or not question.strip() or len(question) > 1500:
                    raise ValueError("Enter a question of 1–1,500 characters.")
                scope = data.get("scope", "both")
                if not isinstance(scope, str) or scope not in {"both", "sales", "stock"}:
                    raise ValueError("Choose sales, stock, or combined analysis.")
                language = data.get("language", "en")
                if not isinstance(language, str) or language not in {"en", "hi"}:
                    raise ValueError("Choose English or Hindi for the analysis.")
                start_date = data.get("startDate")
                end_date = data.get("endDate")
                for value in (start_date, end_date):
                    if value is not None:
                        if not isinstance(value, str):
                            raise ValueError("Selected dates must use YYYY-MM-DD format.")
                        if datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") != value:
                            raise ValueError("Selected dates must use YYYY-MM-DD format.")
                context = build_analysis_context(scope, start_date, end_date)
                answer = build_local_analysis(question.strip(), context, language)
                response = json.dumps({"ok": True, "answer": answer}).encode("utf-8")
                return self.send_bytes(200, response, "application/json; charset=utf-8")
            except (ValueError, json.JSONDecodeError) as exc:
                response = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                return self.send_bytes(400, response, "application/json; charset=utf-8")
            except Exception as exc:
                response = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                return self.send_bytes(502, response, "application/json; charset=utf-8")
        if request_path == "/nepal-manual":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length <= 0 or content_length > 32_000:
                    raise ValueError("Enter Nepal values and save again.")
                data = json.loads(self.rfile.read(content_length).decode("utf-8"))
                report = get_report()
                current = report.get("nepalManual")
                if not current:
                    raise ValueError("No NP summary row is available in this workbook.")

                def required_amount(key, label):
                    value = number(data.get(key))
                    if value is None:
                        raise ValueError(f"Enter a valid number for {label}.")
                    return value

                product_sales = data.get("productSales")
                if not isinstance(product_sales, list) or not product_sales:
                    raise ValueError("Nepal product amounts are missing.")
                cleaned_products = []
                for item in product_sales:
                    if not isinstance(item, dict) or not item.get("product"):
                        raise ValueError("A Nepal product name is missing.")
                    product_value = number(item.get("value"))
                    if product_value is None:
                        raise ValueError(f"Enter a valid number for {item['product']}.")
                    cleaned_products.append({
                        "product": str(item["product"])[:80],
                        "value": product_value,
                    })
                achievement = required_amount("achievement", "monthly billing achievement")
                product_sum = sum(item["value"] for item in cleaned_products)
                if abs(product_sum - achievement) > 0.02:
                    raise ValueError("Nepal product amounts must add up to the monthly billing achievement. Adjust Other / Range Value.")
                saved = {
                    "period": report["period"]["start"][:7],
                    "plan": required_amount("plan", "monthly plan"),
                    "achievement": achievement,
                    "dailyBilling": required_amount("dailyBilling", "dated billing amount"),
                    "dailyHeader": str(current.get("dailyHeader") or "Summary date")[:30],
                    "todayPlan": required_amount("todayPlan", "today's average plan"),
                    "todayAchievement": required_amount("todayAchievement", "today's achievement"),
                    "productSales": cleaned_products,
                }
                NEPAL_MANUAL_PATH.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
                with _CACHE_LOCK:
                    _CACHE.update({"mtime": None, "payload": None})
                return self.send_bytes(200, json.dumps({"ok": True, "period": saved["period"]}).encode("utf-8"), "application/json; charset=utf-8")
            except (ValueError, json.JSONDecodeError) as exc:
                response = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                return self.send_bytes(400, response, "application/json; charset=utf-8")
            except Exception as exc:
                response = json.dumps({"ok": False, "error": "Nepal values could not be saved: " + str(exc)}).encode("utf-8")
                return self.send_bytes(500, response, "application/json; charset=utf-8")

        if request_path not in {"/upload", "/stock-upload", "/weekly-upload", "/last-year-upload"}:
            return self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
        is_stock_upload = request_path == "/stock-upload"
        is_weekly_upload = request_path == "/weekly-upload"
        is_last_year_upload = request_path == "/last-year-upload"
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
                raise ValueError("Upload must be smaller than 50 MB.")
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                raise ValueError("Choose an Excel workbook to upload.")
            message = BytesParser(policy=policy.default).parsebytes(
                (f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n").encode("utf-8")
                + self.rfile.read(content_length)
            )
            upload = next((part for part in message.iter_parts() if part.get_param("name", header="content-disposition") == "workbook"), None)
            if upload is None:
                raise ValueError("No workbook was included in the upload.")
            filename = Path(upload.get_filename() or "").name
            if not filename.lower().endswith(".xlsx"):
                raise ValueError("Please upload an .xlsx file.")
            contents = upload.get_payload(decode=True) or b""
            if not contents:
                raise ValueError("The selected file is empty.")
            if is_last_year_upload:
                validate_workbook_bytes(contents)
                replace_workbook(contents, LAST_YEAR_WORKBOOK_PATH)
                meta_path = LAST_YEAR_META_PATH
                cache = _LAST_YEAR_CACHE
            elif is_weekly_upload:
                validate_weekly_workbook_bytes(contents)
                replace_workbook(contents, WEEKLY_WORKBOOK_PATH)
                meta_path = WEEKLY_META_PATH
                cache = _WEEKLY_CACHE
            elif is_stock_upload:
                validate_stock_workbook_bytes(contents)
                replace_workbook(contents, STOCK_WORKBOOK_PATH)
                meta_path = STOCK_META_PATH
                cache = _STOCK_CACHE
            else:
                validate_workbook_bytes(contents)
                replace_workbook(contents, WORKBOOK_PATH)
                meta_path = META_PATH
                cache = _CACHE
            loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            meta_path.write_text(json.dumps({"source_name": filename, "loaded_at": loaded_at}), encoding="utf-8")
            with _CACHE_LOCK:
                cache.update({"mtime": None, "payload": None})
            response = json.dumps({
                "ok": True,
                "filename": filename,
                "loadedAt": loaded_at,
                "reportUrl": "/stock" if is_stock_upload else "/",
            }).encode("utf-8")
            return self.send_bytes(200, response, "application/json; charset=utf-8")
        except ValueError as exc:
            response = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
            return self.send_bytes(400, response, "application/json; charset=utf-8")
        except Exception as exc:
            response = json.dumps({"ok": False, "error": "Upload failed: " + str(exc)}).encode("utf-8")
            return self.send_bytes(500, response, "application/json; charset=utf-8")

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser(description="Local Sales MIS dashboard")
    parser.add_argument("--check", action="store_true", help="Read the current workbook and print a data summary")
    parser.add_argument("--host", default="127.0.0.1", help="Address to bind the web server to")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5000")), help="Web server port")
    args = parser.parse_args()
    if not WORKBOOK_PATH.exists():
        raise SystemExit(f"Starting workbook not found: {WORKBOOK_PATH}")
    if args.check:
        report = get_report()
        print(json.dumps({
            "source": report["source"],
            "period": report["period"],
            "salesLines": report["quality"]["salesLines"],
            "salesWithoutGSTLakh": round(report["quality"]["netTotal"], 2),
            "activeZeroBilling": report["quality"]["activeZeroBilling"],
            "missingNet": report["quality"]["missingNet"],
            "UP": next((x for x in report["reconciliation"] if x["state"] == "UP"), None),
            "UK": next((x for x in report["reconciliation"] if x["state"] == "UK"), None),
        }, ensure_ascii=False, indent=2))
        return
    if not all(SalesMISHandler._credentials()):
        raise SystemExit(
            "Set SALES_MIS_USERNAME and SALES_MIS_PASSWORD before starting the web server."
        )
    server = ThreadingHTTPServer((args.host, args.port), SalesMISHandler)
    if args.host == "127.0.0.1":
        print(f"Sales MIS is running locally at http://127.0.0.1:{args.port}")
    else:
        print(f"Sales MIS is listening on {args.host}:{args.port}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Sales MIS.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
