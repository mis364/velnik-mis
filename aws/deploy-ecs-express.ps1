param(
    [string]$Profile = "default",
    [string]$Region = "ap-southeast-2",
    [string]$StackName = "velnik-mis",
    [switch]$Confirmed
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$TemplatePath = Join-Path $PSScriptRoot "ecs-express-template.json"

$AwsCliDirectory = Join-Path $env:LOCALAPPDATA "Programs\Amazon\AWSCLIV2"
$AwsCli = Join-Path $AwsCliDirectory "aws.exe"
if (Test-Path -LiteralPath $AwsCli -PathType Leaf) {
    $env:Path = "$AwsCliDirectory;$env:Path"
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI is required. Install it and configure AWS IAM Identity Center (SSO) before deploying."
}

$AccountId = aws sts get-caller-identity --query Account --output text --profile $Profile --region $Region
if ($LASTEXITCODE -ne 0 -or -not $AccountId) {
    throw "AWS authentication failed. Run aws sso login --profile $Profile and retry."
}

Write-Host "AWS account: $AccountId"
Write-Host "AWS region: $Region"
Write-Host "This creates an S3 bucket, ECR repository, Secrets Manager secrets, IAM roles, and an ECS Express service."
Write-Host "The running service includes Fargate and an HTTPS load balancer, which can incur ongoing charges."
if (-not $Confirmed) {
    if ((Read-Host "Type DEPLOY to continue") -cne "DEPLOY") {
        throw "Deployment cancelled."
    }
}

aws cloudformation deploy `
    --template-file $TemplatePath `
    --stack-name $StackName `
    --capabilities CAPABILITY_IAM `
    --parameter-overrides ContainerImage=unset `
    --profile $Profile `
    --region $Region
if ($LASTEXITCODE -ne 0) {
    throw "The AWS foundation stack could not be created or updated."
}

$OutputQuery = "Stacks[0].Outputs[?OutputKey=='ImageRepositoryUri'].OutputValue | [0]"
$RepositoryUri = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query $OutputQuery `
    --output text `
    --profile $Profile `
    --region $Region
if ($LASTEXITCODE -ne 0 -or -not $RepositoryUri -or $RepositoryUri -eq "None") {
    throw "Could not read the ECR repository URI from the CloudFormation stack."
}

$Timestamp = Get-Date -Format "yyyyMMddHHmmss"
$ImageTag = $Timestamp
$ImageUri = "${RepositoryUri}:${ImageTag}"

$SourceBucketQuery = "Stacks[0].Outputs[?OutputKey=='CodeBuildSourceBucketName'].OutputValue | [0]"
$SourceBucketName = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query $SourceBucketQuery `
    --output text `
    --profile $Profile `
    --region $Region
if ($LASTEXITCODE -ne 0 -or -not $SourceBucketName -or $SourceBucketName -eq "None") {
    throw "Could not read the CodeBuild source bucket name."
}

$ProjectQuery = "Stacks[0].Outputs[?OutputKey=='CodeBuildProjectName'].OutputValue | [0]"
$ProjectName = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query $ProjectQuery `
    --output text `
    --profile $Profile `
    --region $Region
if ($LASTEXITCODE -ne 0 -or -not $ProjectName -or $ProjectName -eq "None") {
    throw "Could not read the CodeBuild project name."
}

$StageDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "velnik-mis-build-$PID"
$ArchivePath = Join-Path ([System.IO.Path]::GetTempPath()) "velnik-mis-source-$PID.zip"
Remove-Item $StageDirectory, $ArchivePath -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $StageDirectory | Out-Null
$ExcludedNames = @(".git", ".venv", "aws", "data", "sales-mis-app", "tests", "__pycache__")
Get-ChildItem -LiteralPath $RepositoryRoot -Force | Where-Object { $ExcludedNames -notcontains $_.Name } |
    Copy-Item -Destination $StageDirectory -Recurse -Force

# Build these directories explicitly so remote images always include browser assets and templates.
foreach ($RequiredDirectory in @("static", "templates")) {
    $SourceDirectory = Join-Path $RepositoryRoot $RequiredDirectory
    if (-not (Test-Path -LiteralPath $SourceDirectory -PathType Container)) {
        throw "Required application directory is missing: $RequiredDirectory"
    }
    Copy-Item -LiteralPath $SourceDirectory -Destination $StageDirectory -Recurse -Force
}
foreach ($RequiredFile in @("static/styles.css", "static/language.js")) {
    if (-not (Test-Path -LiteralPath (Join-Path $StageDirectory $RequiredFile) -PathType Leaf)) {
        throw "Required build file is missing: $RequiredFile"
    }
}
if (-not (Get-ChildItem -LiteralPath (Join-Path $StageDirectory "templates") -Filter "*.html" -File | Select-Object -First 1)) {
    throw "Required templates directory contains no HTML files"
}
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path -LiteralPath $ArchivePath) { Remove-Item -LiteralPath $ArchivePath -Force }
$Zip = [System.IO.Compression.ZipFile]::Open(
    $ArchivePath,
    [System.IO.Compression.ZipArchiveMode]::Create
)
try {
    Get-ChildItem -LiteralPath $StageDirectory -Recurse -File | ForEach-Object {
        $RelativePath = $_.FullName.Substring($StageDirectory.Length).TrimStart('\', '/') -replace '\\', '/'
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $Zip,
            $_.FullName,
            $RelativePath,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
}
finally {
    $Zip.Dispose()
}

aws s3 cp $ArchivePath "s3://${SourceBucketName}/source.zip" --sse AES256 --profile $Profile --region $Region
if ($LASTEXITCODE -ne 0) {
    throw "Could not upload the application source to the private build bucket."
}

$BuildJson = aws codebuild start-build `
    --project-name $ProjectName `
    --environment-variables-override "name=IMAGE_REPO_URI,value=$RepositoryUri,type=PLAINTEXT" "name=IMAGE_TAG,value=$ImageTag,type=PLAINTEXT" `
    --profile $Profile `
    --region $Region `
    --output json
if ($LASTEXITCODE -ne 0 -or -not $BuildJson) {
    throw "Could not start the remote CodeBuild image build."
}

$BuildId = ($BuildJson | ConvertFrom-Json).build.id
Write-Host "Remote CodeBuild started: $BuildId"
while ($true) {
    Start-Sleep -Seconds 15
    $BuildResult = aws codebuild batch-get-builds --ids $BuildId --profile $Profile --region $Region --output json
    if ($LASTEXITCODE -ne 0) {
        throw "Could not retrieve CodeBuild build status."
    }
    $Build = ($BuildResult | ConvertFrom-Json).builds[0]
    Write-Host "Build status: $($Build.buildStatus)"
    if ($Build.buildStatus -ne "IN_PROGRESS") {
        if ($Build.buildStatus -ne "SUCCEEDED") {
            throw "Remote image build failed with status $($Build.buildStatus)."
        }
        break
    }
}

Remove-Item $StageDirectory, $ArchivePath -Recurse -Force -ErrorAction SilentlyContinue

$BucketQuery = "Stacks[0].Outputs[?OutputKey=='WorkbookBucketName'].OutputValue | [0]"
$BucketName = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query $BucketQuery `
    --output text `
    --profile $Profile `
    --region $Region
if ($LASTEXITCODE -ne 0 -or -not $BucketName -or $BucketName -eq "None") {
    throw "Could not read the S3 bucket name from the CloudFormation stack."
}

$KnownDataFiles = @(
    "latest.xlsx",
    "source.json",
    "nepal_manual.json",
    "stock_latest.xlsx",
    "stock_source.json",
    "weekly_plan.xlsx",
    "weekly_source.json",
    "last_year_sales.xlsx",
    "last_year_source.json",
    "billing_efficiency_latest.xlsm",
    "billing_efficiency_source.json"
)
$DataDirectory = Join-Path $RepositoryRoot "data"
foreach ($FileName in $KnownDataFiles) {
    $LocalFile = Join-Path $DataDirectory $FileName
    if (Test-Path -LiteralPath $LocalFile -PathType Leaf) {
        aws s3 cp $LocalFile "s3://${BucketName}/velnik-mis/${FileName}" --profile $Profile --region $Region
        if ($LASTEXITCODE -ne 0) {
            throw "Could not seed $FileName to the private S3 bucket."
        }
    }
}

aws cloudformation deploy `
    --template-file $TemplatePath `
    --stack-name $StackName `
    --capabilities CAPABILITY_IAM `
    --parameter-overrides "ContainerImage=$ImageUri" `
    --profile $Profile `
    --region $Region
if ($LASTEXITCODE -ne 0) {
    throw "The ECS Express service could not be deployed."
}

Write-Host ""
Write-Host "Deployment completed. In the AWS ECS console, open the $StackName Express service in $Region to get its HTTPS URL."
Write-Host "The owner username and password are generated in Secrets Manager and are not printed by this script."
Write-Host "Retrieve the secret values from AWS Secrets Manager after deployment; do not share them or commit them."
