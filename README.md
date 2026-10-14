# Velnik MIS

A local Python webpage for daily sales snapshots, state/region plan tracking, product mix, active zero-billing distributor follow-up, data checks, and a separate stock report.

## Start on Windows

1. Install Python 3.10 or newer if it is not already installed.
2. Open this folder in File Explorer.
3. Double-click `run.bat`. It checks the required package versions and installs or updates them only when needed. If Windows says Python is unavailable, install Python and enable “Add Python to PATH”.
5. Open the local address printed in the black command window (normally `http://127.0.0.1:5000`). Keep that window open while using the report.
6. Use **Choose workbook** to select the latest sales workbook. The app saves it as `data/latest.xlsx` and rebuilds the report from that file. Keep an unchanged copy of your source workbook elsewhere.
7. To update Nepal figures without changing Excel, use the **Nepal** section’s **Update Nepal figures** form and click **Save Nepal figures**. Amounts are in lakh. The entered values are saved locally for that reporting month; product amounts must add up to monthly achievement. If you change only achievement, **Other / Range Value** adjusts to balance the product mix.
8. Select **Stock report** in the navigation and upload a stock workbook there. Stock workbooks are saved separately as `data/stock_latest.xlsx`; uploading one does not replace the sales workbook.
   If Windows denies access while replacing the stock workbook, close `stock_latest.xlsx` in Excel or any other app, check that the `data` folder is writable, and retry.

9. Select **Weekly** in the navigation to review weekly state performance. The weekly plan workbook is saved separately as `data/weekly_plan.xlsx`; upload a new planning workbook there to replace it.
10. Use **Local analysis** in either report to ask about sales trends, plan gaps, product and state rankings, states with relatively high stock but low billing, and data checks. Select **हिन्दी** to show analysis in Hindi; selecting a language again also re-runs the latest question in that language. The stock-versus-billing check compares only matching states/regions, flagging above-median stock with below-median billing. Stock and sales units differ, and their report dates may differ, so treat flags as review priorities rather than a direct ratio. Analysis runs on this computer and requires no API key, credits, or internet connection.
11. In **Year-over-year**, upload the prior-year sales workbook separately (for example, `31-Oct-2025.xlsx`). It is stored as `data/last_year_sales.xlsx` and does not replace the current sales workbook. The section compares the selected current dates with matching calendar dates one year earlier, including totals and state/region changes. The prior-year workbook must include the `Raw` and `SS to DB Sale` sheets, and its dated Raw data must cover the full matching range.
12. The sales report also compares selected dates with the immediately preceding period of equal length. **Download action report** exports this comparison, year-over-year changes, stock/billing review flags, and plan gaps. Previous-period figures require those dates in the current sales workbook; manual Nepal summary amounts are excluded from dated comparisons.

## Workbook assumptions

- The workbook has `Raw`, `Without GST`, `SS to DB Sale`, and `Zero Billing` sheets.
- `Raw` has headers on row 2 and contains transaction-level lines.
- `Without GST` contains region plan and achievement values.
- `SS to DB Sale` contains distributor master data; `Zero Billing` marks accounts with no billing.
- The weekly planning workbook's first sheet contains `State`, `Week Plan`, `Week Ach.`, and `Balance` columns. Weekly achievement is read from that workbook and is not recalculated from daily sales.
- SO and MH totals are calculated from components only when every expected component row is present. If the source has an explicit group total but incomplete components, the source total is retained and a dashboard warning lists the missing rows.
- The State Billing section ranks state / region billing for the selected snapshot date range and shows each location's share of total billing and per-capita billing rank. Per-capita billing uses projected population as of 1 July 2026; SO combines AP/TG/KR/KN/TN and MH uses component regions when present, otherwise the MH total. Nepal and regions without population estimates are not per-capita ranked.
- Sales values are displayed in lakh. The app flags mismatches and missing fields rather than silently correcting them.

If your next workbook changes sheet names or column layout, the app may report a missing sheet/field. Update the column mapping in `app.py` for the new layout.

## Run regression tests

From this folder, run `python -m unittest discover -s tests -v`. The tests cover atomic workbook replacement and weekly SO/MH rollups.

## Deploy a free demo on Render

The included `render.yaml` configures a free Render web service. To deploy:

1. Push this project to a GitHub repository, including `app.py`, `requirements.txt`, `render.yaml`, `templates/`, `static/`, and the sample workbook in `data/`.
2. In Render, choose **New > Blueprint**, connect that GitHub repository, and apply the `render.yaml` configuration.
3. Wait for the build to finish, then open the service URL shown in the Render dashboard.

The service binds to Render's network interface and uses its assigned `PORT`. Free instances may sleep when idle and their filesystem is temporary: uploaded workbooks or other changes can be lost after a restart or redeploy. This demo has no login protection, so use only non-sensitive sample data and do not share confidential sales workbooks or the public URL as if it were access-controlled. For real sales data, deploy behind authentication and use persistent storage on a private service.

## Generate the appointment letter PDF

Run `.\.venv\Scripts\python.exe py.py` from this folder. This uses the project's virtual environment, which includes the `reportlab` dependency. If running with a different Python interpreter, install dependencies first with `python -m pip install -r requirements.txt`.

## Stock report workbook

- The stock report requires the `Stock`, `Item Stock CS & SS Stock`, and `State wise Stock` sheets.
- It shows product and state balances, stock by distributor/stock point, negative stock, and NPD stock as a separate figure.
- Stock values are shown as recorded in the workbook; the sales upload and stock upload are stored independently.

## Report timing

The webpage recalculates when you upload a workbook, save Nepal figures, or reload it. It does not run on a schedule while the computer and app are closed. For a recurring report, leave the app available or configure Windows Task Scheduler to run a separate refresh process.

## Privacy

When run locally, the server binds to `127.0.0.1` on this computer and workbooks are kept in this project folder. Local analysis uses fixed rules against report figures on this computer; it does not send workbook data or API keys to an online service. It is not a generative AI model and can only answer using the supported report checks. A cloud deployment is publicly reachable unless access controls are added; do not upload confidential data to the demo deployment.
