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

8. Select **Billing efficiency** in the navigation and upload the separate `.xlsm` or `.xlsx` billing workbook. It must contain an `SS to DB Sale` sheet with headers on row 2. This report shows month, state, zone, representative, product-coverage, and active zero-billing analysis without replacing sales or stock reports. Billing efficiency is positive `Value In Lacs` distributor codes divided by active distributor codes; zero-billing follow-ups include active codes whose net billing is zero or negative. Product coverage counts distributors with positive values in product columns; the workbook does not specify those values' units. `ASD` and `ASDF` are not interpreted because their meanings are undefined. The separate local workbook `data/billing_efficiency_latest.xlsm` is excluded from Git to avoid publishing business-sensitive distributor data. When external object storage is configured, it is synchronized there automatically. Macros in uploaded files are not run.
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

The service binds to Render's network interface and uses its assigned `PORT`. It can start before a sales workbook has been uploaded; after signing in, the dashboard opens with the report area ready for the first `.xlsx` workbook upload. The workbook must include the `Raw` and `SS to DB Sale` sheets. The health check exposes no report data. Upload and Nepal-update endpoints require the owner sign-in even if someone manually calls them; sessions expire after 12 hours and are cleared on a server restart. Use **Sign out** when finished. Free instances may sleep when idle and their filesystem is temporary: uploaded workbooks or other changes can be lost after a restart or redeploy.

The dashboard shows the latest workbook that is currently available, including its source filename and upload time. On the free Render service this is not guaranteed to survive a restart or redeploy; if the displayed workbook is old or the service has reset, sign in and upload the latest daily workbook again.

### Free-tier backup and restore

Before replacing workbooks or a planned restart/redeploy, sign in and use **Download backup** in the navigation. The ZIP contains the current sales, stock, weekly, prior-year, and billing-efficiency workbooks (when present), their source metadata, and the Nepal manual-entry data. Store the archive encrypted and outside this repository; it contains the same sensitive business data as the reports. Download backups regularly because a free Render instance cannot guarantee that uploaded files survive a restart.

To restore a local installation, stop the server, extract the ZIP into the project's `data/` folder, allow the files to replace the existing copies, and restart the app. To restore on Render, sign in and upload the sales, stock, weekly, and prior-year workbooks from the archive through their respective report sections. Re-enter any Nepal manual figures using the archived `nepal_manual.json` as the reference; the app does not accept a ZIP restore upload.

### Keep Render uploads across deployments

Render's free web-service filesystem is ephemeral. To keep uploaded workbooks and Nepal manual-entry data when the service restarts or redeploys, configure one of the supported external object-storage providers. The app supports Google Drive Shared Drives through a Google Cloud service account or Cloudflare R2 through S3-compatible credentials. Only configure one provider at a time.

### Deploy the full app to Google Cloud Run

The repository includes a Dockerfile for Cloud Run. Runtime workbook persistence uses a Google Drive Shared Drive and Cloud Run's attached service identity (Application Default Credentials), so no service-account private key needs to be stored in the image or Render environment.

1. **Keep the current data safe.** Before migrating, sign in to the live app and download **Download backup**. Keep the ZIP private and encrypted.
2. **Create a Google Cloud project.** In [Google Cloud Console](https://console.cloud.google.com/), create/select a project and attach a billing account. Enable **Cloud Run Admin API**, **Cloud Build API**, **Artifact Registry API**, and **Google Drive API**. Cloud Run may incur charges; configure a billing budget alert before production use.
3. **Create the Drive folder before deploying.** Use an organization Google Workspace **Shared Drive**, create a new empty folder such as `velnik-mis-data`, and add the Cloud Run runtime service account (step 4) as **Content manager** on that Shared Drive. Copy the folder ID from its URL. The service account needs Drive membership because it reads and writes the uploaded business workbooks.
4. **Create the Cloud Run service identity.** In Google Cloud Console, go to **IAM & Admin → Service Accounts → Create service account** and name it `velnik-mis-run`. It does not need broad project roles to read Drive; grant it access to the Shared Drive instead. Record its email address. When prompted to attach a service account in Cloud Run, choose this identity. (If deploying from CLI, the deployer must also have permission to attach it.)
5. **Seed the Shared Drive before deploying.** Extract the backup ZIP on your computer and upload its report files into the new Shared Drive folder, keeping their original filenames, such as `latest.xlsx`, `source.json`, `stock_latest.xlsx`, `stock_source.json`, `weekly_plan.xlsx`, `weekly_source.json`, `last_year_sales.xlsx`, `last_year_source.json`, `billing_efficiency_latest.xlsm`, and `billing_efficiency_source.json`. Include `nepal_manual.json` if it exists. Keep this folder private and do not share it publicly. The container intentionally excludes the local `data/` directory; the app needs the backed-up `latest.xlsx` in Drive to start.
6. **Create login secrets.** In **Security → Secret Manager**, create secrets named `SALES_MIS_USERNAME` and `SALES_MIS_PASSWORD` with the owner login values you want for this Cloud Run deployment. Grant the `velnik-mis-run` service account **Secret Manager Secret Accessor** for these two secrets. Do not put passwords in Git or into a command that you might save/share.
7. **Deploy from Windows.** Install and initialize the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install), open PowerShell in the repository root (the folder containing `Dockerfile`), and run:

   ```powershell
   gcloud init
   gcloud config set project YOUR_PROJECT_ID
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com drive.googleapis.com
   gcloud run deploy velnik-mis `
     --source . `
     --region asia-south1 `
     --service-account velnik-mis-run@YOUR_PROJECT_ID.iam.gserviceaccount.com `
     --allow-unauthenticated `
     --memory 1Gi `
     --timeout 300 `
     --set-env-vars "SALES_MIS_STORAGE_PROVIDER=google_drive,GOOGLE_DRIVE_FOLDER_ID=YOUR_SHARED_DRIVE_FOLDER_ID" `
     --set-secrets "SALES_MIS_USERNAME=SALES_MIS_USERNAME:latest,SALES_MIS_PASSWORD=SALES_MIS_PASSWORD:latest"
   ```

   Replace both `YOUR_PROJECT_ID` and `YOUR_SHARED_DRIVE_FOLDER_ID`. The Cloud Run URL is printed when deployment completes. Public invocation only exposes the app's sign-in screen; report and upload endpoints still require the configured owner login.
