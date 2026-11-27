# Velnik MIS

A password-protected sales, stock, weekly, billing-efficiency, and year-over-year reporting webpage. The application runs in AWS ECS and stores workbook data in private Amazon S3 storage through the ECS task IAM role. It does not use AWS access keys, Google Drive, Render, or Cloud Run.

The sales, stock, and billing pages include expandable guides that explain the source and meaning of each report section. Billing efficiency also supports a month-to-month comparison of sales, distributor coverage, efficiency, and state-level changes.

## AWS deployment

Use the deployment script from PowerShell:

```powershell
.\aws\deploy-ecs-express.ps1
```

The script installs or uses AWS CLI, creates the required ECS Express, private S3, ECR, Secrets Manager, IAM, CloudWatch, and load-balancer resources, builds the container with AWS CodeBuild, and seeds existing report files into S3.

The deployed container requires:

- `SALES_MIS_USERNAME`
- `SALES_MIS_PASSWORD`
- `SALES_MIS_SESSION_SIGNING_KEY`
- `SALES_MIS_STORAGE_PROVIDER=s3`
- `SALES_MIS_STORAGE_BUCKET=<private bucket>`
- `SALES_MIS_STORAGE_REGION=<AWS region>`
- `SALES_MIS_STORAGE_PREFIX=velnik-mis/`

Owner credentials should be stored in AWS Secrets Manager. S3 access must be granted to the ECS task role, not configured as static application credentials.

## Data files

Workbook data is synchronized between the container and S3:

- Sales: `latest.xlsx`, `source.json`
- Nepal figures: `nepal_manual.json`
- Stock: `stock_latest.xlsx`, `stock_source.json`
- Weekly: `weekly_plan.xlsx`, `weekly_source.json`
- Prior year: `last_year_sales.xlsx`, `last_year_source.json`
- Billing: `billing_efficiency_latest.xlsm`, `billing_efficiency_source.json`

The app uses atomic local file replacement and uploads changed files before confirming success. Uploaded business workbooks and backup archives contain sensitive data and should remain private.

## Browser and source-code privacy

The app does not expose server-side Python files, templates, or the `data` directory through its HTTP routes. Report pages, workbook uploads, and backups require the owner session; S3 blocks public access. Responses are marked `noindex` and use a Content Security Policy as additional safeguards, not as access controls.

HTML, CSS, and JavaScript required to render the website are sent to the browser and can always be inspected by visitors who can access that page. Do not put credentials, signing keys, or other secrets in templates or static assets. Minifying or disabling browser developer tools cannot make client-side code private.

## Workbook assumptions

- Sales workbooks require `Raw` and `SS to DB Sale`; dated `Raw` headers are on row 2.
- Stock workbooks require `Stock`, `Item Stock CS & SS Stock`, and `State wise Stock`.
- Weekly planning uses a `State`, `Week Plan`, `Week Ach.`, and `Balance` layout on the first sheet.
- Billing efficiency workbooks require a `SS to DB Sale` sheet with headers on row 2.

Sales values are shown in lakh. Formula-like CSV text is escaped so spreadsheet applications do not execute it as a formula. SO and MH group totals are handled only from complete component rows or retained with explicit source warnings when components are incomplete.

## Run locally for development

Python 3.10 or newer is required.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SALES_MIS_USERNAME = "owner"
$env:SALES_MIS_PASSWORD = "use-a-long-unique-password"
.\.venv\Scripts\python.exe app.py
```

For local development only, omit S3 variables to use the temporary local `data` directory. Production deployments must configure a private S3 bucket and task IAM role.

### Manager accounts

Keep the owner credentials in `SALES_MIS_USERNAME` and `SALES_MIS_PASSWORD`. For local development, manager accounts can be stored in the ignored `data/manager_accounts.json` file with PBKDF2 password hashes and assigned state labels. In production, set `SALES_MIS_MANAGERS` through AWS Secrets Manager. An account can define multiple `loginOptions`; each option has its own `loginId`, visible `groupName`, and state scope, and uses that manager's password. This supports separate state logins as well as consolidated South and MH logins. State labels are matched without regard to letter case and must match the labels used in the workbooks.

The sign-in page offers Boss and Manager modes. Manager mode lists each configured state or region login and fills the username with its `loginId`; managers enter their account password to continue.

```json
[
  {"username":"manager1","name":"Manager One","password":"use-a-strong-password","states":["DL","HR"],"loginOptions":[
    {"loginId":"DL","groupName":"DL","states":["DL"]},
    {"loginId":"HR","groupName":"HR","states":["HR"]}
  ]},
  {"username":"manager2","name":"Manager Two","password":"use-another-strong-password","states":["AP","TG"],"loginOptions":[
    {"loginId":"south","groupName":"South","states":["AP","TG"]}
  ]}
]
```

Managers can view and download report data for their assigned states. Workbook uploads, Nepal figure edits, and the full backup remain owner-only. Store production manager credentials in AWS Secrets Manager and pass them to the task as `SALES_MIS_MANAGERS`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run `tests/browser-analysis.html` in a browser for browser-side regression checks.

## Container checks

```powershell
docker build -t sales-mis-app .
docker run --rm -p 8080:8080 -e PORT=8080 -e SALES_MIS_USERNAME=owner -e SALES_MIS_PASSWORD='use-a-long-unique-password' sales-mis-app
```

Docker is optional for ECS deployment; the AWS deployment script builds through AWS CodeBuild.
