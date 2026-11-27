import json
import http.client
from io import BytesIO
import os
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import app
from billing_efficiency import build_billing_efficiency_report


class ExecutiveKpiTests(unittest.TestCase):
    def test_calculates_plan_gap_forecast_and_status(self):
        kpis = app.calculate_executive_kpis(
            [{"state": "UP", "plan": 100, "achievement": 60}],
            60,
            pd.Timestamp("2026-10-31").to_pydatetime(),
        )
        self.assertEqual(kpis["planTotal"], 100)
        self.assertEqual(kpis["achievementPct"], 0.6)
        self.assertEqual(kpis["remainingGap"], 40)
        self.assertEqual(kpis["elapsedDays"], 31)
        self.assertEqual(kpis["daysRemaining"], 0)
        self.assertEqual(kpis["dailyRunRate"], 60 / 31)
        self.assertEqual(kpis["projectedMonthEnd"], 60)
        self.assertEqual(kpis["forecastStatus"], "behind")

    def test_uses_workbook_total_row_when_available(self):
        kpis = app.calculate_executive_kpis(
            [{"state": "UP", "plan": 2500, "achievement": 1720}],
            1720,
            pd.Timestamp("2026-10-31").to_pydatetime(),
            7950,
        )
        self.assertEqual(kpis["planTotal"], 7950)
        self.assertEqual(kpis["remainingGap"], 6230)


