from __future__ import annotations

import argparse
import json
import mimetypes
import re
import shutil
import threading
from datetime import datetime
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
WORKBOOK_PATH = DATA_DIR / "latest.xlsx"
META_PATH = DATA_DIR / "source.json"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
REQUIRED_SHEETS = {"Raw", "SS to DB Sale"}
_CACHE_LOCK = threading.Lock()
_CACHE = {"mtime": None, "payload": None}


def clean_text(value, fallback=""):
    if pd.isna(value):
        return fallback
    return str(value).strip()


def number(value):
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(parsed) else float(parsed)


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


def build_report(workbook_source, source_name="latest.xlsx", loaded_at=None):
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
    month = raw[(raw["Date"] >= first_date) & (raw["Date"] <= last_date)].copy()
    month["DateKey"] = month["Date"].dt.strftime("%Y-%m-%d")

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

    def grouped_daily(field, value):
        result = []
        for (date_key, label), group in month.groupby(["DateKey", field], dropna=False, sort=True):
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
    if "Without GST" in book.sheet_names:
        plan_sheet = pd.read_excel(book, sheet_name="Without GST", header=1)
        state_col, plan_col, ach_col = find_plan_columns(plan_sheet)
        state_plan_cols = (plan_col, ach_col, state_col)
        if len(plan_sheet.columns) > 1:
            summary_date_header = clean_text(plan_sheet.columns[1])
        if state_col and plan_col and ach_col:
            plan_sheet[plan_col] = pd.to_numeric(plan_sheet[plan_col], errors="coerce")
            plan_sheet[ach_col] = pd.to_numeric(plan_sheet[ach_col], errors="coerce")
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

    net_total = number(month["Without GST"].sum(min_count=1)) or 0.0
    gross_total = number(month["In Lacs"].sum(min_count=1)) or 0.0
    product_totals = (
        month.groupby("Item Group2")["Without GST"].sum(min_count=1)
        .sort_values(ascending=False)
    )
    product_mix = [
        {"product": clean_text(label, "Unclassified"), "value": number(value) or 0.0,
         "share": (number(value) or 0.0) / net_total if net_total else 0.0}
        for label, value in product_totals.items()
    ]

    raw_state_totals = month.groupby("State")["Without GST"].sum(min_count=1).to_dict()
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
        "statePlan": state_plan,
        "reconciliation": reconciliation,
        "followups": followups,
        "zeroByState": zero_by_state,
        "productMix": product_mix,
        "summaryDateHeader": summary_date_header,
        "planColumns": {"plan": str(state_plan_cols[0] or ""), "achievement": str(state_plan_cols[1] or "")},
        "quality": {
            "salesLines": int(len(month)),
            "missingNet": int(month["Without GST"].isna().sum()),
            "missingTariff": missing_tariff,
            "duplicateRows": duplicate_rows,
            "netTotal": net_total,
            "grossTotal": gross_total,
            "grossVsNetRatio": gross_total / net_total if net_total else None,
            "activeZeroBilling": len(followups),
        },
    }


def read_metadata():
    if not META_PATH.exists():
        return {"source_name": WORKBOOK_PATH.name, "loaded_at": "Initial workbook"}
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"source_name": WORKBOOK_PATH.name, "loaded_at": "Unknown"}


def get_report():
    mtime = WORKBOOK_PATH.stat().st_mtime
    with _CACHE_LOCK:
        if _CACHE["payload"] is not None and _CACHE["mtime"] == mtime:
            return _CACHE["payload"]
        meta = read_metadata()
        payload = build_report(WORKBOOK_PATH, meta.get("source_name", WORKBOOK_PATH.name), meta.get("loaded_at"))
        _CACHE.update({"mtime": mtime, "payload": payload})
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


class SalesMISHandler(BaseHTTPRequestHandler):
    server_version = "SalesMIS/1.0"

    def send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.send_bytes(200, b"ok", "text/plain; charset=utf-8")
        if path.startswith("/static/"):
            filename = Path(path.removeprefix("/static/")).name
            file_path = STATIC_DIR / filename
            if not file_path.exists() or file_path.parent != STATIC_DIR:
                return self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            return self.send_bytes(200, file_path.read_bytes(), content_type + "; charset=utf-8")
        if path != "/":
            return self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
        try:
            payload = get_report()
            template = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
            page = template.replace("__REPORT_DATA__", encoded)
            return self.send_bytes(200, page.encode("utf-8"), "text/html; charset=utf-8")
        except Exception as exc:
            body = ("<h1>Could not build the report</h1><p>" + str(exc) + "</p>").encode("utf-8")
            return self.send_bytes(500, body, "text/html; charset=utf-8")

    def do_POST(self):
        if urlparse(self.path).path != "/upload":
            return self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")
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
            validate_workbook_bytes(contents)
            temporary = DATA_DIR / "latest.uploading.xlsx"
            temporary.write_bytes(contents)
            temporary.replace(WORKBOOK_PATH)
            loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            META_PATH.write_text(json.dumps({"source_name": filename, "loaded_at": loaded_at}), encoding="utf-8")
            with _CACHE_LOCK:
                _CACHE.update({"mtime": None, "payload": None})
            response = json.dumps({"ok": True, "filename": filename, "loadedAt": loaded_at}).encode("utf-8")
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
    parser.add_argument("--port", type=int, default=5000, help="Local web server port")
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
    server = ThreadingHTTPServer(("127.0.0.1", args.port), SalesMISHandler)
    print(f"Sales MIS is running locally at http://127.0.0.1:{args.port}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Sales MIS.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
