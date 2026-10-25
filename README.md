# Velnik MIS

A local Python webpage for daily sales snapshots, state/region plan tracking, product mix, active zero-billing distributor follow-up, data checks, and a separate stock report.

Use the **हिन्दी** button in the page header to switch the sales report, stock report, and owner sign-in page to Hindi. Your choice is saved in the browser and applied across the pages; choose **English** to switch back.

## Start on Windows

1. Install Python 3.10 or newer if it is not already installed.
2. Open this folder in File Explorer.
3. In PowerShell, set `SALES_MIS_USERNAME` and `SALES_MIS_PASSWORD` for the session before starting the server, for example `$env:SALES_MIS_USERNAME = "owner"; $env:SALES_MIS_PASSWORD = "use-a-long-unique-password"; .\run.bat`. It checks the required package versions and installs them only when needed. If Windows says Python is unavailable, install Python and enable “Add Python to PATH”.
4. Open the local address printed in the black command window (normally `http://127.0.0.1:5000`). Keep that window open while using the report.
5. Use **Choose workbook** to select the latest sales workbook. The app saves it as `data/latest.xlsx` and rebuilds the report from that file. Keep an unchanged copy of your source workbook elsewhere.
6. To update Nepal figures without changing Excel, use the **Nepal** section’s **Update Nepal figures** form and click **Save Nepal figures**. Amounts are in lakh. The entered values are saved locally for that reporting month; product amounts must add up to monthly achievement. If you change only achievement, **Other / Range Value** adjusts to balance the product mix.
7. Select **Stock report** in the navigation and upload a stock workbook there. Stock workbooks are saved separately as `data/stock_latest.xlsx`; uploading one does not replace the sales workbook.
   If Windows denies access while replacing the stock workbook, close `stock_latest.xlsx` in Excel or any other app, check that the `data` folder is writable, and retry.

8. Select **Billing efficiency** in the navigation and upload the separate `.xlsm` or `.xlsx` billing workbook. It must contain an `SS to DB Sale` sheet with headers on row 2. This report shows month, state, zone, representative, product-coverage, and active zero-billing analysis without replacing sales or stock reports. Billing efficiency is positive `Value In Lacs` distributor codes divided by active distributor codes; zero-billing follow-ups include active codes whose net billing is zero or negative. Product coverage counts distributors with positive values in product columns; the workbook does not specify those values' units. `ASD` and `ASDF` are not interpreted because their meanings are undefined. The separate local workbook `data/billing_efficiency_latest.xlsm` is excluded from Git to avoid publishing business-sensitive distributor data; after deployment or on another computer, upload it again. Macros in uploaded files are not run.
9. Select **Weekly** in the navigation to review weekly state performance. The weekly plan workbook is saved separately as `data/weekly_plan.xlsx`; upload a new planning workbook there to replace it.
10. Use **Local analysis** in either report to ask about sales trends, plan gaps, product and state rankings, states with relatively high stock but low billing, and data checks. Select **हिन्दी** to show analysis in Hindi; selecting a language again also re-runs the latest question in that language. The stock-versus-billing check compares only matching states/regions, flagging above-median stock with below-median billing. Stock and sales units differ, and their report dates may differ, so treat flags as review priorities rather than a direct ratio. Analysis runs on this computer and requires no API key, credits, or internet connection.
11. In **Year-over-year**, upload the prior-year sales workbook separately (for example, `31-Oct-2025.xlsx`). It is stored as `data/last_year_sales.xlsx` and does not replace the current sales workbook. The section compares the selected current dates with matching calendar dates one year earlier, including totals and state/region changes. The prior-year workbook must include the `Raw` and `SS to DB Sale` sheets, and its dated Raw data must cover the full matching range.
12. The sales report also compares selected dates with the immediately preceding period of equal length. **Download action report** exports this comparison, year-over-year changes, stock/billing review flags, and plan gaps. Previous-period figures require those dates in the current sales workbook; manual Nepal summary amounts are excluded from dated comparisons.
    CSV exports escape formula-like text from workbook data so spreadsheet apps treat those cells as text.

## Workbook assumptions