class BillingEfficiencyReportTests(unittest.TestCase):
    def create_workbook(self, rows):
        temporary = tempfile.TemporaryFile()
        with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(
                writer,
                sheet_name="SS to DB Sale",
                index=False,
                startrow=1,
            )
        temporary.seek(0)
        return temporary

    def test_builds_monthly_billing_coverage_and_flags_duplicates(self):
        rows = [
            {
                "Month": "Apr",
                "DB Code": "DB-1",
                "DB Status": "Active",
                "Zone": "North",
                "State": "State A",
                "SS Name": "SS A",
                "DB Name": "Distributor 1",
                "Res SR/SO Name": "Rep A",
                "Value In Lacs": 2,
                "Babelois Diaper": 1,
            },
            {
                "Month": "Apr",
                "DB Code": "DB-2",
                "DB Status": "ACTIVE",
                "Zone": "North",
                "State": "State A",
                "SS Name": "SS A",
                "DB Name": "Distributor 2",
                "Res SR/SO Name": "Rep A",
                "Value In Lacs": 0,
                "Babelois Diaper": 0,
            },
            {
                "Month": "Apr",
                "DB Code": "DB-2",
                "DB Status": "Active",
                "Zone": "North",
                "State": "State A",
                "SS Name": "SS A",
                "DB Name": "Distributor 2",
                "Res SR/SO Name": "Rep A",
                "Value In Lacs": 0,
                "Babelois Diaper": 0,
            },
            {
                "Month": "Apr",
                "DB Code": "DB-3",
                "DB Status": "Inactive",
                "Zone": "South",
                "State": "State B",
                "SS Name": "SS B",
                "DB Name": "Distributor 3",
                "Res SR/SO Name": "Rep B",
                "Value In Lacs": 5,
                "Babelois Diaper": 2,
            },
            {
                "Month": "May",
                "DB Code": "DB-4",
                "DB Status": "Active",
                "Zone": "South",
                "State": "State B",
                "SS Name": "SS B",
                "DB Name": "Distributor 4",
                "Res SR/SO Name": "Rep B",
                "Value In Lacs": -1,
                "Babelois Diaper": 1,
            },
        ]
        workbook = self.create_workbook(rows)
        try:
            report = build_billing_efficiency_report(workbook)
        finally:
            workbook.close()

        self.assertEqual(report["months"], ["Apr", "May"])
        self.assertEqual(report["monthly"][0]["salesLakh"], 7)
        self.assertEqual(report["monthly"][0]["activeDbCount"], 2)
        self.assertEqual(report["monthly"][0]["billedActiveDbCount"], 1)
        self.assertEqual(report["monthly"][0]["zeroBillingActiveDbCount"], 1)
        self.assertEqual(report["monthly"][0]["efficiencyPct"], 50)
        self.assertEqual(report["quality"]["duplicateDistributorMonthRows"], 1)
        self.assertEqual(
            [(row["month"], row["dbCode"]) for row in report["zeroBilling"]],
            [("Apr", "DB-2"), ("May", "DB-4")],
        )
        product = next(row for row in report["products"] if row["product"] == "Babelois Diaper")
        self.assertEqual(product["billedDistributors"], 1)

    def test_requires_expected_sheet_and_columns(self):
        workbook = tempfile.TemporaryFile()
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            pd.DataFrame({"Month": ["Apr"]}).to_excel(writer, sheet_name="Other", index=False)
        workbook.seek(0)
        try:
            with self.assertRaisesRegex(ValueError, "SS to DB Sale"):
                build_billing_efficiency_report(workbook)
        finally:
            workbook.close()

    def test_manager_scope_limits_billing_rows_and_summaries(self):
        workbook = self.create_workbook([
            {
                "Month": "Apr", "DB Code": "DB-1", "DB Status": "Active",
                "Zone": "North", "State": "State A", "SS Name": "SS A",
                "DB Name": "Distributor 1", "Res SR/SO Name": "Rep A",
                "Value In Lacs": 0, "Babelois Diaper": 1,
            },
            {
                "Month": "Apr", "DB Code": "DB-2", "DB Status": "Active",
                "Zone": "South", "State": "State B", "SS Name": "SS B",
                "DB Name": "Distributor 2", "Res SR/SO Name": "Rep B",
                "Value In Lacs": 9, "Babelois Diaper": 1,
            },
        ])
        try:
            report = build_billing_efficiency_report(workbook, allowed_states={"state a"})
        finally:
            workbook.close()

        self.assertEqual(report["monthly"][0]["salesLakh"], 0)
        self.assertEqual({row["state"] for row in report["states"]}, {"State A"})
        self.assertEqual({row["dbName"] for row in report["zeroBilling"]}, {"Distributor 1"})


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "SALES_MIS_USERNAME": "owner",
                "SALES_MIS_PASSWORD": "test-password",
                "SALES_MIS_MANAGERS": "",
            },
        )
        self.environment.start()
        self.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.SalesMISHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.environment.stop()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.getheaders(), response.read()
        connection.close()
        return result

    def test_reports_and_workbook_changes_require_owner_login(self):
        status, _, body = self.request("GET", "/login")
        self.assertEqual(status, 200)
        self.assertIn(b"Choose Owner or Manager sign in", body)

        status, _, body = self.request("GET", "/static/styles.css")
        self.assertEqual(status, 200)
        self.assertIn(b"--navy", body)

        for path in ("/", "/stock", "/billing-efficiency"):
            status, headers, _ = self.request("GET", path)
            self.assertEqual(status, 303, path)
            self.assertEqual(dict(headers)["Location"], "/login")

        for path in ("/upload", "/stock-upload", "/weekly-upload", "/last-year-upload", "/billing-efficiency-upload", "/nepal-manual", "/ai-chat"):
            status, _, body = self.request("POST", path)
            self.assertEqual(status, 401, path)
            self.assertIn(b"Sign in is required", body)

        status, _, _ = self.request(
            "POST",
            "/login",
            body="username=owner&password=wrong",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 401)

        status, headers, _ = self.request(
            "POST",
            "/login",
            body="username=owner&password=test-password",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Forwarded-Proto": "https",
            },
        )
        self.assertEqual(status, 303)
        cookie = dict(headers)["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn("Secure", cookie)

        status, _, body = self.request(
            "GET",
            "/static/styles.css",
            headers={"Cookie": cookie.split(";", 1)[0]},
        )
        self.assertEqual(status, 200)
        self.assertIn(b"--navy", body)

        status, _, body = self.request(
            "GET",
            "/",
            headers={"Cookie": cookie.split(";", 1)[0]},
        )
        self.assertEqual(status, 200)
        if app.WORKBOOK_PATH.is_file():
            self.assertIn(b'data-owner="true"', body)
            self.assertIn(b"Choose workbook", body)
            self.assertIn(b"Download backup", body)
        else:
            self.assertIn(b"<h1>Sales overview</h1>", body)
            self.assertIn(b'id="workbookFile"', body)

        status, _, body = self.request(
            "POST",
            "/upload",
            headers={"Cookie": cookie.split(";", 1)[0]},
        )
        self.assertEqual(status, 400)
        self.assertNotIn(b"Sign in is required", body)

        status, _, body = self.request(
            "POST",
            "/ai-chat",
            body=json.dumps({}),
            headers={"Cookie": cookie.split(";", 1)[0]},
        )
        self.assertEqual(status, 400)
        self.assertIn(b"Enter a question", body)

        with patch.object(app, "get_stock_report", return_value={"available": False}):
            status, _, body = self.request(
                "GET",
                "/stock",
                headers={"Cookie": cookie.split(";", 1)[0]},
            )
        self.assertEqual(status, 200)
        self.assertIn(b'id="stock-upload"', body)

        with patch.object(app, "get_billing_efficiency_report", return_value={"available": False}):
            status, _, body = self.request(
                "GET",
                "/billing-efficiency",
                headers={"Cookie": cookie.split(";", 1)[0]},
            )
        self.assertEqual(status, 200)
        self.assertIn(b'id="billing-upload"', body)

    def test_manager_can_view_reports_but_cannot_change_or_download_all_data(self):
        manager = [{"username": "mp-manager", "password": "manager-password", "states": ["MP"]}]
        with patch.dict(os.environ, {"SALES_MIS_MANAGERS": json.dumps(manager)}):
            status, _, login_page = self.request("GET", "/login")
            self.assertEqual(status, 200)
            self.assertIn(b"Owner", login_page)
            self.assertIn(b"Manager", login_page)
            manager_form = login_page.split(b'id="managerLoginPanel"', 1)[1].split(b"</form>", 1)[0]
            self.assertIn(b'name="username"', manager_form)
            self.assertIn(b'id="managerPassword"', manager_form)
            self.assertNotIn(b'managerUsername', manager_form)
            self.assertIn(b'value="MP"', login_page)
            status, headers, _ = self.request(
                "POST",
                "/login",
                body="accountType=manager&username=MP&password=manager-password",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            self.assertEqual(status, 303)
            cookie = dict(headers)["Set-Cookie"].split(";", 1)[0]
            manager_headers = {"Cookie": cookie}

            status, _, body = self.request("GET", "/", headers=manager_headers)
            self.assertEqual(status, 200)
            self.assertIn(b"mp-manager", body)
            self.assertNotIn(b"Download backup", body)
            self.assertNotIn(b"Choose workbook", body)

            status, _, _ = self.request("GET", "/backup-download", headers=manager_headers)
            self.assertEqual(status, 403)
            status, _, _ = self.request("POST", "/upload", headers=manager_headers)
            self.assertEqual(status, 403)

    def test_home_page_allows_initial_sales_workbook_upload(self):
        _, login_headers, _ = self.request(
            "POST",
            "/login",
            body="username=owner&password=test-password",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        cookie = dict(login_headers)["Set-Cookie"].split(";", 1)[0]

        with tempfile.TemporaryDirectory() as directory:
            missing_workbook = Path(directory) / "latest.xlsx"
            with patch.object(app, "WORKBOOK_PATH", missing_workbook):
                status, _, body = self.request(
                    "GET",
                    "/",
                    headers={"Cookie": cookie},
                )

        self.assertEqual(status, 200)
        self.assertIn(b'id="report-data" type="application/json">{"available":false}</script>', body)
        self.assertIn(b"<h1>Sales overview</h1>", body)
        self.assertIn(b'id="workbookFile"', body)
        self.assertNotIn(b"Upload sales workbook | Velnik MIS", body)
        self.assertIn(b"SS to DB Sale", body)

    def test_missing_credentials_fail_closed(self):
        with patch.dict(os.environ, {"SALES_MIS_USERNAME": "", "SALES_MIS_PASSWORD": ""}):
            status, _, body = self.request("GET", "/login")
        self.assertEqual(status, 503)
        self.assertIn(b"Owner sign-in is not configured", body)

    def test_static_assets_are_served_with_correct_javascript_mime_type(self):
        status, headers, body = self.request("GET", "/static/language.js")
        self.assertEqual(status, 200)
        self.assertIn(b"localStorage", body)
        header_map = dict(headers)
        self.assertTrue(header_map["Content-Type"].startswith("text/javascript"))
        self.assertEqual(header_map["X-Frame-Options"], "DENY")
        self.assertEqual(header_map["X-Content-Type-Options"], "nosniff")
        self.assertEqual(header_map["X-Robots-Tag"], "noindex, nofollow, noarchive")
        self.assertIn("script-src 'self'", header_map["Content-Security-Policy"])

    def test_static_asset_path_cannot_escape_static_directory(self):
        status, _, _ = self.request("GET", "/static/../app.py")
        self.assertEqual(status, 404)

    def test_server_source_and_workbooks_are_not_routable(self):
        for path in (
            "/app.py",
            "/persistent_storage.py",
            "/templates/index.html",
            "/data/latest.xlsx",
            "/data/stock_latest.xlsx",
        ):
            with self.subTest(path=path):
                status, _, body = self.request("GET", path)
                self.assertEqual(status, 404)
                self.assertNotIn(b"SALES_MIS_PASSWORD", body)

    def test_unexpected_report_errors_do_not_reach_the_browser(self):
        internal_detail = "C:\\private\\server\\source.py"
        with patch.object(app, "get_report", side_effect=RuntimeError(internal_detail)):
            status, headers, body = self.request(
                "GET",
                "/",
                headers={"Cookie": self.owner_cookie()},
            )
        self.assertEqual(status, 500)
        self.assertIn(b"Please try again", body)
        self.assertNotIn(internal_detail.encode(), body)
        self.assertEqual(dict(headers)["X-Robots-Tag"], "noindex, nofollow, noarchive")

    def owner_cookie(self):
        _, headers, _ = self.request(
            "POST",
            "/login",
            body="username=owner&password=test-password",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return dict(headers)["Set-Cookie"].split(";", 1)[0]

    def test_billing_efficiency_upload_accepts_macro_workbook_separately(self):
        workbook_bytes = BytesIO()
        frame = pd.DataFrame([{
            "Month": "Apr",
            "DB Code": "DB-1",
            "DB Status": "Active",
            "Zone": "North",
            "State": "State A",
            "SS Name": "SS A",
            "DB Name": "Distributor 1",
            "Res SR/SO Name": "Rep A",
            "Value In Lacs": 1,
            "Product A": 1,
        }])
        with pd.ExcelWriter(workbook_bytes, engine="openpyxl") as writer:
            frame.to_excel(writer, sheet_name="SS to DB Sale", index=False, startrow=1)
        contents = workbook_bytes.getvalue()

        _, login_headers, _ = self.request(
            "POST",
            "/login",
            body="username=owner&password=test-password",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        cookie = dict(login_headers)["Set-Cookie"].split(";", 1)[0]
        boundary = "billing-upload-test"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="workbook"; filename="billing.xlsm"\r\n'
            "Content-Type: application/vnd.ms-excel.sheet.macroEnabled.12\r\n\r\n"
        ).encode("utf-8") + contents + f"\r\n--{boundary}--\r\n".encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            billing_path = Path(directory) / "billing_efficiency_latest.xlsm"
            metadata_path = Path(directory) / "billing_efficiency_source.json"
            sales_path = Path(directory) / "latest.xlsx"
            sales_path.write_bytes(b"sales workbook")
            with (
                patch.object(app, "BILLING_EFFICIENCY_WORKBOOK_PATH", billing_path),
                patch.object(app, "BILLING_EFFICIENCY_META_PATH", metadata_path),
            ):
                status, _, response_body = self.request(
                    "POST",
                    "/billing-efficiency-upload",
                    body=body,
                    headers={
                        "Cookie": cookie,
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                    },
                )
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(response_body)["reportUrl"], "/billing-efficiency")
            self.assertEqual(billing_path.read_bytes(), contents)
            self.assertEqual(sales_path.read_bytes(), b"sales workbook")
            self.assertEqual(
                json.loads(metadata_path.read_text(encoding="utf-8"))["source_name"],
                "billing.xlsm",
            )

    def test_backup_download_requires_owner_and_contains_only_report_files(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "latest.xlsx").write_bytes(b"sales workbook")
            (data_dir / "source.json").write_text('{"source_name":"sales.xlsx"}', encoding="utf-8")
            (data_dir / "unrelated.txt").write_text("not included", encoding="utf-8")
            with patch.object(app, "DATA_DIR", data_dir):
                status, _, _ = self.request("GET", "/backup-download")
                self.assertEqual(status, 401)

                status, headers, _ = self.request(
                    "POST",
                    "/login",
                    body="username=owner&password=test-password",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                self.assertEqual(status, 303)
                cookie = dict(headers)["Set-Cookie"].split(";", 1)[0]
                status, headers, body = self.request(
                    "GET",
                    "/backup-download",
                    headers={"Cookie": cookie},
                )

        self.assertEqual(status, 200)
        self.assertEqual(dict(headers)["Content-Type"], "application/zip")
        self.assertIn("attachment;", dict(headers)["Content-Disposition"])
        with tempfile.TemporaryFile() as archive_file:
            archive_file.write(body)
            archive_file.seek(0)
            with zipfile.ZipFile(archive_file) as backup:
                self.assertEqual(set(backup.namelist()), {"latest.xlsx", "source.json"})
                self.assertEqual(backup.read("latest.xlsx"), b"sales workbook")


class ManagerStateScopeTests(unittest.TestCase):
    def test_local_manager_password_hash_is_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "manager_accounts.json"
            salt = "00112233445566778899aabbccddeeff"
            password = "local-manager-test"
            password_hash = app.hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt), app.MANAGER_PASSWORD_HASH_ITERATIONS
            ).hex()
            config_path.write_text(json.dumps([{
                "username": "state-manager",
                "passwordHash": password_hash,
                "salt": salt,
                "states": ["UP"],
            }]), encoding="utf-8")
            with (
                patch.object(app, "MANAGER_ACCOUNTS_PATH", config_path),
                patch.dict(os.environ, {"SALES_MIS_USERNAME": "owner"}, clear=True),
            ):
                account = app.manager_accounts()[0]
        self.assertTrue(app.manager_password_matches(account, password))
        self.assertFalse(app.manager_password_matches(account, "wrong"))

    def test_sales_payload_is_recomputed_from_only_assigned_states(self):
        workbook = tempfile.TemporaryFile()
        raw = pd.DataFrame([
            {"Voucher Number": "V1", "Date": "2026-10-01", "Without GST": 10, "In Lacs": 11, "State": "UP", "Item Group2": "Product A"},
            {"Voucher Number": "V2", "Date": "2026-10-01", "Without GST": 90, "In Lacs": 99, "State": "MP", "Item Group2": "Product B"},
        ])
        db = pd.DataFrame([
            {"DB Code": "DB-UP", "DB Status": "ACTIVE", "State": "UP", "DB Name": "UP Distributor", "Zero Billing": "Zero Billing DB"},
            {"DB Code": "DB-MP", "DB Status": "ACTIVE", "State": "MP", "DB Name": "MP Distributor", "Zero Billing": "Zero Billing DB"},
        ])
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            raw.to_excel(writer, sheet_name="Raw", index=False, startrow=1)
            db.to_excel(writer, sheet_name="SS to DB Sale", index=False, startrow=1)
        workbook.seek(0)
        try:
            report = app.build_report(workbook, allowed_states={"up"})
        finally:
            workbook.close()

        self.assertEqual(report["quality"]["netTotal"], 10)
        self.assertEqual({row["label"] for row in report["stateByDay"]}, {"UP"})
        self.assertEqual({row["product"] for row in report["productMix"]}, {"Product A"})
        self.assertEqual({row["name"] for row in report["followups"]}, {"UP Distributor"})

    def test_manager_scope_without_raw_sales_keeps_state_plan_data(self):
        workbook = tempfile.TemporaryFile()
        raw = pd.DataFrame([
            {"Voucher Number": "V1", "Date": "2026-10-01", "Without GST": 10, "In Lacs": 11, "State": "UP", "Item Group2": "Product A"},
        ])
        db = pd.DataFrame([
            {"DB Code": "DB-UP", "DB Status": "ACTIVE", "State": "UP", "DB Name": "UP Distributor", "Zero Billing": "Zero Billing DB"},
        ])
        state_summary = pd.DataFrame([
            {"State": "NP", "Billing Plan Lacs": 100, "Ach. MTD": 40, "Achive. %": 0.4},
            {"State": "Total", "Billing Plan Lacs": 100, "Ach. MTD": 50, "Achive. %": 0.5},
        ])
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            raw.to_excel(writer, sheet_name="Raw", index=False, startrow=1)
            db.to_excel(writer, sheet_name="SS to DB Sale", index=False, startrow=1)
            state_summary.to_excel(writer, sheet_name="Without GST", index=False, startrow=1)
        workbook.seek(0)
        try:
            report = app.build_report(workbook, allowed_states={"np"})
        finally:
            workbook.close()

        self.assertEqual(report["quality"]["salesLines"], 0)
        self.assertEqual(report["quality"]["netTotal"], 40)
        self.assertEqual([row["state"] for row in report["statePlan"]], ["NP"])
        self.assertEqual(report["nepalManual"]["state"], "NP")


class ReplaceWorkbookTests(unittest.TestCase):
    def test_replaces_destination_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "workbook.xlsx"
            destination.write_bytes(b"old workbook")

            app.replace_workbook(b"new workbook", destination)

            self.assertEqual(destination.read_bytes(), b"new workbook")
            self.assertEqual([path.name for path in Path(directory).iterdir()], ["workbook.xlsx"])

    def test_preserves_destination_when_atomic_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "workbook.xlsx"
            destination.write_bytes(b"old workbook")

            with patch.object(Path, "replace", side_effect=OSError("replacement failed")):
                with self.assertRaisesRegex(OSError, "replacement failed"):
                    app.replace_workbook(b"new workbook", destination)

            self.assertEqual(destination.read_bytes(), b"old workbook")
            self.assertEqual([path.name for path in Path(directory).iterdir()], ["workbook.xlsx"])

    def test_explains_access_denied_during_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "stock_latest.xlsx"
            destination.write_bytes(b"old workbook")

            with patch.object(Path, "replace", side_effect=PermissionError("Access is denied")):
                with self.assertRaisesRegex(
                    PermissionError,
                    "Close the workbook in Excel or any other app",
                ):
                    app.replace_workbook(b"new workbook", destination)

            self.assertEqual(destination.read_bytes(), b"old workbook")
            self.assertEqual([path.name for path in Path(directory).iterdir()], ["stock_latest.xlsx"])

    def test_stock_master_data_does_not_copy_quantity_into_value(self):
        with tempfile.TemporaryDirectory() as directory:
            workbook = Path(directory) / "stock.xlsx"
            with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
                pd.DataFrame([
                    [None, None, None],
                    [None, None, None],
                    ["Type", "State", "Name"],
                    ["CS", "UP", "Stock Point"],
                ]).to_excel(writer, sheet_name="Stock", header=False, index=False)
                pd.DataFrame([
                    [None, None, None, None],
                    [None, None, None, None],
                    ["Item", "CS", "SS", "Grand Total"],
                    ["Product A", 5, 2, 7],
                ]).to_excel(writer, sheet_name="Item Stock CS & SS Stock", header=False, index=False)
                pd.DataFrame([
                    [None, None, None, None],
                    [None, None, None, None],
                    ["Item", "UP", "CG", "Grand Total"],
                    ["Product A", 7, 70, 77],
                ]).to_excel(writer, sheet_name="State wise Stock", header=False, index=False)
                pd.DataFrame([
                    [None, None, None, None, None, None],
                    ["New State", "New Product", "New Value", "State", "Type", "SKU"],
                    ["UP", "Product A", 7, "UP", "CS", "SKU-1"],
                    ["CG", "Product A", 70, "CG", "CS", "SKU-2"],
                ]).to_excel(writer, sheet_name="Master Data", header=False, index=False)

            report = app.build_stock_report(workbook, source_name="stock.xlsx")

            detail = report["stateProductDetails"][0]
            self.assertEqual(detail["quantity"], 7)
            self.assertEqual(detail["value"], 0)

            scoped = app.build_stock_report(workbook, source_name="stock.xlsx", allowed_states={"up"})
            self.assertEqual(scoped["summary"]["totalStock"], 7)
            self.assertEqual({row["state"] for row in scoped["states"]}, {"UP"})
            self.assertEqual({row["state"] for row in scoped["stateProductDetails"]}, {"UP"})
            self.assertEqual(scoped["stateProductRows"][0]["values"], {"UP": 7})


class LastYearWorkbookTests(unittest.TestCase):
    def test_loads_and_caches_separate_last_year_report(self):
        with tempfile.TemporaryDirectory() as directory:
            workbook = Path(directory) / "last_year_sales.xlsx"
            metadata = Path(directory) / "last_year_source.json"
            workbook.write_bytes(b"prior-year workbook")
            metadata.write_text(
                json.dumps({"source_name": "31-Oct-2025.xlsx", "loaded_at": "2026-10-14 13:00"}),
                encoding="utf-8",
            )
            report = {
                "source": "31-Oct-2025.xlsx",
                "loadedAt": "2026-10-14 13:00",
                "history": {"start": "2025-10-01", "end": "2025-10-31"},
            }
            with (
                patch.object(app, "LAST_YEAR_WORKBOOK_PATH", workbook),
                patch.object(app, "LAST_YEAR_META_PATH", metadata),
                patch.dict(app._LAST_YEAR_CACHE, {"mtime": None, "payload": None}),
                patch.object(app, "build_report", return_value=report) as build_report,
            ):
                first = app.get_last_year_report()
                second = app.get_last_year_report()

        self.assertIs(first, report)
        self.assertIs(second, report)
        build_report.assert_called_once_with(
            workbook,
            "31-Oct-2025.xlsx",
            "2026-10-14 13:00",
        )


class AIChatTests(unittest.TestCase):
    def test_sales_context_obeys_selected_dates_and_omits_followup_details(self):
        report = {
            "period": {"start": "2026-10-01", "end": "2026-10-03"},
            "history": {
                "start": "2026-09-29",
                "end": "2026-10-03",
                "daily": [
                    {"date": "2026-09-29", "net": 2},
                    {"date": "2026-09-30", "net": 8},
                    {"date": "2026-10-01", "net": 10},
                    {"date": "2026-10-02", "net": 20},
                    {"date": "2026-10-03", "net": 30},
                ],
                "stateByDay": [
                    {"date": "2026-09-29", "label": "UP", "value": 2},
                    {"date": "2026-09-30", "label": "UP", "value": 8},
                    {"date": "2026-10-01", "label": "UP", "value": 10},
                    {"date": "2026-10-02", "label": "UP", "value": 20},
                    {"date": "2026-10-03", "label": "UP", "value": 30},
                ],
                "productByDay": [],
            },
            "daily": [
                {"date": "2026-10-01", "net": 10, "gross": 12, "lines": 2},
                {"date": "2026-10-02", "net": 20, "gross": 24, "lines": 3},
                {"date": "2026-10-03", "net": 30, "gross": 36, "lines": 4},
            ],
            "stateByDay": [
                {"date": "2026-10-01", "label": "UP", "value": 10},
                {"date": "2026-10-02", "label": "UP", "value": 20},
                {"date": "2026-10-03", "label": "UP", "value": 30},
            ],
            "productByDay": [
                {"date": "2026-10-02", "label": "Product A", "value": 20},
            ],
            "statePlan": [{"state": "UP", "plan": 100, "achievement": 60, "gap": 40}],
            "quality": {
                "salesLines": 9,
                "missingNet": 0,
                "missingTariff": 0,
                "duplicateRows": 0,
                "activeZeroBilling": 0,
            },
            "followups": [{"name": "Private Distributor", "code": "123"}],
            "zeroByState": {},
        }
        with (
            patch.object(app, "get_report", return_value=report),
            patch.object(app, "get_weekly_performance", return_value={"available": False}),
        ):
            context = app.build_analysis_context("sales", "2026-10-02", "2026-10-02")

        self.assertEqual(context["sales"]["daily"], [report["daily"][1]])
        self.assertEqual(context["sales"]["stateSales"], [{"name": "UP", "salesLakh": 20}])
        self.assertEqual(context["sales"]["productSales"], [{"name": "Product A", "salesLakh": 20}])
        self.assertNotIn("followups", context["sales"])
        self.assertNotIn("Private Distributor", json.dumps(context))
        self.assertEqual(context["sales"]["comparison"]["previousSales"], 10)
        self.assertEqual(context["sales"]["comparison"]["currentSales"], 20)

    def test_stock_context_excludes_distributor_identity(self):
        stock = {
            "reportDate": "14-Oct-26",
            "summary": {"totalStock": 100},
            "products": [{"item": "Product A", "total": 100}],
            "states": [{"state": "UP", "total": 100}],
            "distributors": [{"name": "Private Distributor", "total": 100}],
        }
        with patch.object(app, "get_stock_report", return_value=stock):
            context = app.build_analysis_context("stock")

        self.assertEqual(context["stock"]["products"], stock["products"])
        self.assertNotIn("distributors", context["stock"])
        self.assertNotIn("Private Distributor", json.dumps(context))

    def test_local_analysis_reports_selected_sales_and_plan_gaps(self):
        context = {
            "sales": {
                "period": {"start": "2026-10-01", "end": "2026-10-02"},
                "daily": [
                    {"date": "2026-10-01", "net": 10},
                    {"date": "2026-10-02", "net": 20},
                ],
                "stateSales": [{"name": "UP", "salesLakh": 30}],
                "productSales": [{"name": "Product A", "salesLakh": 30}],
                "monthlyPlanProgress": [
                    {"state": "UP", "plan": 100, "achievement": 60, "gap": 40, "pct": 0.6},
                ],
                "quality": {
                    "missingNet": 0,
                    "missingTariff": 0,
                    "duplicateRows": 0,
                    "activeZeroBilling": 2,
                },
                "zeroBillingByState": [("UP", 2)],
                "weeklyPerformance": None,
            },
            "stock": None,
        }

        answer = app.build_local_analysis("Show sales, products and plan gaps", context)

        self.assertIn("30.00 lakh", answer)
        self.assertIn("UP: 40.00 lakh gap", answer)
        self.assertIn("Product A", answer)

    def test_local_stock_analysis_highlights_negative_balances(self):
        context = {
            "stock": {
                "reportDate": "14-Oct-26",
                "summary": {
                    "totalStock": 25,
                    "csStock": 20,
                    "ssStock": 5,
                    "negativeProductCount": 1,
                },
                "products": [
                    {"item": "Product A", "total": 25, "negative": -3},
                ],
                "states": [{"state": "UP", "total": 25}],
            },
        }

        answer = app.build_local_analysis("Which items have negative stock?", context)

        self.assertIn("Product A (-3.00 workbook units)", answer)
        self.assertIn("Reconcile these", answer)

    def test_local_analysis_compares_shared_product_sales_and_stock(self):
        context = {
            "sales": {
                "period": {"start": "2026-10-01", "end": "2026-10-02"},
                "daily": [],
                "stateSales": [],
                "productSales": [{"name": "Product A", "salesLakh": 12}],
                "monthlyPlanProgress": [],
                "quality": {},
                "zeroBillingByState": [],
                "weeklyPerformance": None,
            },
            "stock": {
                "reportDate": "14-Oct-26",
                "summary": {
                    "totalStock": 4,
                    "csStock": 3,
                    "ssStock": 1,
                    "negativeProductCount": 0,
                },
                "products": [{"item": "product a", "total": 4, "negative": 0}],
                "states": [],
            },
        }

        answer = app.build_local_analysis("Compare product sales vs stock", context)

        self.assertIn("Product A: 12.00 lakh sales, 4.00 workbook units stock", answer)
        self.assertIn("not a sell-through", answer)

    def test_local_analysis_flags_high_stock_states_with_low_billing(self):
        context = {
            "sales": {
                "period": {"start": "2026-10-01", "end": "2026-10-14"},
                "daily": [],
                "stateSales": [
                    {"name": "Alpha", "salesLakh": 5},
                    {"name": "Beta", "salesLakh": 10},
                    {"name": "Gamma", "salesLakh": 50},
                    {"name": "Delta", "salesLakh": 60},
                ],
                "productSales": [],
                "monthlyPlanProgress": [],
                "quality": {},
                "zeroBillingByState": [],
                "weeklyPerformance": None,
            },
            "stock": {
                "reportDate": "14-Oct-26",
                "summary": {
                    "totalStock": 210,
                    "csStock": 150,
                    "ssStock": 60,
                    "negativeProductCount": 0,
                },
                "products": [],
                "states": [
                    {"state": "Alpha", "total": 100},
                    {"state": "Beta", "total": 80},
                    {"state": "Gamma", "total": 20},
                    {"state": "Delta", "total": 10},
                ],
            },
        }

        answer = app.build_local_analysis(
            "Which states have stock to sell but low billing?", context
        )

        self.assertIn("Alpha: 100.00 workbook units stock, 5.00 lakh billing", answer)
        self.assertIn("Beta: 80.00 workbook units stock, 10.00 lakh billing", answer)
        self.assertIn("above-median stock and below-median billing", answer)
        self.assertIn("billing covers 2026-10-01 to 2026-10-14", answer)
        self.assertIn("not a direct stock-to-sales ratio", answer)

    def test_local_analysis_returns_hindi_for_high_stock_low_billing(self):
        context = {
            "sales": {
                "period": {"start": "2026-10-01", "end": "2026-10-14"},
                "daily": [],
                "stateSales": [
                    {"name": "Alpha", "salesLakh": 5},
                    {"name": "Beta", "salesLakh": 10},
                    {"name": "Gamma", "salesLakh": 50},
                    {"name": "Delta", "salesLakh": 60},
                ],
                "productSales": [],
                "monthlyPlanProgress": [],
                "quality": {},
                "zeroBillingByState": [],
                "weeklyPerformance": None,
            },
            "stock": {
                "reportDate": "14-Oct-26",
                "summary": {
                    "totalStock": 210,
                    "csStock": 150,
                    "ssStock": 60,
                    "negativeProductCount": 0,
                },
                "products": [],
                "states": [
                    {"state": "Alpha", "total": 100},
                    {"state": "Beta", "total": 80},
                    {"state": "Gamma", "total": 20},
                    {"state": "Delta", "total": 10},
                ],
            },
        }

        answer = app.build_local_analysis(
            "किन राज्यों में स्टॉक अधिक लेकिन बिलिंग कम है?", context, "hi"
        )

        self.assertIn("अधिक स्टॉक लेकिन कम बिलिंग वाले राज्य", answer)
        self.assertIn("Alpha: 100.00 वर्कबुक इकाई स्टॉक, 5.00 लाख बिलिंग", answer)
        self.assertIn("वितरक के पास उपलब्धता", answer)

    def test_period_comparison_uses_equal_length_preceding_dates(self):
        history = {
            "start": "2026-09-01",
            "end": "2026-10-10",
            "daily": [
                {"date": "2026-09-08", "net": 5},
                {"date": "2026-09-09", "net": 15},
                {"date": "2026-10-08", "net": 10},
                {"date": "2026-10-09", "net": 30},
            ],
            "stateByDay": [
                {"date": "2026-09-08", "label": "UP", "value": 5},
                {"date": "2026-09-09", "label": "UP", "value": 15},
                {"date": "2026-10-08", "label": "UP", "value": 10},
                {"date": "2026-10-09", "label": "UP", "value": 30},
            ],
        }

        comparison = app.build_period_comparison(history, "2026-10-08", "2026-10-09")

        self.assertEqual(comparison["previousPeriod"], {"start": "2026-10-06", "end": "2026-10-07"})
        self.assertEqual(comparison["currentSales"], 40)
        self.assertEqual(comparison["previousSales"], 0)
        self.assertIsNone(comparison["changePct"])
        self.assertTrue(comparison["available"])

    def test_period_comparison_is_unavailable_when_history_does_not_cover_prior_range(self):
        history = {
            "start": "2026-10-08",
            "end": "2026-10-10",
            "daily": [{"date": "2026-10-08", "net": 10}],
            "stateByDay": [],
        }

        comparison = app.build_period_comparison(history, "2026-10-08", "2026-10-09")

        self.assertFalse(comparison["available"])
        self.assertNotIn("currentSales", comparison)

    def test_local_analysis_summarizes_period_change(self):
        context = {
            "sales": {
                "comparison": {
                    "available": True,
                    "previousPeriod": {"start": "2026-10-01", "end": "2026-10-03"},
                    "currentPeriod": {"start": "2026-10-04", "end": "2026-10-06"},
                    "previousSales": 30,
                    "currentSales": 45,
                    "change": 15,
                    "changePct": 50,
                    "states": [
                        {"state": "UP", "change": 15},
                    ],
                },
                "period": {"start": "2026-10-04", "end": "2026-10-06"},
            },
            "stock": None,
        }

        answer = app.build_local_analysis("Compare sales with previous period", context)

        self.assertIn("Equal-length period comparison", answer)
        self.assertIn("50.0% increase", answer)
        self.assertIn("UP (15.00 lakh)", answer)


class WeeklyRollupTests(unittest.TestCase):
    @staticmethod
    def workbook(rows):
        return pd.DataFrame(
            rows,
            columns=["State", "Week Plan", "Week Ach.", "Balance"],
        )

    def build_report(self, rows):
        with patch.object(app.pd, "read_excel", return_value=self.workbook(rows)):
            return app.build_weekly_performance("unused.xlsx")

    def test_complete_component_rows_replace_group_total(self):
        rows = [
            ["AP", 1, 0.5, 0.5],
            ["TG", 2, 1, 1],
            ["KR", 3, 1.5, 1.5],
            ["KN", 4, 2, 2],
            ["TN", 5, 2.5, 2.5],
            ["SO", 999, 999, 0],
        ]

        report = self.build_report(rows)

        self.assertEqual([row["state"] for row in report["states"]], ["SO"])
        self.assertEqual(report["summary"]["plan"], 15)
        self.assertEqual(report["states"][0]["achievement"], 7.5)
        self.assertEqual(report["warnings"], [])

    def test_incomplete_components_use_workbook_group_total_with_warning(self):
        report = self.build_report([
            ["AP", 1, 0.5, 0.5],
            ["TG", 2, 1, 1],
            ["SO", 90, 40, 50],
        ])

        self.assertEqual([row["state"] for row in report["states"]], ["SO"])
        self.assertEqual(report["summary"]["plan"], 90)
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("KN, KR, TN", report["warnings"][0])
        self.assertIn("workbook-provided group total", report["warnings"][0])

    def test_incomplete_components_without_group_total_are_not_rolled_up(self):
        report = self.build_report([
            ["AP", 1, 0.5, 0.5],
            ["TG", 2, 1, 1],
        ])

        self.assertEqual([row["state"] for row in report["states"]], ["AP", "TG"])
        self.assertEqual(report["summary"]["plan"], 3)
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("SO group total is not calculated", report["warnings"][0])

    def test_manager_scope_limits_weekly_rows_and_totals(self):
        rows = [
            ["UP", 100, 60, 40],
            ["MP", 200, 100, 100],
        ]
        with patch.object(app.pd, "read_excel", return_value=self.workbook(rows)):
            report = app.build_weekly_performance("unused.xlsx", allowed_states={"up"})
        self.assertEqual(report["summary"]["plan"], 100)
        self.assertEqual([row["state"] for row in report["states"]], ["UP"])


if __name__ == "__main__":
    unittest.main()
