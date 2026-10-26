# Local Sales MIS Analysis

A local Python webpage for daily sales snapshots, state/region plan tracking, product mix, active zero-billing distributor follow-up, and data checks. It starts with the September workbook provided for this task.

## Start on Windows

1. Install Python 3.10 or newer if it is not already installed.
2. Open this folder in File Explorer.
3. Double-click `run.bat`. If Windows says Python is unavailable, install Python and enable “Add Python to PATH”.
4. On the first run, install the listed packages in Command Prompt from this folder:

   ```text
   python -m pip install -r requirements.txt
   ```

   Then double-click `run.bat` again.
5. Open the local address printed in the black command window (normally `http://127.0.0.1:5000`). Keep that window open while using the report.
6. Use **Upload Excel** to select the latest sales workbook. The app saves it as `data/latest.xlsx` and rebuilds the report from that file. Keep an unchanged copy of your source workbook elsewhere.

## Workbook assumptions

- The workbook has `Raw`, `Without GST`, `SS to DB Sale`, and `Zero Billing` sheets.
- `Raw` has headers on row 2 and contains transaction-level lines.
- `Without GST` contains region plan and achievement values.
- `SS to DB Sale` contains distributor master data; `Zero Billing` marks accounts with no billing.
- Sales values are displayed in lakh. The app flags mismatches and missing fields rather than silently correcting them.

If your next workbook changes sheet names or column layout, the app may report a missing sheet/field. Update the column mapping in `app.py` for the new layout.

## Report timing

The webpage recalculates when you upload a workbook or press **Refresh**. It does not run on a schedule while the computer and app are closed. For a recurring report, leave the app available or configure Windows Task Scheduler to run a separate refresh process.

## Privacy

The server binds to `127.0.0.1` on this computer. The workbook and report are kept in this project folder; the app does not send them to an online service.
