import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import app


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


if __name__ == "__main__":
    unittest.main()