8. **Verify before relying on it.** Open the printed Cloud Run URL, sign in with the secrets from step 6, and check the report pages show **Persistent storage: connected**. Confirm all reports load from the Shared Drive. Upload a small update and verify it appears in Drive before considering migration complete. Keep the original backup and continue downloading encrypted backups regularly.

On each Cloud Run start, known report files are restored from the Shared Drive. Future workbook uploads and Nepal manual changes are written there before upload success is reported. The project needs a current backup in Drive before its first start; deployment cannot recover files already lost from Render's temporary filesystem.

#### Google Drive Shared Drive setup

1. Before deploying the storage change, sign in to the live app and download a backup. Keep this archive encrypted and outside the repository.
2. In [Google Cloud Console](https://console.cloud.google.com/), create/select a project and enable the **Google Drive API**. For Cloud Run, use its attached service identity as described above; a JSON key is only needed for another hosting provider without Google Application Default Credentials.
3. In Google Drive, create or choose a folder inside your organization's **Shared Drive**. Add the runtime service account's email as a **Content manager** on the Shared Drive. Personal My Drive isn't supported by this service-account setup.
4. Set `SALES_MIS_STORAGE_PROVIDER=google_drive` and `GOOGLE_DRIVE_FOLDER_ID` to the Shared Drive folder ID. On Cloud Run, the attached service identity authenticates through Application Default Credentials. For another host, set `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON` to its service-account JSON key and keep the JSON private.
5. Before first startup, place the current workbooks in the Shared Drive folder with the filenames used in `data/`. At startup the app restores known report files from the Drive folder. Future workbook uploads and Nepal manual changes are written to Drive before the app confirms success.
6. Sign in, confirm the pages show **Persistent storage: connected**, and keep downloading encrypted backups regularly.

#### Cloudflare R2 setup

Create a private R2 Standard bucket and an R2 API token scoped to **Object Read & Write** access for that bucket. In Render, set `SALES_MIS_STORAGE_PROVIDER` to `r2`, `SALES_MIS_STORAGE_BUCKET` to the bucket name, `SALES_MIS_STORAGE_ENDPOINT_URL` to `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`, `SALES_MIS_STORAGE_ACCESS_KEY_ID` and `SALES_MIS_STORAGE_SECRET_ACCESS_KEY` to the token values, `SALES_MIS_STORAGE_REGION` to `auto`, and `SALES_MIS_STORAGE_PREFIX` to `velnik-mis/`. Keep the token private. Check [current R2 pricing](https://developers.cloudflare.com/r2/pricing/) for free-tier limits and billing terms.

Do not deploy the storage change until you have downloaded the live backup. Files already on Render's temporary filesystem cannot be recovered by the app after Render has discarded them. The first configured deployment must be followed by re-uploading the current workbooks from the backup to seed external storage.

Reports and distributor details require owner sign-in. GitHub repository access is separate from site access. Keep the repository private because its tracked workbooks contain business data; if it has ever been public, making it private does not remove copies from Git history or prior downloads.

## Stock report workbook

- The stock report requires the `Stock`, `Item Stock CS & SS Stock`, and `State wise Stock` sheets.
- It shows product and state balances, stock by distributor/stock point, negative stock, and NPD stock as a separate figure.
- Stock values are shown as recorded in the workbook; the sales upload and stock upload are stored independently.

## Report timing

The webpage recalculates when you upload a workbook, save Nepal figures, or reload it. It does not run on a schedule while the computer and app are closed. For a recurring report, leave the app available or configure Windows Task Scheduler to run a separate refresh process.

## Privacy

When run locally, the server binds to `127.0.0.1` on this computer and workbooks are kept in this project folder. Starting the web server requires `SALES_MIS_USERNAME` and `SALES_MIS_PASSWORD`; all reports and report analysis require the configured owner sign-in. Local analysis uses fixed rules against report figures on this computer and does not send workbook data or API keys to an online service. In the cloud deployment, reports, uploads, and data changes are all restricted to signed-in owners.