- The workbook has `Raw`, `Without GST`, `SS to DB Sale`, and `Zero Billing` sheets.
- `Raw` has headers on row 2 and contains transaction-level lines.
- `Without GST` contains region plan and achievement values.
- `SS to DB Sale` contains distributor master data; `Zero Billing` marks accounts with no billing.
- The weekly planning workbook's first sheet contains `State`, `Week Plan`, `Week Ach.`, and `Balance` columns. Weekly achievement is read from that workbook and is not recalculated from daily sales.
- SO and MH totals are calculated from components only when every expected component row is present. If the source has an explicit group total but incomplete components, the source total is retained and a dashboard warning lists the missing rows.
- The State Billing section ranks state / region billing for the selected snapshot date range and shows each location's share of total billing and per-capita billing rank. Per-capita billing uses projected population as of 1 July 2026; SO combines AP/TG/KR/KN/TN and MH uses component regions when present, otherwise the MH total. Nepal and regions without population estimates are not per-capita ranked.
- Sales values are displayed in lakh. The app flags mismatches and missing fields rather than silently correcting them.

If your next workbook changes sheet names or column layout, the app may report a missing sheet/field. Update the sales and stock mappings in `app.py`; weekly plan calculations are in `weekly.py`, and shared workbook value parsing is in `workbook_utils.py`.

## Run regression tests

From this folder, run `python -m unittest discover -s tests -v`. This runs the Python regression tests. To run the browser-side date and stock comparison tests, open `tests/browser-analysis.html` in a web browser and check that it reports **All 4 browser tests passed**.

## Deploy on Render

The included `render.yaml` configures a free Render web service. The owner account is required to view reports, upload workbooks, or change Nepal figures. To deploy:

1. Push this project to a **private** GitHub repository. The tracked workbooks in `data/` may contain business-sensitive sales, stock, and distributor information. Never make this repository public with those files or publish them as sample data.
2. In Render, choose **New > Blueprint**, connect that GitHub repository, and apply the `render.yaml` configuration.
3. In the Render service's **Environment** settings, set `SALES_MIS_USERNAME` and `SALES_MIS_PASSWORD` to a unique username and a long, strong password. These values are secrets: do not put them in source code, commit them, or share them.
4. Wait for the build to finish, then open the service URL shown in the Render dashboard. Sign in with your configured credentials to view reports, upload workbooks, or update Nepal figures.

The service binds to Render's network interface and uses its assigned `PORT`. The health check exposes no report data. Upload and Nepal-update endpoints require the owner sign-in even if someone manually calls them; sessions expire after 12 hours and are cleared on a server restart. Use **Sign out** when finished. Free instances may sleep when idle and their filesystem is temporary: uploaded workbooks or other changes can be lost after a restart or redeploy.

The dashboard shows the latest workbook that is currently available, including its source filename and upload time. On the free Render service this is not guaranteed to survive a restart or redeploy; if the displayed workbook is old or the service has reset, sign in and upload the latest daily workbook again.

### Free-tier backup and restore

Before replacing workbooks or a planned restart/redeploy, sign in and use **Download backup** in the navigation. The ZIP contains the current sales, stock, weekly, prior-year, and billing-efficiency workbooks (when present), their source metadata, and the Nepal manual-entry data. Store the archive encrypted and outside this repository; it contains the same sensitive business data as the reports. Download backups regularly because a free Render instance cannot guarantee that uploaded files survive a restart.

To restore a local installation, stop the server, extract the ZIP into the project's `data/` folder, allow the files to replace the existing copies, and restart the app. To restore on Render, sign in and upload the sales, stock, weekly, and prior-year workbooks from the archive through their respective report sections. Re-enter any Nepal manual figures using the archived `nepal_manual.json` as the reference; the app does not accept a ZIP restore upload.

Reports and distributor details require owner sign-in. GitHub repository access is separate from site access. Keep the repository private because its tracked workbooks contain business data; if it has ever been public, making it private does not remove copies from Git history or prior downloads.

## Stock report workbook

- The stock report requires the `Stock`, `Item Stock CS & SS Stock`, and `State wise Stock` sheets.
- It shows product and state balances, stock by distributor/stock point, negative stock, and NPD stock as a separate figure.
- Stock values are shown as recorded in the workbook; the sales upload and stock upload are stored independently.

## Report timing

The webpage recalculates when you upload a workbook, save Nepal figures, or reload it. It does not run on a schedule while the computer and app are closed. For a recurring report, leave the app available or configure Windows Task Scheduler to run a separate refresh process.

## Privacy

When run locally, the server binds to `127.0.0.1` on this computer and workbooks are kept in this project folder. Starting the web server requires `SALES_MIS_USERNAME` and `SALES_MIS_PASSWORD`; all reports and report analysis require the configured owner sign-in. Local analysis uses fixed rules against report figures on this computer and does not send workbook data or API keys to an online service. In the cloud deployment, reports, uploads, and data changes are all restricted to signed-in owners.
